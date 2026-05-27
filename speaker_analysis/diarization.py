"""Pyannote diarization backend with version-compatible token handling."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import shutil
import subprocess
import tempfile
import time
from importlib import metadata
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "pyannote/speaker-diarization-community-1"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_int(name: str) -> int | None:
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _token() -> str:
    return (
        os.environ.get("VIDIOLINGUA_PYANNOTE_TOKEN", "").strip()
        or os.environ.get("HUGGINGFACE_TOKEN", "").strip()
        or os.environ.get("HF_TOKEN", "").strip()
        or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    )


def _pyannote_version() -> str | None:
    try:
        return metadata.version("pyannote.audio")
    except metadata.PackageNotFoundError:
        return None


def _torch_device(requested: str) -> str:
    requested = (requested or "auto").strip().lower()
    if requested in {"cpu", "cuda"}:
        return requested
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _failure(
    *,
    status: str,
    backend: str,
    model: str,
    device: str,
    duration_sec: float | None,
    errors: list[str],
    warnings: list[str] | None = None,
    pyannote_version: str | None = None,
    elapsed_sec: float | None = None,
    recommended_fix: str | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "backend": backend,
        "model": model,
        "device": device,
        "pyannote_version": pyannote_version,
        "token_present": bool(_token()),
        "speaker_count": None,
        "duration_sec": duration_sec,
        "elapsed_sec": elapsed_sec,
        "turns": [],
        "warnings": warnings or [],
        "errors": errors,
    }
    if recommended_fix:
        payload["recommended_fix"] = recommended_fix
    return payload


def _extract_wav(audio_or_video: Path, output_wav: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for diarization audio extraction but was not found on PATH.")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(audio_or_video),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr or result.stdout}")


def _load_waveform(wav_path: Path) -> tuple[Any, int, float]:
    import soundfile as sf
    import torch

    data, sample_rate = sf.read(str(wav_path), dtype="float32", always_2d=True)
    if data.size == 0:
        raise RuntimeError("Extracted diarization audio is empty.")
    waveform = torch.from_numpy(data.T)
    duration_sec = float(waveform.shape[1]) / float(sample_rate)
    return waveform, int(sample_rate), duration_sec


def _load_pipeline(model_id: str, token: str | None, device: str) -> Any:
    from pyannote.audio import Pipeline

    signature = inspect.signature(Pipeline.from_pretrained)
    kwargs: dict[str, Any] = {}
    if token:
        if "token" in signature.parameters:
            kwargs["token"] = token
        elif "use_auth_token" in signature.parameters:
            kwargs["use_auth_token"] = token

    pipeline = Pipeline.from_pretrained(model_id, **kwargs)
    if pipeline is None:
        raise RuntimeError(
            f"Pyannote returned no pipeline for {model_id}. Accept the model terms on Hugging Face "
            "and provide VIDIOLINGUA_PYANNOTE_TOKEN or HUGGINGFACE_TOKEN."
        )

    try:
        import torch

        pipeline.to(torch.device(device))
    except Exception as exc:
        if device == "cuda":
            raise RuntimeError(f"Could not move pyannote pipeline to CUDA: {exc}") from exc
    return pipeline


def _iter_turns(output: Any) -> list[dict[str, Any]]:
    diarization = getattr(output, "exclusive_speaker_diarization", None)
    if diarization is None:
        diarization = getattr(output, "speaker_diarization", None)
    if diarization is None:
        diarization = output

    turns: list[dict[str, Any]] = []
    if hasattr(diarization, "itertracks"):
        iterator = diarization.itertracks(yield_label=True)
        for turn, _track, speaker in iterator:
            start = round(float(turn.start), 3)
            end = round(float(turn.end), 3)
            if end > start:
                turns.append(
                    {
                        "start": start,
                        "end": end,
                        "speaker_id": str(speaker),
                        "confidence": None,
                    }
                )
        return sorted(turns, key=lambda item: (item["start"], item["end"], item["speaker_id"]))

    try:
        for item in diarization:
            if len(item) == 2:
                turn, speaker = item
            elif len(item) >= 3:
                turn, _track, speaker = item[:3]
            else:
                continue
            start = round(float(turn.start), 3)
            end = round(float(turn.end), 3)
            if end > start:
                turns.append(
                    {
                        "start": start,
                        "end": end,
                        "speaker_id": str(speaker),
                        "confidence": None,
                    }
                )
    except TypeError:
        pass
    return sorted(turns, key=lambda item: (item["start"], item["end"], item["speaker_id"]))


def diarize_audio(audio_or_video: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    """Run pyannote diarization and optionally write the canonical JSON report."""
    started = time.perf_counter()
    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")

    audio_or_video = Path(audio_or_video)
    model_id = os.environ.get("VIDIOLINGUA_PYANNOTE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    backend = os.environ.get("VIDIOLINGUA_DIARIZATION_BACKEND", "pyannote").strip().lower() or "pyannote"
    device = _torch_device(os.environ.get("VIDIOLINGUA_PYANNOTE_DEVICE", "auto"))
    version = _pyannote_version()
    token = _token()

    if not _env_bool("VIDIOLINGUA_ENABLE_SPEAKER_DIARIZATION", True):
        report = _failure(
            status="unavailable",
            backend=backend,
            model=model_id,
            device=device,
            duration_sec=None,
            pyannote_version=version,
            elapsed_sec=round(time.perf_counter() - started, 3),
            errors=[],
            warnings=["Speaker diarization is disabled by VIDIOLINGUA_ENABLE_SPEAKER_DIARIZATION=false."],
            recommended_fix="Set VIDIOLINGUA_ENABLE_SPEAKER_DIARIZATION=true to run pyannote diarization.",
        )
        return _write_if_requested(report, output_path)

    if backend != "pyannote":
        report = _failure(
            status="unavailable",
            backend=backend,
            model=model_id,
            device=device,
            duration_sec=None,
            pyannote_version=version,
            elapsed_sec=round(time.perf_counter() - started, 3),
            errors=[f"Unsupported diarization backend '{backend}'."],
            recommended_fix="Set VIDIOLINGUA_DIARIZATION_BACKEND=pyannote.",
        )
        return _write_if_requested(report, output_path)

    if not version:
        report = _failure(
            status="unavailable",
            backend=backend,
            model=model_id,
            device=device,
            duration_sec=None,
            pyannote_version=None,
            elapsed_sec=round(time.perf_counter() - started, 3),
            errors=["pyannote.audio is not installed in this Python runtime."],
            recommended_fix="Run diarization with the ASR runtime or install pyannote.audio only after approval.",
        )
        return _write_if_requested(report, output_path)

    if not token and str(model_id).startswith("pyannote/"):
        report = _failure(
            status="unavailable",
            backend=backend,
            model=model_id,
            device=device,
            duration_sec=None,
            pyannote_version=version,
            elapsed_sec=round(time.perf_counter() - started, 3),
            errors=["No Hugging Face token configured for pyannote diarization."],
            recommended_fix=(
                "Set VIDIOLINGUA_PYANNOTE_TOKEN or HUGGINGFACE_TOKEN in backend/.env, "
                f"then accept the terms for {model_id} on Hugging Face."
            ),
        )
        return _write_if_requested(report, output_path)

    print(
        "[SpeakerDiarization] "
        f"backend=pyannote model={model_id} pyannote_version={version} "
        f"token_present={bool(token)} device={device}"
    )

    try:
        tmp_parent = Path(output_path).parent if output_path else Path.cwd()
        tmp_parent.mkdir(parents=True, exist_ok=True)
        tmpdir = Path(tempfile.mkdtemp(prefix=".diarization_", dir=str(tmp_parent)))
        try:
            wav_path = tmpdir / "diarization_input.wav"
            _extract_wav(audio_or_video, wav_path)
            waveform, sample_rate, duration_sec = _load_waveform(wav_path)
            pipeline = _load_pipeline(model_id, token, device)
            kwargs: dict[str, Any] = {}
            min_speakers = _env_int("VIDIOLINGUA_PYANNOTE_MIN_SPEAKERS")
            max_speakers = _env_int("VIDIOLINGUA_PYANNOTE_MAX_SPEAKERS")
            if min_speakers is not None:
                kwargs["min_speakers"] = min_speakers
            if max_speakers is not None:
                kwargs["max_speakers"] = max_speakers
            try:
                output = pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
            except TypeError:
                output = pipeline({"waveform": waveform, "sample_rate": sample_rate})
            turns = _iter_turns(output)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as exc:
        message = str(exc)
        lower = message.lower()
        if any(part in lower for part in ("gated", "private", "401", "403", "terms", "access")):
            fix = (
                f"Accept the terms/access request for {model_id} on Hugging Face and set "
                "VIDIOLINGUA_PYANNOTE_TOKEN or HUGGINGFACE_TOKEN in backend/.env."
            )
        elif "torchcodec" in lower:
            fix = (
                "Pyannote audio decoding failed. This implementation preloads WAV tensors, so check that "
                "ffmpeg, soundfile, torch, and the installed torchcodec/torch versions are compatible."
            )
        else:
            fix = (
                "Check VIDIOLINGUA_PYANNOTE_MODEL, token/model access, ffmpeg availability, "
                "and VIDIOLINGUA_PYANNOTE_DEVICE."
            )
        report = _failure(
            status="failed",
            backend=backend,
            model=model_id,
            device=device,
            duration_sec=None,
            pyannote_version=version,
            elapsed_sec=round(time.perf_counter() - started, 3),
            errors=[f"PyAnnote diarization failed: {message}"],
            recommended_fix=fix,
        )
        return _write_if_requested(report, output_path)

    speaker_ids = sorted({turn["speaker_id"] for turn in turns})
    report = {
        "status": "computed",
        "backend": "pyannote",
        "model": model_id,
        "device": device,
        "pyannote_version": version,
        "token_present": bool(token),
        "speaker_count": len(speaker_ids),
        "duration_sec": round(duration_sec, 3),
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "turns": turns,
        "warnings": [] if turns else ["Pyannote completed but produced no speaker turns."],
        "errors": [],
    }
    print(
        "[SpeakerDiarization] "
        f"status={report['status']} speaker_count={report['speaker_count']} "
        f"turns={len(turns)} elapsed_sec={report['elapsed_sec']}"
    )
    return _write_if_requested(report, output_path)


def _write_if_requested(report: dict[str, Any], output_path: str | Path | None) -> dict[str, Any]:
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run VideoLingua speaker diarization.")
    parser.add_argument("--audio", required=True, help="Input audio or video file.")
    parser.add_argument("--output", required=True, help="Output speaker_diarization.json path.")
    args = parser.parse_args()
    report = diarize_audio(args.audio, args.output)
    if report.get("status") == "failed" and _env_bool("VIDIOLINGUA_FAIL_ON_DIARIZATION_ERROR"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
