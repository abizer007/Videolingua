"""Fast preflight for the video translation pipeline.

This does not run ASR, translation inference, XTTS generation, or lip-sync.
It validates local inputs and configuration so full jobs fail early with useful
messages instead of hanging during model resolution.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(PROJECT_ROOT / ".env")
_load_env_file(PROJECT_ROOT / "backend" / ".env")

from voice.xtts_cloner import VoiceClonePreflightError, config_from_env, preflight_xtts_voice_cloning


SUPPORTED_TRANSLATION_LANGS = {"hi", "es", "fr", "de", "ja", "zh", "ar", "pt", "en"}
XTTS_SUPPORTED_LANGS = {
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
    "nl", "cs", "ar", "zh", "hu", "ko", "ja",
}


@dataclass
class PreflightReport:
    ok: bool
    video_path: str
    target_language: str
    metadata: dict = field(default_factory=dict)
    audio_probe_path: str | None = None
    translation_engine: str = ""
    xtts: dict | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _run(cmd: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _probe_media(video_path: Path) -> dict:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "ffprobe failed")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    return {
        "duration_s": float(data.get("format", {}).get("duration") or 0),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": int(audio.get("sample_rate") or 0),
        "audio_channels": int(audio.get("channels") or 0),
    }


def _extract_probe_audio(video_path: Path, work_dir: Path) -> Path:
    output = work_dir / "preflight_audio.wav"
    result = _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-t",
            "3",
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output),
        ],
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "ffmpeg audio extraction failed")
    return output


def _check_translation(target_language: str, warnings: list[str]) -> str:
    engine = os.environ.get("VIDIOLINGUA_TRANSLATION_ENGINE", "llama3").strip().lower()
    if engine not in {"llama3", "google"}:
        raise RuntimeError(f"Unsupported VIDIOLINGUA_TRANSLATION_ENGINE={engine!r}")
    if target_language not in SUPPORTED_TRANSLATION_LANGS:
        raise RuntimeError(f"Unsupported target language '{target_language}'")

    if engine == "google":
        try:
            import deep_translator  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("deep-translator is not installed for Google translation") from exc
        warnings.append("Google translation uses an external service and may rate-limit.")
        return engine

    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests is not installed for Ollama/Llama-3 translation") from exc

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        response.raise_for_status()
        models = response.json().get("models", [])
        names = {m.get("name", "").split(":")[0] for m in models}
        if model.split(":")[0] not in names:
            raise RuntimeError(f"Ollama is reachable but model '{model}' is not listed")
    except Exception as exc:
        raise RuntimeError(
            "Llama-3 translation preflight failed. Start Ollama and pull the configured model, "
            "or set VIDIOLINGUA_TRANSLATION_ENGINE=google with fallback explicitly accepted."
        ) from exc
    return engine


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight VideoLingua video translation.")
    parser.add_argument("--video", default="Vidiolingua_Test_Official.mp4")
    parser.add_argument("--target-language", default="fr")
    parser.add_argument("--reference", default="test_speaker_ref.wav")
    parser.add_argument("--output", default="outputs/preflight_french.wav")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--device", default=None, choices=["auto", "cpu", "cuda"])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    video_path = Path(args.video)
    target_language = args.target_language.lower().strip()
    report = PreflightReport(ok=False, video_path=str(video_path), target_language=target_language)

    if not shutil.which("ffmpeg"):
        report.errors.append("ffmpeg is not on PATH")
    if not shutil.which("ffprobe"):
        report.errors.append("ffprobe is not on PATH")
    if not video_path.is_file():
        report.errors.append(f"Official/input video not found: {video_path}")
    if target_language not in XTTS_SUPPORTED_LANGS:
        report.errors.append(f"XTTS v2 does not support target language: {target_language}")

    if not report.errors:
        try:
            report.metadata = _probe_media(video_path)
        except Exception as exc:
            report.errors.append(f"Media metadata probe failed: {exc}")

    if not report.errors:
        runtime_tmp = PROJECT_ROOT / ".runtime_tmp"
        runtime_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime_tmp) as tmpdir:
            try:
                audio_path = _extract_probe_audio(video_path, Path(tmpdir))
                report.audio_probe_path = str(audio_path)
            except Exception as exc:
                report.errors.append(f"Audio extraction preflight failed: {exc}")

    try:
        report.translation_engine = _check_translation(target_language, report.warnings)
    except Exception as exc:
        report.errors.append(str(exc))

    config = config_from_env(target_language)
    if args.model_path:
        config.model_path = Path(args.model_path)
    if args.device:
        config.device = args.device
    try:
        xtts_report = preflight_xtts_voice_cloning(
            reference_audio_path=args.reference,
            output_path=args.output,
            language=target_language,
            config=config,
        )
        report.xtts = xtts_report.to_report()
    except VoiceClonePreflightError as exc:
        report.errors.append(f"XTTS preflight failed: {exc}")
    except Exception as exc:
        report.errors.append(f"XTTS preflight failed unexpectedly: {exc}")

    report.ok = not report.errors
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        status = "PASSED" if report.ok else "FAILED"
        print(f"Video translation preflight {status}")
        print(f"  video: {report.video_path}")
        print(f"  target language: {report.target_language}")
        if report.metadata:
            print(f"  duration: {report.metadata.get('duration_s'):.2f}s")
            print(f"  video codec: {report.metadata.get('video_codec')}")
            print(f"  audio codec: {report.metadata.get('audio_codec')}")
            print(f"  audio sample rate: {report.metadata.get('audio_sample_rate')}")
            print(f"  audio channels: {report.metadata.get('audio_channels')}")
        if report.translation_engine:
            print(f"  translation engine: {report.translation_engine}")
        if report.xtts:
            print(f"  xtts model dir: {report.xtts['model_files']['model_dir']}")
            print(f"  xtts device: {report.xtts['device']}")
        for warning in report.warnings:
            print(f"  warning: {warning}")
        for error in report.errors:
            print(f"  error: {error}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
