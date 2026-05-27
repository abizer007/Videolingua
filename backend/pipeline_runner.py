"""
Pipeline orchestrator — upgraded for Phase 1 model enhancements.

Stage order:
  0. BGM Separation (UVR5/Demucs) — optional, if VIDIOLINGUA_USE_UVR5=true
  0b. Clean voice sample extraction (from Demucs vocals, for XTTS cloning)
  1. ASR (WhisperX + PyAnnote)
  2. Translation (Llama-3 via Ollama | Google fallback)
  3. TTS (Coqui XTTSv2 | Hume | legacy gTTS)
  4. LipSync (SadTalker → Wav2Lip → ffmpeg) + GFPGAN + BGM remix

Python Runtime Split:
  FastAPI can run in a lightweight API env.
  Heavy ML stages use isolated envs via VIDIOLINGUA_ASR_PYTHON,
  VIDIOLINGUA_TTS_PYTHON, and VIDIOLINGUA_BGM_PYTHON.

All stages are subprocess-based and receive per-job input/output folders.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import json
from pathlib import Path

from backend import job_manifest, job_store
from compliance.compliance_passport import generate_compliance_bundle


def _timeout_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _run_stage(name: str, cmd: list, cwd: str, env=None, timeout_sec: int | None = None):
    """Run a stage; on failure raise with decoded stderr for reporting."""
    stage_env = dict(env or os.environ)
    stage_env["PYTHONIOENCODING"] = "utf-8"  # fix Unicode crash on Windows cp1252
    started = time.time()
    print(f"[Pipeline] Stage start: {name} at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    if cmd:
        print(f"[Pipeline] Stage python executable for {name}: {cmd[0]}")
    log_dir = stage_env.get("VIDIOLINGUA_STAGE_LOG_DIR", "").strip()
    log_path = Path(log_dir) if log_dir else None
    safe_name = name.lower().replace(" ", "_")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=stage_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_text(exc.stdout)
        stderr = _timeout_text(exc.stderr)
        if log_path:
            log_path.mkdir(parents=True, exist_ok=True)
            (log_path / f"{safe_name}.stdout.log").write_text(stdout, encoding="utf-8")
            (log_path / f"{safe_name}.stderr.log").write_text(stderr, encoding="utf-8")
        tail = (stderr or stdout or "").strip()[-1200:]
        raise RuntimeError(
            f"{name} timed out after {timeout_sec}s. "
            f"{tail or 'No subprocess output was captured.'}"
        ) from exc
    if log_path:
        log_path.mkdir(parents=True, exist_ok=True)
        (log_path / f"{safe_name}.stdout.log").write_text(result.stdout or "", encoding="utf-8")
        (log_path / f"{safe_name}.stderr.log").write_text(result.stderr or "", encoding="utf-8")
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip() or f"Exit code {result.returncode}"
        raise RuntimeError(f"{name}: {err}")
    print(f"[Pipeline] Stage end: {name} elapsed={time.time() - started:.1f}s")
    return result


def _manifest_stage_logs(logs_dir: Path, stage_name: str) -> list[str]:
    safe_name = stage_name.lower().replace(" ", "_")
    return [
        str(path)
        for path in (
            logs_dir / f"{safe_name}.stdout.log",
            logs_dir / f"{safe_name}.stderr.log",
        )
        if path.is_file()
    ]


def _register_compliance_artifacts(manifest_path: Path, bundle: dict | None, *, stage: str = "output_validation") -> None:
    try:
        passport = (bundle or {}).get("passport") or {}
        artifacts = passport.get("artifacts") or {}
        for key, artifact_path in artifacts.items():
            if not artifact_path:
                continue
            path = Path(artifact_path)
            suffix = path.suffix.lower().lstrip(".") or "jsonl"
            job_manifest.register_artifact(
                manifest_path,
                key,
                path,
                stage=stage,
                kind=suffix,
                role="output",
            )
    except Exception as exc:
        job_manifest.register_warning(manifest_path, f"Responsible AI artifacts could not be registered: {exc}", stage=stage)


def _responsible_ai_context(
    *,
    languages: list[str],
    voice_options: dict | None,
    voice_backend: str | None,
    translation_backend: str | None = None,
    reference_audio_used: bool = False,
    xtts_speaker_reference_used: bool = False,
    managed_tts_used: bool = False,
    lip_sync_or_visual_modification_used: bool = False,
    final_mp4_replaces_original_audio: bool = False,
    transcript_text: str = "",
    translated_text: str = "",
) -> dict:
    consent_fields = (voice_options or {}).get("responsibleAIConsent") or (voice_options or {}).get("responsible_ai_consent") or {}
    return {
        "target_languages": languages,
        "voice_backend": voice_backend,
        "translation_backend": translation_backend,
        "reference_audio_used": reference_audio_used,
        "xtts_speaker_reference_used": xtts_speaker_reference_used,
        "voice_cloning_or_speaker_reference_used": bool(xtts_speaker_reference_used or (reference_audio_used and not managed_tts_used)),
        "managed_tts_used": managed_tts_used,
        "lip_sync_or_visual_modification_used": lip_sync_or_visual_modification_used,
        "final_mp4_replaces_original_audio": final_mp4_replaces_original_audio,
        "consent_fields": consent_fields,
        "user_purpose": consent_fields.get("intended_use") or consent_fields.get("intendedUse"),
        "transcript_text": transcript_text,
        "translated_text": translated_text,
    }


def _first_file(paths: list[Path]) -> Path | None:
    return paths[0] if paths else None


def _env_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_false(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"0", "false", "no", "off"}


def _option_true(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(float(raw)))
    except ValueError:
        return default


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asr_cache_key(video_path: Path, *, source_language: str | None, engine: str, model: str) -> str:
    payload = {
        "video_sha256": _sha256_file(video_path),
        "source_language": source_language or "auto",
        "engine": engine,
        "model": model,
        "version": "asr-cache-v1",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _copy_cached_asr(cache_path: Path, output_path: Path, *, video_file: Path) -> bool:
    if not cache_path.is_file():
        return False
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        payload["video_file"] = str(video_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def _voice_cloning_required(voice_options: dict | None = None) -> bool:
    if _env_false("VOICE_CLONING_REQUIRED"):
        return False
    if _env_true("VOICE_CLONING_REQUIRED") or _env_true("VIDIOLINGUA_REQUIRE_VOICE_CLONE"):
        return True
    if _env_true("ALLOW_GENERIC_TTS_FALLBACK"):
        return False
    if voice_options and "cloned" in voice_options:
        return bool(voice_options.get("cloned"))
    return True


def _resolve_xtts_model_path() -> Path | None:
    for key in ("VIDIOLINGUA_XTTS_MODEL_PATH", "XTTS_MODEL_PATH", "COQUI_XTTS_MODEL_PATH"):
        value = os.environ.get(key, "").strip()
        if value:
            return _normalize_xtts_model_dir(Path(value))
    candidate = PROJECT_ROOT / "models" / "xtts_v2"
    return candidate if candidate.exists() else None


def _normalize_xtts_model_dir(path: Path) -> Path:
    """Coqui XTTS expects the model directory, not the model.pth file."""
    path = Path(path)
    if path.name.lower() == "model.pth" or path.suffix.lower() == ".pth":
        return path.parent
    return path


def _find_xtts_checkpoint(model_path: Path) -> Path | None:
    exact = model_path / "model.pth"
    if exact.is_file():
        return exact
    for candidate in sorted(model_path.glob("*.pth")):
        name = candidate.name.lower()
        if name.startswith("speakers") or name == "speakers_xtts.pth":
            continue
        return candidate
    return None


def _assert_xtts_model_ready() -> None:
    model_path = _resolve_xtts_model_path()
    if not model_path:
        raise RuntimeError(
            "XTTS cloned voice mode requires local XTTS v2 model files. "
            "Run scripts/download_xtts_v2_model.ps1 -AgreeToCoquiTerms after accepting Coqui terms."
        )
    model_path = _normalize_xtts_model_dir(model_path)
    config_path = model_path / "config.json"
    checkpoint_path = _find_xtts_checkpoint(model_path)
    vocab_path = model_path / "vocab.json"
    tokenizer_path = model_path / "tokenizer.json"
    speakers_path = model_path / "speakers_xtts.pth"
    missing: list[str] = []
    if not config_path.is_file():
        missing.append("config.json")
    if not checkpoint_path:
        missing.append("model.pth or another .pth checkpoint")
    if not (vocab_path.is_file() or tokenizer_path.is_file()):
        missing.append("vocab.json or tokenizer.json")
    if missing:
        raise RuntimeError(
            f"XTTS cloned voice mode requires a complete model directory at {model_path}; "
            f"missing: {', '.join(missing)}. "
            "Run scripts/download_xtts_v2_model.ps1 -AgreeToCoquiTerms after accepting Coqui terms."
        )
    os.environ["VIDIOLINGUA_XTTS_MODEL_PATH"] = str(model_path)
    print(f"[Pipeline] XTTS model_dir: {model_path}")
    print(f"[Pipeline] XTTS config_path: {config_path}")
    print(f"[Pipeline] XTTS checkpoint_path: {checkpoint_path}")
    print(f"[Pipeline] XTTS vocab_path: {vocab_path if vocab_path.is_file() else tokenizer_path}")
    if speakers_path.is_file():
        print(f"[Pipeline] XTTS speakers_path: {speakers_path}")


PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = Path(os.environ.get("JOBS_DIR", str(PROJECT_ROOT / "jobs")))
XTTS_QUALITY_DEFAULTS = {
    "VIDIOLINGUA_XTTS_TEMP": "0.52",
    "VIDIOLINGUA_XTTS_REPETITION_PENALTY": "8.5",
    "VIDIOLINGUA_XTTS_MAX_CHARS": "180",
    "VIDIOLINGUA_XTTS_CROSSFADE_MS": "25.0",
    "VIDIOLINGUA_AUDIO_LOUDNESS_NORMALIZE": "false",
    "VIDIOLINGUA_AUDIO_TARGET_LUFS": "-16",
}
XTTS_ROUTER_LANGS = {
    "ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh",
}
INDICF5_ROUTER_LANGS = {"as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te"}


def _lang_base(language_code: str) -> str:
    code = (language_code or "").strip().lower().replace("_", "-").split("-")[0]
    return "or" if code == "od" else code


def _indic_voice_backend() -> str:
    backend = os.environ.get("VIDIOLINGUA_INDIC_VOICE_BACKEND", "sarvam").strip().lower()
    return backend if backend in {"sarvam", "indicf5", "disabled"} else "sarvam"


def _requires_indicf5_reference_text(languages: list[str]) -> bool:
    if _indic_voice_backend() != "indicf5":
        return False
    return any(_lang_base(lang) in INDICF5_ROUTER_LANGS and _lang_base(lang) not in XTTS_ROUTER_LANGS for lang in languages)


def _read_reference_text_from_env() -> str:
    text = os.environ.get("VIDIOLINGUA_REFERENCE_TEXT", "").strip()
    if text:
        return text
    path_value = os.environ.get("VIDIOLINGUA_REFERENCE_TEXT_PATH", "").strip()
    if path_value:
        path = Path(path_value)
        if not path.is_file():
            raise RuntimeError(f"Configured VIDIOLINGUA_REFERENCE_TEXT_PATH does not exist: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Configured VIDIOLINGUA_REFERENCE_TEXT_PATH is empty: {path}")
        return text
    return ""


def _apply_xtts_quality_defaults(env: dict[str, str]) -> None:
    for key, value in XTTS_QUALITY_DEFAULTS.items():
        env.setdefault(key, value)
    print(
        "[Pipeline] XTTS quality settings: "
        f"temp={env.get('VIDIOLINGUA_XTTS_TEMP')} "
        f"repetition_penalty={env.get('VIDIOLINGUA_XTTS_REPETITION_PENALTY')} "
        f"max_chars={env.get('VIDIOLINGUA_XTTS_MAX_CHARS')} "
        f"crossfade_ms={env.get('VIDIOLINGUA_XTTS_CROSSFADE_MS')} "
        f"loudness_normalize={env.get('VIDIOLINGUA_AUDIO_LOUDNESS_NORMALIZE')} "
        f"target_lufs={env.get('VIDIOLINGUA_AUDIO_TARGET_LUFS')}"
    )


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
JOBS_DIR = Path(os.environ.get("JOBS_DIR", str(PROJECT_ROOT / "jobs")))

# ML Python runtimes (Micro-Environments)
# Set these in backend/.env to point at their respective isolated virtual environments
def _get_python(env_var: str, default_venv: str, legacy_env_var: str | None = None) -> str:
    py = os.environ.get(env_var, "").strip()
    if not py and legacy_env_var:
        py = os.environ.get(legacy_env_var, "").strip()
    if py and Path(py).is_file():
        return py
    candidate = PROJECT_ROOT / default_venv / "Scripts" / "python.exe"
    if candidate.is_file():
        return str(candidate)
    fallback = os.environ.get("PYTHON", "python")
    print(f"[Pipeline] WARNING: {env_var} not set — using {fallback!r}. "
          f"ML stages may fail on Python 3.13. Set {env_var} in backend/.env.")
    return fallback

def _whisperx_python() -> str:
    return _get_python("VIDIOLINGUA_ASR_PYTHON", ".venv_asr", "PYTHON_WHISPERX")

def _tts_python() -> str:
    return _get_python("VIDIOLINGUA_TTS_PYTHON", ".venv_tts", "PYTHON_TTS")

def _demucs_python() -> str:
    return _get_python("VIDIOLINGUA_BGM_PYTHON", ".venv_bgm", "PYTHON_DEMUCS")

def _musetalk_python() -> str:
    return _get_python("VIDIOLINGUA_MUSETALK_PYTHON", ".venv_musetalk", "PYTHON_MUSETALK")

def _wav2lip_python() -> str:
    return _get_python("VIDIOLINGUA_WAV2LIP_PYTHON", ".venv_tts", "PYTHON_WAV2LIP")

def _lipsync_mode() -> str:
    raw_mode = os.environ.get("VIDIOLINGUA_LIPSYNC_MODE", "").strip().lower()
    if raw_mode in {"ffmpeg_mux", "wav2lip_optional", "wav2lip_required"}:
        return raw_mode
    legacy_engine = os.environ.get("VIDIOLINGUA_LIPSYNC_ENGINE", "").strip().lower()
    if legacy_engine == "ffmpeg":
        return "ffmpeg_mux"
    if legacy_engine == "wav2lip":
        return "wav2lip_required" if _env_true("VIDIOLINGUA_REQUIRE_VISUAL_LIPSYNC") else "wav2lip_optional"
    if _env_true("VIDIOLINGUA_REQUIRE_VISUAL_LIPSYNC"):
        return "wav2lip_required"
    return "ffmpeg_mux"

def _wav2lip_preflight_report(wav2lip_dir: str | None = None, checkpoint: str | None = None) -> dict:
    try:
        from tools.validate_wav2lip_runtime import build_preflight_report

        return build_preflight_report(wav2lip_dir=wav2lip_dir, checkpoint=checkpoint)
    except Exception as exc:
        return {
            "ok": False,
            "selected_python": None,
            "wav2lip_dir": wav2lip_dir,
            "checkpoint_path": checkpoint,
            "checkpoint_exists": bool(checkpoint and Path(checkpoint).is_file()),
            "errors": [f"Wav2Lip preflight failed: {exc}"],
            "warnings": [],
        }

def _summarize_error(value: object, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        text = "; ".join(str(item) for item in value if item)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text[:limit] if text else None

def _lipsync_python() -> str:
    if os.environ.get("VIDIOLINGUA_MUSETALK_DIR", "").strip():
        return _musetalk_python()
    return _api_python()

def _api_python() -> str:
    return _get_python("VIDIOLINGUA_API_PYTHON", ".venv_api", "PYTHON_API")

def _gfpgan_python() -> str:
    return _get_python("VIDIOLINGUA_GFP_GAN_PYTHON", ".venv_gfpgan", "PYTHON_GFPGAN")

ASR_INPUT = PROJECT_ROOT / "asr" / "input"
ASR_OUTPUT = PROJECT_ROOT / "asr" / "output"
TRANS_INPUT = PROJECT_ROOT / "translation" / "input"
TRANS_OUTPUT = PROJECT_ROOT / "translation" / "output"
TTS_INPUT = PROJECT_ROOT / "tts" / "input"
TTS_OUTPUT = PROJECT_ROOT / "tts" / "output"
LIPSYNC_INPUT = PROJECT_ROOT / "lipsync" / "input"
LIPSYNC_OUTPUT = PROJECT_ROOT / "lipsync" / "output"


def _ensure_dirs():
    for d in (
        ASR_INPUT, ASR_OUTPUT, TRANS_INPUT, TRANS_OUTPUT,
        TTS_INPUT, TTS_OUTPUT, LIPSYNC_INPUT, LIPSYNC_OUTPUT,
    ):
        d.mkdir(parents=True, exist_ok=True)


def _clear_dir(d: Path):
    if d.exists():
        for f in d.iterdir():
            if f.is_file():
                f.unlink()
            else:
                shutil.rmtree(f, ignore_errors=True)


def _copy_all(src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    if src.exists():
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)


def _extract_voice_sample(video_path: Path, output_path: Path, duration_s: int = 30) -> None:
    """
    Extract a raw voice sample WAV from the video (includes BGM).
    This is the FALLBACK method. Prefer _extract_clean_voice_sample() which
    runs Demucs first to remove background music for better XTTS cloning.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-t", str(duration_s),
        "-vn", "-ac", "1", "-ar", "22050",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Voice sample extraction failed: {result.stderr or result.stdout}")


def _extract_clean_voice_sample(
    video_path: Path,
    work_dir: Path,
    target_duration_s: float = 20.0,
) -> Path:
    """
    Extract a CLEAN voice-only sample for XTTS cloning by:
    1. Extracting full audio from video
    2. Running Demucs to separate vocals from BGM
    3. Finding the best 10-20s window of clean speech (highest RMS energy)
    4. Returning the clean vocal segment path

    This is critical: XTTS voice cloning quality degrades severely when the
    reference audio contains background music or noise.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    raw_audio = work_dir / "raw_audio_for_cloning.wav"
    clean_vocals = work_dir / "clean_vocals.wav"
    best_segment = work_dir / "best_voice_segment.wav"

    # Step 1: Extract full audio
    print("[Pipeline] Extracting audio for clean voice sample...")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(raw_audio),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {r.stderr or r.stdout}")

    # Step 2: Run Demucs (via ML python) to separate vocals
    print("[Pipeline] Running Demucs to isolate clean vocals for XTTS reference...")
    demucs_out = work_dir / "demucs_out"
    demucs_out.mkdir(parents=True, exist_ok=True)
    demucs_cmd = [
        _demucs_python(), "-m", "demucs",
        "--two-stems", "vocals",
        "--model", os.environ.get("VIDIOLINGUA_DEMUCS_MODEL", "htdemucs"),
        "--out", str(demucs_out),
        str(raw_audio),
    ]
    r = subprocess.run(
        demucs_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        raise RuntimeError(f"Demucs vocal separation failed: {r.stderr or r.stdout}")

    # Locate vocals.wav from Demucs output
    model_name = os.environ.get("VIDIOLINGUA_DEMUCS_MODEL", "htdemucs")
    stem_name = raw_audio.stem
    vocals_path = None
    for candidate in demucs_out.rglob("vocals.wav"):
        vocals_path = candidate
        break
    if not vocals_path or not vocals_path.is_file():
        raise RuntimeError(f"Demucs vocals.wav not found in {demucs_out}")

    # Step 3: Convert vocals to 22050 Hz mono for XTTS
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(vocals_path),
         "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
         str(clean_vocals)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        raise RuntimeError(f"Vocal conversion failed: {r.stderr}")

    # Step 4: Find best speech segment (highest RMS energy window)
    # This picks the most active speech window, avoiding silence/music bleed
    best_start = _find_best_speech_window(clean_vocals, window_s=target_duration_s)
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(clean_vocals),
         "-ss", str(best_start),
         "-t", str(target_duration_s),
         "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
         str(best_segment)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        # Fallback: just use the full vocals file
        import shutil
        shutil.copy2(clean_vocals, best_segment)

    print(f"[Pipeline] Clean voice segment ready: {best_segment.name} "
          f"(from {best_start:.1f}s, target {target_duration_s:.0f}s)")
    return best_segment


def _find_best_speech_window(audio_path: Path, window_s: float = 20.0) -> float:
    """
    Find the start timestamp of the highest-energy window of length window_s
    in audio_path. Uses numpy RMS energy on 1-second chunks.
    Returns start time in seconds (default 0.0 if numpy unavailable).
    """
    current_manifest_stage = None
    try:
        import wave
        import struct
        import numpy as np

        with wave.open(str(audio_path), 'rb') as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        chunk_size = sr  # 1-second chunks
        n_chunks = len(samples) // chunk_size
        if n_chunks == 0:
            return 0.0

        rms = np.array([
            np.sqrt(np.mean(samples[i * chunk_size:(i + 1) * chunk_size] ** 2))
            for i in range(n_chunks)
        ])

        window_chunks = max(1, int(window_s))
        if window_chunks >= n_chunks:
            return 0.0

        # Sliding window sum of RMS
        best_start_chunk = 0
        best_energy = -1.0
        for i in range(n_chunks - window_chunks + 1):
            energy = rms[i:i + window_chunks].sum()
            if energy > best_energy:
                best_energy = energy
                best_start_chunk = i

        return float(best_start_chunk)  # seconds (1 chunk = 1 second)
    except Exception as e:
        print(f"[Pipeline] RMS window search failed ({e}), using t=0")
        return 0.0


def _probe_duration(audio_path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return float(r.stdout.strip())
    except (TypeError, ValueError):
        return 0.0


def _probe_media_metadata(media_path: Path) -> dict:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
            "-of", "json",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        return {"output_validation_passed": False, "output_validation_error": (r.stderr or r.stdout or "").strip()}
    try:
        data = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return {"output_validation_passed": False, "output_validation_error": "ffprobe returned invalid JSON"}

    streams = data.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    meta = {
        "output_validation_passed": bool(video_stream and audio_stream),
        "output_has_video_stream": bool(video_stream),
        "output_has_audio_stream": bool(audio_stream),
    }
    fmt = data.get("format") or {}
    try:
        meta["final_mp4_duration_s"] = round(float(fmt.get("duration")), 3)
    except (TypeError, ValueError):
        pass
    try:
        meta["final_mp4_size_mb"] = round(float(fmt.get("size")) / (1024 * 1024), 3)
    except (TypeError, ValueError):
        pass
    if video_stream:
        meta["video_codec"] = video_stream.get("codec_name")
        if video_stream.get("width") and video_stream.get("height"):
            meta["video_resolution"] = f"{video_stream.get('width')}x{video_stream.get('height')}"
        frame_rate = str(video_stream.get("avg_frame_rate") or "")
        if "/" in frame_rate:
            try:
                numerator, denominator = frame_rate.split("/", 1)
                if float(denominator) != 0:
                    meta["video_fps"] = round(float(numerator) / float(denominator), 3)
            except (TypeError, ValueError):
                pass
    if audio_stream:
        meta["audio_codec"] = audio_stream.get("codec_name")
        meta["audio_sample_rate"] = audio_stream.get("sample_rate")
        meta["audio_channels"] = audio_stream.get("channels")
    return meta


def _load_translation_evidence(paths: list[Path]) -> dict:
    evidence: dict[str, object] = {}
    for path in paths:
        if path.suffix.lower() != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("translation_engine"):
            evidence["translation_backend"] = data.get("translation_engine")
        if data.get("source_language"):
            evidence["translation_source_language"] = data.get("source_language")
        if data.get("language"):
            evidence["target_language"] = data.get("language")
        qa = data.get("translation_qa")
        if isinstance(qa, dict):
            evidence["translation_qa_status"] = qa.get("status")
            evidence["translation_qa_checks_passed"] = qa.get("checksPassed")
            evidence["translation_qa_warnings_count"] = qa.get("warningsCount")
            evidence["translation_qa_errors_count"] = qa.get("errorsCount")
            evidence["translation_qa_empty_segments"] = qa.get("emptySegments")
            evidence["translation_qa_script_match"] = qa.get("scriptMatch")
            evidence["translation_qa_number_issues"] = qa.get("numberIssues")
            evidence["translation_qa_entity_issues"] = qa.get("entityIssues")
            evidence["translation_qa_expansion_ratio_warnings"] = qa.get("expansionRatioWarnings")
            evidence["translation_qa_report_path"] = qa.get("reportPath")
        linguistic = data.get("linguistic_integrity")
        if isinstance(linguistic, dict):
            evidence["linguistic_integrity_status"] = linguistic.get("status")
            evidence["linguistic_integrity_score"] = linguistic.get("score")
            evidence["linguistic_integrity_script_status"] = linguistic.get("scriptStatus")
            evidence["linguistic_integrity_empty_segments"] = linguistic.get("emptySegments")
            evidence["linguistic_integrity_number_warnings"] = linguistic.get("numberWarnings")
            evidence["linguistic_integrity_name_warnings"] = linguistic.get("nameWarnings")
            evidence["linguistic_integrity_expansion_warnings"] = linguistic.get("expansionWarnings")
            evidence["linguistic_integrity_report_path"] = linguistic.get("reportPath")
        policy = data.get("translation_policy")
        if isinstance(policy, dict):
            if "fallback_used" in policy:
                evidence["translation_fallback_used"] = bool(policy.get("fallback_used"))
            if "indictrans2_supported_pair" in policy:
                evidence["indictrans2_supported_pair"] = bool(policy.get("indictrans2_supported_pair"))
        if evidence:
            return evidence
    return evidence


def _is_translation_payload(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    name = path.name.lower()
    return not (
        name == "translation_qa_report.json"
        or name.endswith(".translation_qa_report.json")
        or name == "linguistic_integrity_report.json"
        or name.endswith(".linguistic_integrity_report.json")
    )


def _translation_qa_summary_from_evidence(evidence: dict) -> dict:
    if not evidence:
        return {
            "status": None,
            "checksPassed": None,
            "warningsCount": None,
            "errorsCount": None,
            "emptySegments": None,
            "scriptMatch": None,
            "numberIssues": None,
            "entityIssues": None,
            "expansionRatioWarnings": None,
            "reportPath": None,
        }
    return {
        "status": evidence.get("translation_qa_status"),
        "checksPassed": evidence.get("translation_qa_checks_passed"),
        "warningsCount": evidence.get("translation_qa_warnings_count"),
        "errorsCount": evidence.get("translation_qa_errors_count"),
        "emptySegments": evidence.get("translation_qa_empty_segments"),
        "scriptMatch": evidence.get("translation_qa_script_match"),
        "numberIssues": evidence.get("translation_qa_number_issues"),
        "entityIssues": evidence.get("translation_qa_entity_issues"),
        "expansionRatioWarnings": evidence.get("translation_qa_expansion_ratio_warnings"),
        "reportPath": evidence.get("translation_qa_report_path"),
    }


def _linguistic_integrity_summary_from_evidence(evidence: dict) -> dict:
    return {
        "status": evidence.get("linguistic_integrity_status"),
        "score": evidence.get("linguistic_integrity_score"),
        "scriptStatus": evidence.get("linguistic_integrity_script_status"),
        "emptySegments": evidence.get("linguistic_integrity_empty_segments"),
        "numberWarnings": evidence.get("linguistic_integrity_number_warnings"),
        "nameWarnings": evidence.get("linguistic_integrity_name_warnings"),
        "expansionWarnings": evidence.get("linguistic_integrity_expansion_warnings"),
        "reportPath": evidence.get("linguistic_integrity_report_path"),
    }


def _load_phonetic_evidence(paths: list[Path]) -> dict:
    evidence: dict[str, object] = {}
    for path in paths:
        if path.suffix.lower() != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        report = data
        if "reports" in data and isinstance(data.get("reports"), dict):
            first = next((item for item in data["reports"].values() if isinstance(item, dict)), {})
            report = first if first else data
        evidence["phonetic_resolution_status"] = report.get("status") or data.get("status")
        evidence["phonetic_risk_score"] = report.get("phonetic_risk_score_0_100")
        evidence["phonetic_dictionary_used"] = bool(report.get("dictionary_used"))
        evidence["phonetic_terms_detected"] = len(report.get("terms_detected") or [])
        evidence["phonetic_acronyms_detected"] = len(report.get("acronyms_detected") or [])
        evidence["phonetic_ambiguity_warnings"] = len(report.get("ambiguity_warnings") or [])
        evidence["phonetic_resolution_report_path"] = path.name
        if evidence:
            return evidence
    return evidence


def _phonetic_resolution_summary_from_evidence(evidence: dict) -> dict:
    return {
        "status": evidence.get("phonetic_resolution_status"),
        "phoneticRiskScore": evidence.get("phonetic_risk_score"),
        "termsDetected": evidence.get("phonetic_terms_detected"),
        "acronymsDetected": evidence.get("phonetic_acronyms_detected"),
        "ambiguityWarnings": evidence.get("phonetic_ambiguity_warnings"),
        "dictionaryUsed": evidence.get("phonetic_dictionary_used"),
        "reportPath": evidence.get("phonetic_resolution_report_path"),
    }


def _alignment_level_analysis(asr_json_paths: list[Path]) -> dict:
    total_segments = 0
    segments_with_words = 0
    total_words = 0
    timed_words = 0
    for path in asr_json_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        segments = data.get("segments") if isinstance(data.get("segments"), list) else []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            total_segments += 1
            words = segment.get("words") if isinstance(segment.get("words"), list) else []
            segment_timed_words = 0
            for word in words:
                if not isinstance(word, dict):
                    continue
                total_words += 1
                if isinstance(word.get("start"), (int, float)) and isinstance(word.get("end"), (int, float)):
                    timed_words += 1
                    segment_timed_words += 1
            if segment_timed_words:
                segments_with_words += 1

    coverage = (segments_with_words / total_segments) if total_segments else 0.0
    alignment_level = "word" if timed_words > 0 and coverage >= 0.5 else "segment" if total_segments else "unknown"
    warnings = []
    if alignment_level == "segment":
        warnings.append("Only segment-level timestamps available; visual mouth alignment may be approximate.")
    elif alignment_level == "unknown":
        warnings.append("No ASR timing evidence was available for lip-sync alignment.")
    return {
        "alignment_level": alignment_level,
        "alignment_word_count": timed_words,
        "alignment_word_coverage_ratio": round(coverage, 3) if total_segments else None,
        "alignment_segments_with_words": segments_with_words,
        "alignment_segment_count": total_segments,
        "alignment_warnings": warnings,
    }


def _prosody_summary(profile: dict | None, plan: dict | None = None, hubert_report: dict | None = None) -> dict:
    profile = profile if isinstance(profile, dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    hubert_report = hubert_report if isinstance(hubert_report, dict) else {}
    profile_global = profile.get("global") if isinstance(profile.get("global"), dict) else {}
    plan_global = plan.get("global") if isinstance(plan.get("global"), dict) else {}
    hubert_global = hubert_report.get("global") if isinstance(hubert_report.get("global"), dict) else {}
    return {
        "status": profile.get("summary", {}).get("status") if isinstance(profile.get("summary"), dict) else profile.get("status"),
        "preset": plan.get("preset"),
        "speechRateClass": profile_global.get("speech_rate_class"),
        "averageSpeechRateWpm": profile_global.get("speech_rate_wpm"),
        "pauseCount": profile_global.get("pause_count"),
        "averagePauseSec": profile_global.get("average_pause_sec"),
        "durationPressure": plan_global.get("duration_pressure"),
        "maxDurationPressureRatio": plan_global.get("max_duration_pressure_ratio"),
        "hubertStatus": hubert_report.get("status"),
        "hubertModel": hubert_report.get("hubert_model") or hubert_report.get("model"),
        "hubertProsodySimilarity": hubert_global.get("prosody_similarity_score_0_100"),
        "adapterStatus": hubert_report.get("adapter_status"),
        "adapterConfidence": hubert_global.get("confidence"),
        "warnings": [
            *((profile.get("warnings") or []) if isinstance(profile.get("warnings"), list) else []),
            *((plan.get("warnings") or []) if isinstance(plan.get("warnings"), list) else []),
            *((hubert_report.get("warnings") or []) if isinstance(hubert_report.get("warnings"), list) else []),
        ],
    }


def _safe_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _voice_route_evidence(languages: list[str], cloning_required: bool) -> dict:
    bases = [_lang_base(lang) for lang in languages]
    uses_xtts = any(lang in XTTS_ROUTER_LANGS for lang in bases)
    uses_indic = any(lang in INDICF5_ROUTER_LANGS and lang not in XTTS_ROUTER_LANGS for lang in bases)
    indic_backend = _indic_voice_backend()
    voice_backend = "XTTS" if uses_xtts and cloning_required else "Sarvam" if uses_indic and indic_backend == "sarvam" else "configured router"
    return {
        "voice_backend": voice_backend,
        "xtts_selected": voice_backend == "XTTS",
        "sarvam_selected": voice_backend == "Sarvam",
        "indicf5_loaded": False,
        "generic_fallback_used": False,
        "exact_voice_clone": voice_backend == "XTTS",
        "managed_tts": voice_backend == "Sarvam",
    }


def _advanced_metric_requirements() -> dict:
    return {
        "asr_accuracy": {"status": "requires_ground_truth"},
        "bleu": {"status": "requires_reference_translation"},
        "mos": {"status": "requires_human_or_evaluator"},
        "lse_c": {"status": "requires_lipsync_evaluator"},
        "voice_similarity": {"status": "requires_speaker_embedding_evaluator"},
    }


def _reference_not_required_analysis() -> dict:
    return {
        "mode": "none",
        "status": "not_required",
        "path": None,
        "duration_sec": None,
        "sample_rate": None,
        "channels": None,
        "peak": None,
        "validation_passed": None,
        "reason": "Sarvam managed Indian-language TTS does not use exact speaker cloning reference audio.",
    }


def _normalize_reference_mode(raw: object) -> str:
    value = str(raw or "").strip().lower().replace("-", "_")
    aliases = {
        "auto": "auto_extract",
        "auto_reference": "auto_extract",
        "auto_extracted": "auto_extract",
        "not_required": "none",
        "missing": "none",
    }
    normalized = aliases.get(value, value)
    return normalized if normalized in {"uploaded", "auto_extract", "none"} else "none"


def _sarvam_auto_extract_analysis(speaker_report: dict | None, speaker_analysis_dir: Path) -> dict:
    references_payload: dict = {}
    references_path = speaker_analysis_dir / "references" / "speaker_reference_candidates.json"
    if references_path.is_file():
        try:
            references_payload = json.loads(references_path.read_text(encoding="utf-8"))
        except Exception:
            references_payload = {}
    references = references_payload.get("references") if isinstance(references_payload, dict) else {}
    first_reference = None
    if isinstance(references, dict):
        first_reference = next(
            (ref for ref in references.values() if isinstance(ref, dict) and ref.get("path")),
            None,
        )
    warnings = []
    if isinstance(speaker_report, dict):
        warnings.extend(speaker_report.get("warnings") or [])
    if isinstance(references_payload, dict):
        warnings.extend(references_payload.get("warnings") or [])
    if first_reference:
        return {
            "mode": "auto_extract",
            "status": "computed",
            "path": first_reference.get("path"),
            "duration_sec": first_reference.get("duration_sec"),
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "validation_passed": None,
            "reason": "Auto-analysis produced a speaker reference candidate for Sarvam voice-fit hints. Sarvam remains managed TTS, not exact cloning.",
            "warnings": warnings,
        }
    return {
        "mode": "auto_extract",
        "status": "unavailable",
        "path": None,
        "duration_sec": None,
        "sample_rate": None,
        "channels": None,
        "peak": None,
        "validation_passed": None,
        "reason": "Auto-analysis did not produce a usable speaker profile hint; Sarvam will use the default managed voice.",
        "warnings": warnings or ["Speaker profile hint unavailable; default Sarvam voice will be used."],
    }


def _default_sarvam_male_speaker() -> str:
    return (
        os.environ.get("VIDIOLINGUA_SARVAM_DEFAULT_MALE_SPEAKER", "").strip()
        or "shubh"
    )


def _apply_default_single_speaker_labels(asr_json_paths: list[Path], speaker_id: str = "SPEAKER_00") -> int:
    labeled_segments = 0
    for json_path in asr_json_paths:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            segments = payload.get("segments")
            if not isinstance(segments, list):
                continue
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                segment["speaker"] = segment.get("speaker") or speaker_id
                segment["speaker_id"] = segment.get("speaker_id") or speaker_id
                segment["speaker_ambiguous"] = False
                labeled_segments += 1
            payload.setdefault("diarization", {})
            if isinstance(payload["diarization"], dict):
                payload["diarization"].update(
                    {
                        "enabled": False,
                        "status": "default_single_speaker",
                        "reason": "Speaker diarization was unavailable; all ASR segments were assigned to one default speaker for managed Sarvam voice selection.",
                    }
                )
            json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"[Pipeline] Default speaker labeling skipped for {json_path}: {exc}")
    return labeled_segments


def _write_default_sarvam_voice_plan(
    path: Path,
    *,
    target_language: str,
    reason: str,
    segment_count: int = 0,
) -> dict:
    male_speaker = _default_sarvam_male_speaker()
    plan = {
        "status": "defaulted",
        "target_language": _lang_base(target_language),
        "voice_backend": "sarvam",
        "managed_tts": True,
        "exact_voice_clone": False,
        "speakers": [
            {
                "speaker_id": "SPEAKER_00",
                "segment_count": max(0, int(segment_count or 0)),
                "total_speech_sec": 0.0,
                "reference_audio_path": None,
                "voice_profile_hint": "masculine_voice_fit",
                "confidence": "low",
                "hint_source": "default_policy",
                "selected_tts_voice": male_speaker,
                "selection_reason": reason,
                "override_supported": True,
                "managed_tts": True,
                "exact_voice_clone": False,
                "sarvam_is_managed_tts_not_cloning": True,
            }
        ],
        "warnings": [
            "Speaker diarization/profile analysis was unavailable, so Sarvam uses the default male managed-TTS speaker.",
            "Sarvam is managed TTS, not exact voice cloning.",
        ],
        "errors": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return plan


def _reference_audio_analysis(path: str | Path | None, mode: str) -> dict:
    if not path:
        return {
            "mode": mode,
            "path": None,
            "duration_sec": None,
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "validation_passed": False,
            "reason": "Reference audio was required but no path was available.",
        }
    try:
        from voice.audio_validation import validate_reference_audio

        stats = validate_reference_audio(path, min_duration_s=6.0, max_duration_s=60.0)
        return {
            "mode": mode,
            "path": str(path),
            "duration_sec": round(stats.duration_s, 3),
            "sample_rate": stats.sample_rate,
            "channels": stats.channels,
            "peak": round(stats.peak, 6),
            "validation_passed": True,
        }
    except Exception as exc:
        return {
            "mode": mode,
            "path": str(path),
            "duration_sec": None,
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "validation_passed": False,
            "reason": str(exc),
        }


def _tts_audio_validation_analysis(tts_files: list[Path]) -> dict:
    if not tts_files:
        return {
            "tts_wav_exists": False,
            "duration_sec": None,
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "normalization_applied": None,
            "validation_passed": False,
        }
    path = tts_files[0]
    try:
        from voice.audio_validation import analyze_audio

        stats = analyze_audio(path)
        sidecars = list(path.parent.glob(f"{path.stem}.sarvam_clean{path.suffix}"))
        return {
            "tts_wav_exists": True,
            "path": str(path),
            "duration_sec": round(stats.duration_s, 3),
            "sample_rate": stats.sample_rate,
            "channels": stats.channels,
            "peak": round(stats.peak, 6),
            "clipping_ratio": round(stats.clipping_ratio, 6),
            "normalization_applied": bool(sidecars),
            "validation_passed": True,
        }
    except Exception as exc:
        return {
            "tts_wav_exists": True,
            "path": str(path),
            "duration_sec": None,
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "normalization_applied": None,
            "validation_passed": False,
            "reason": str(exc),
        }


def _output_inspection_analysis(results_dir: Path, metrics: dict) -> dict:
    final_exists = bool(metrics.get("final_mp4_count"))
    file_size_bytes = None
    final_mp4 = next(
        (path for path in results_dir.iterdir() if path.is_file() and path.suffix.lower() == ".mp4" and "_dubbed_" in path.stem),
        None,
    )
    if final_mp4:
        file_size_bytes = final_mp4.stat().st_size
    return {
        "final_mp4_exists": final_exists,
        "duration_sec": metrics.get("final_mp4_duration_s"),
        "file_size_bytes": file_size_bytes,
        "video_codec": metrics.get("video_codec"),
        "resolution": metrics.get("video_resolution"),
        "fps": metrics.get("video_fps"),
        "audio_codec": metrics.get("audio_codec"),
        "audio_sample_rate": metrics.get("audio_sample_rate"),
        "audio_channels": metrics.get("audio_channels"),
        "validation_passed": metrics.get("output_validation_passed"),
    }


def _build_metrics_report_for_job(job_dir: Path) -> dict:
    from evaluation.worker import run_evaluation

    return run_evaluation(job_dir, job_dir / "evaluation" / "metrics_report.json")


def _make_reference_clip(video_path: Path, start_s: float, duration_s: float, output_path: Path) -> bool:
    """Trim one speech segment and lightly denoise/normalize it for voice cloning."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_s = max(0.0, start_s)
    duration_s = max(0.2, duration_s)
    filters = [
        "highpass=f=70,lowpass=f=7600,afftdn=nf=-25,loudnorm=I=-18:TP=-3:LRA=11",
        "highpass=f=70,lowpass=f=7600,loudnorm=I=-18:TP=-3:LRA=11",
    ]
    for audio_filter in filters:
        r = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_s:.3f}",
                "-i", str(video_path),
                "-t", f"{duration_s:.3f}",
                "-vn",
                "-af", audio_filter,
                "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 2048:
            return True
    return False


def _concat_reference_clips(clip_paths: list[Path], output_path: Path) -> bool:
    if not clip_paths:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
        dir=output_path.parent,
    ) as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve().as_posix()}'\n")
        list_file = f.name
    try:
        r = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-af", "loudnorm=I=-18:TP=-3:LRA=11",
                "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 2048
    finally:
        Path(list_file).unlink(missing_ok=True)


def _build_speaker_reference_wavs(
    video_path: Path,
    asr_json_paths: list[Path],
    work_dir: Path,
    target_duration_s: float = 24.0,
    min_duration_s: float = 6.0,
) -> dict[str, str]:
    """
    Build clean per-speaker reference WAVs from ASR timestamps.

    The earlier fallback uses the first 30 seconds of the video, which may include
    music, silence, or another speaker. This routine uses the ASR timeline to
    choose the longest speech spans per speaker, trims them, denoises them, and
    concatenates enough material for XTTS or cloud cloning.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = {}

    for json_path in asr_json_paths:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for seg in data.get("segments", []):
            try:
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start))
            except (TypeError, ValueError):
                continue
            text = (seg.get("text") or "").strip()
            duration = end - start
            if duration < 0.75 or not text:
                continue
            speaker = str(seg.get("speaker") or "SPEAKER_00")
            grouped.setdefault(speaker, []).append(
                {"start": start, "end": end, "duration": duration, "text": text}
            )

    refs: dict[str, str] = {}
    for speaker, segments in grouped.items():
        chosen: list[dict] = []
        total = 0.0
        for seg in sorted(segments, key=lambda s: s["duration"], reverse=True):
            chosen.append(seg)
            total += min(seg["duration"], 8.0)
            if total >= target_duration_s:
                break

        if not chosen:
            continue

        speaker_dir = work_dir / speaker
        speaker_dir.mkdir(parents=True, exist_ok=True)
        clips: list[Path] = []
        for i, seg in enumerate(sorted(chosen, key=lambda s: s["start"])):
            padded_start = max(0.0, seg["start"] - 0.05)
            padded_duration = min(seg["duration"] + 0.10, 8.0)
            clip_path = speaker_dir / f"clip_{i:03d}.wav"
            if _make_reference_clip(video_path, padded_start, padded_duration, clip_path):
                clips.append(clip_path)

        output_path = work_dir / f"{speaker}_reference.wav"
        if _concat_reference_clips(clips, output_path):
            duration = _probe_duration(output_path)
            if duration >= min_duration_s:
                ref_text = " ".join(
                    (seg.get("text") or "").strip()
                    for seg in sorted(chosen, key=lambda s: s["start"])
                    if (seg.get("text") or "").strip()
                )
                output_path.with_suffix(".txt").write_text(ref_text, encoding="utf-8")
                refs[speaker] = str(output_path)
                print(
                    f"[Pipeline] Speaker reference ready: {speaker} "
                    f"({duration:.1f}s from {len(clips)} clips)"
                )
            else:
                print(
                    f"[Pipeline] Speaker reference too short for {speaker}: "
                    f"{duration:.1f}s"
                )

    return refs


# ---------------------------------------------------------------------------
# Background execution
# ---------------------------------------------------------------------------

def run_pipeline_background(
    job_id: str,
    video_path: str,
    languages: list[str],
    source_language: str | None = None,
    voice_options: dict | None = None,
    voice_sample_path: str | None = None,
    include_captions: bool = False,
    run_source: str = "api",
) -> None:
    """Start pipeline in a background thread."""
    def run():
        run_pipeline(
            job_id,
            video_path,
            languages,
            source_language,
            voice_options,
            voice_sample_path,
            include_captions=include_captions,
            run_source=run_source,
        )
    t = threading.Thread(target=run, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    job_id: str,
    video_path: str,
    languages: list[str],
    source_language: str | None = None,
    voice_options: dict | None = None,
    voice_sample_path: str | None = None,
    include_captions: bool = False,
    run_source: str = "api",
) -> None:
    start_time = time.time()
    job_dir = JOBS_DIR / job_id
    results_dir = job_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = job_manifest.manifest_path_for_job(job_dir)
    voice_options = voice_options or {}
    captions_requested = bool(
        include_captions
        or _option_true(voice_options.get("includeCaptions"))
        or _option_true(voice_options.get("captionsRequested"))
        or _option_true(voice_options.get("include_captions"))
    )
    voice_options["includeCaptions"] = captions_requested
    voice_options["captionsRequested"] = captions_requested

    # Make original video available for download
    job_manifest.create_manifest(
        job_dir,
        job_id,
        input_video_path=video_path,
        reference_audio_path=voice_sample_path,
        auto_reference_enabled=bool((voice_options or {}).get("autoReference") or (voice_options or {}).get("auto_reference")),
        target_language=languages,
        source_language=source_language,
        mode=os.environ.get("VIDIOLINGUA_PIPELINE_MODE", "practical"),
        run_source=run_source,
        output_dir=job_dir,
        captions_requested=captions_requested,
    )
    job_manifest.start_stage(manifest_path, "receive_upload", input_artifacts=[video_path])
    try:
        shutil.copy2(video_path, results_dir / "input_video.mp4")
        job_manifest.register_artifact(manifest_path, "source_video", results_dir / "input_video.mp4", stage="receive_upload", kind="video", role="output")
    except Exception:
        job_manifest.register_warning(manifest_path, "Could not copy original video into results folder.", stage="receive_upload")
    job_manifest.complete_stage(manifest_path, "receive_upload", output_artifacts=[results_dir / "input_video.mp4"])

    # Per-job stage directories
    asr_in = job_dir / "asr" / "input"
    asr_out = job_dir / "asr" / "output"
    trans_in = job_dir / "translation" / "input"
    trans_out = job_dir / "translation" / "output"
    tts_in = job_dir / "tts" / "input"
    tts_out = job_dir / "tts" / "output"
    lipsync_in = job_dir / "lipsync" / "input"
    lipsync_out = job_dir / "lipsync" / "output"
    logs_dir = job_dir / "logs"
    uvr5_work = job_dir / "uvr5"
    prosody_dir = job_dir / "prosody"
    speaker_analysis_dir = job_dir / "speaker_analysis"
    for d in (asr_in, asr_out, trans_in, trans_out, tts_in, tts_out,
              lipsync_in, lipsync_out, logs_dir, uvr5_work, prosody_dir, speaker_analysis_dir):
        d.mkdir(parents=True, exist_ok=True)

    video_path = Path(video_path)
    print(f"[Pipeline] Input video: {video_path}")
    print(f"[Pipeline] Target languages: {', '.join(languages)}")
    api_base = os.environ.get("API_BASE_URL", "http://localhost:8000")
    caption_metadata: list[dict] = []
    caption_artifact_paths: list[Path] = []
    cloning_required = _voice_cloning_required(voice_options)
    language_bases = [_lang_base(lang) for lang in languages]
    xtts_targets = [lang for lang in language_bases if lang in XTTS_ROUTER_LANGS]
    sarvam_targets = [
        lang
        for lang in language_bases
        if lang in INDICF5_ROUTER_LANGS and lang not in XTTS_ROUTER_LANGS and _indic_voice_backend() == "sarvam"
    ]
    if cloning_required and not xtts_targets:
        cloning_required = False
        voice_options["cloned"] = False
        voice_options["mode"] = "managed"
    auto_reference_requested = bool(
        voice_options.get("autoReference") or voice_options.get("auto_reference")
    )
    requested_reference_mode = _normalize_reference_mode(
        voice_options.get("referenceMode") or voice_options.get("reference_mode")
    )
    auto_reference_requested = auto_reference_requested or requested_reference_mode == "auto_extract"
    resolved_xtts_model_path = None
    if cloning_required and xtts_targets:
        _assert_xtts_model_ready()
        resolved_xtts_model_path = _resolve_xtts_model_path()
    user_supplied_voice_sample = bool(voice_sample_path)
    reference_mode = "uploaded" if user_supplied_voice_sample else "auto_extract" if auto_reference_requested else "none"
    voice_options["referenceMode"] = reference_mode
    voice_options["reference_mode"] = reference_mode
    voice_options["autoReference"] = reference_mode == "auto_extract"
    voice_options["auto_reference"] = reference_mode == "auto_extract"
    speaker_ref_paths: dict[str, str] = {}
    source_prosody_profile: dict | None = None
    source_hubert_features: dict | None = None
    tts_prosody_plan: dict | None = None
    prosody_validation_report: dict | None = None
    hubert_prosody_report: dict | None = None
    responsible_ai_bundle: dict | None = None
    job_manifest.set_routing_decision(
        manifest_path,
        selected_translation_backend=os.environ.get("VIDIOLINGUA_TRANSLATION_ENGINE", "auto"),
        selected_voice_backend="XTTS" if xtts_targets and cloning_required else "Sarvam" if sarvam_targets else None,
        xtts_supported=bool(xtts_targets),
        sarvam_supported=bool(sarvam_targets),
        indicf5_enabled=False,
        generic_fallback_allowed=_env_true("ALLOW_GENERIC_TTS_FALLBACK"),
        fallback_used=False,
        fallback_reason=None,
    )
    if voice_sample_path:
        job_manifest.register_artifact(manifest_path, "reference_audio", voice_sample_path, stage="receive_upload", kind="audio", role="input")
    initial_reference = (
        _reference_audio_analysis(voice_sample_path, "uploaded")
        if user_supplied_voice_sample
        else {
            "mode": "auto_extract",
            "status": "pending",
            "path": None,
            "duration_sec": None,
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "validation_passed": None,
            "reason": "Waiting for speaker profile auto-analysis. Sarvam remains managed TTS, not exact cloning.",
        }
        if sarvam_targets and not xtts_targets and auto_reference_requested
        else _reference_not_required_analysis()
        if sarvam_targets and not xtts_targets
        else {
            "mode": reference_mode,
            "path": None,
            "duration_sec": None,
            "sample_rate": None,
            "channels": None,
            "peak": None,
            "validation_passed": None,
            "reason": "Waiting for automatic extraction." if auto_reference_requested else "Reference audio is required for XTTS.",
        }
    )
    job_store.update_job(
        job_id,
        metrics={
            "reference_mode": initial_reference.get("mode"),
            "reference_audio_validation_passed": initial_reference.get("validation_passed"),
            "captions_requested": captions_requested,
        },
        captions_requested=captions_requested,
        analysis={
            "run_evidence": {
                "source_language": source_language or None,
                "target_language": ",".join(languages),
                "translation_backend": None,
                "voice_backend": None,
                "fallback_used": False,
                "generic_fallback_used": False,
            },
            "speaker_analysis": {
                "status": "pending",
                "speakers_detected": None,
                "source": None,
                "reason": "ASR has not completed yet.",
            },
            "reference_audio": initial_reference,
            "output_inspection": {},
            "audio_validation": {"validation_passed": None},
            "advanced_metrics": _advanced_metric_requirements(),
        },
    )
    try:
        responsible_ai_bundle = generate_compliance_bundle(
            job_dir=job_dir,
            job_id=job_id,
            context=_responsible_ai_context(
                languages=languages,
                voice_options=voice_options,
                voice_backend="XTTS" if xtts_targets and cloning_required else "Sarvam" if sarvam_targets else None,
                translation_backend=os.environ.get("VIDIOLINGUA_TRANSLATION_ENGINE", "auto"),
                reference_audio_used=bool(voice_sample_path),
                xtts_speaker_reference_used=bool(xtts_targets and cloning_required),
                managed_tts_used=bool(sarvam_targets and not xtts_targets),
                lip_sync_or_visual_modification_used=False,
                final_mp4_replaces_original_audio=False,
            ),
            input_video_path=video_path,
            mode=os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only"),
            raise_on_block=True,
            final=False,
        )
        _register_compliance_artifacts(manifest_path, responsible_ai_bundle, stage="receive_upload")
        job_store.update_job(job_id, responsible_ai=responsible_ai_bundle.get("summary"))
    except Exception as compliance_error:
        if os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only").strip().lower() == "strict":
            raise
        job_manifest.register_warning(manifest_path, f"Responsible AI preliminary reports did not complete: {compliance_error}", stage="receive_upload")

    # Voice sample extraction for XTTS cloning.
    # CRITICAL: We use Demucs first to get CLEAN vocals (no BGM).
    # Dirty reference audio (with music) severely hurts XTTS similarity.
    job_manifest.start_stage(manifest_path, "prepare_audio", input_artifacts=[video_path, voice_sample_path])
    if cloning_required and xtts_targets and not voice_sample_path and _env_true("VIDIOLINGUA_REQUIRE_UVR5"):
        voice_work_dir = job_dir / "voice"
        use_uvr5_for_voice = _env_true("VIDIOLINGUA_USE_UVR5") or _env_true("VIDIOLINGUA_REQUIRE_UVR5")
        if use_uvr5_for_voice:
            try:
                clean_sample = _extract_clean_voice_sample(video_path, voice_work_dir)
                voice_sample_path = str(clean_sample)
                job_store.update_job(job_id, voice_sample_path=voice_sample_path)
                print(f"[Pipeline] Clean voice sample ready for XTTS: {clean_sample.name}")
            except Exception as e:
                if cloning_required:
                    job_manifest.fail_stage(manifest_path, "prepare_audio", f"Clean XTTS speaker reference extraction failed: {e}")
                    raise RuntimeError(
                        f"Clean XTTS speaker reference extraction failed and voice cloning is required: {e}"
                    ) from e
                print(f"[Pipeline] Clean vocal extraction failed ({e}), falling back to raw audio")
                try:
                    raw_sample = voice_work_dir / "raw_sample.wav"
                    _extract_voice_sample(video_path, raw_sample)
                    voice_sample_path = str(raw_sample)
                    job_store.update_job(job_id, voice_sample_path=voice_sample_path)
                except Exception as e2:
                    print(f"[Pipeline] Raw voice sample also failed ({e2}). XTTS will use neutral speaker.")
                    if cloning_required:
                        job_manifest.fail_stage(manifest_path, "prepare_audio", f"Speaker reference extraction failed: {e2}")
                        raise RuntimeError(
                            f"Speaker reference extraction failed and voice cloning is required: {e2}"
                        ) from e2
        else:
            # UVR5 off: extract raw audio (includes BGM — lower clone quality)
            try:
                raw_sample = voice_work_dir / "raw_sample.wav"
                _extract_voice_sample(video_path, raw_sample)
                voice_sample_path = str(raw_sample)
                job_store.update_job(job_id, voice_sample_path=voice_sample_path)
                print(f"[Pipeline] Raw voice sample extracted (enable UVR5 for better cloning): {raw_sample.name}")
            except Exception as e:
                print(f"[Pipeline] Voice sample extraction failed (XTTS will use neutral): {e}")
                if cloning_required:
                    job_manifest.fail_stage(manifest_path, "prepare_audio", f"Speaker reference extraction failed: {e}")
                    raise RuntimeError(
                        f"Speaker reference extraction failed and voice cloning is required: {e}"
                    ) from e
    if voice_sample_path:
        reference_key = "reference_audio"
        job_manifest.register_artifact(manifest_path, reference_key, voice_sample_path, stage="prepare_audio", kind="audio", role="output")
        if auto_reference_requested and not user_supplied_voice_sample:
            job_manifest.update_job_metadata(manifest_path, extracted_reference_path=voice_sample_path)
    job_manifest.complete_stage(manifest_path, "prepare_audio", output_artifacts=[voice_sample_path] if voice_sample_path else [])

    current_manifest_stage = "prepare_audio"
    try:
        # ----------------------------------------------------------------
        # Stage 0: BGM Separation (UVR5 / Demucs) — optional
        # ----------------------------------------------------------------
        bgm_path = None
        use_uvr5 = _env_true("VIDIOLINGUA_USE_UVR5") or _env_true("VIDIOLINGUA_REQUIRE_UVR5")
        if use_uvr5:
            job_store.update_job(job_id, stage="bgm_separation", progress=5)
            try:
                # Run Demucs via ML Python (requires torch, Python 3.11)
                uvr5_script = PROJECT_ROOT / "lipsync" / "run_uvr5_subprocess.py"
                if uvr5_script.exists():
                    r = subprocess.run(
                        [_demucs_python(), str(uvr5_script), str(video_path), str(uvr5_work)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env={**os.environ, "VIDIOLINGUA_USE_UVR5": "true"},
                    )
                    if r.returncode != 0:
                        raise RuntimeError(r.stderr or r.stdout)
                    bgm_candidate = uvr5_work / "no_vocals.wav"
                    bgm_path = str(bgm_candidate) if bgm_candidate.is_file() else None
                else:
                    from lipsync.run_uvr5 import extract_bgm_from_video
                    _, bgm_path_obj = extract_bgm_from_video(video_path, uvr5_work)
                    bgm_path = str(bgm_path_obj) if bgm_path_obj else None
                if bgm_path:
                    print(f"[Pipeline] BGM extracted for remix: {Path(bgm_path).name}")
                    job_manifest.register_artifact(manifest_path, "extracted_audio", bgm_path, stage="prepare_audio", kind="wav", role="output")
                    job_store.update_job(job_id, stage="bgm_separation", progress=10)
            except Exception as uvr5_err:
                print(f"[Pipeline] UVR5/BGM stage failed: {repr(uvr5_err)}")
                job_manifest.register_warning(manifest_path, f"Optional BGM extraction failed: {uvr5_err}", stage="prepare_audio")
                if _env_true("VIDIOLINGUA_REQUIRE_UVR5"):
                    raise
            if _env_true("VIDIOLINGUA_REQUIRE_UVR5") and not bgm_path:
                raise RuntimeError("UVR5/Demucs was required but no background track was produced.")

        # ----------------------------------------------------------------
        # Stage 1: ASR (WhisperX + PyAnnote)
        # ----------------------------------------------------------------
        current_manifest_stage = "asr"
        job_manifest.start_stage(manifest_path, "asr", input_artifacts=[video_path], logs=_manifest_stage_logs(logs_dir, "ASR"))
        job_store.update_job(job_id, stage="asr", progress=10)
        _clear_dir(asr_in)
        _clear_dir(asr_out)
        shutil.copy2(video_path, asr_in / video_path.name)
        job_manifest.register_artifact(manifest_path, "source_video", asr_in / video_path.name, stage="asr", kind="video", role="input")

        asr_env = os.environ.copy()
        asr_env["VIDIOLINGUA_ASR_INPUT_DIR"] = str(asr_in)
        asr_env["VIDIOLINGUA_ASR_OUTPUT_DIR"] = str(asr_out)
        asr_env["VIDIOLINGUA_STAGE_LOG_DIR"] = str(logs_dir)
        asr_env.setdefault("VIDIOLINGUA_ASR_ENGINE", "faster_whisper")
        asr_env.setdefault("VIDIOLINGUA_ENABLE_INLINE_ASR_DIARIZATION", "false")
        if source_language:
            asr_env["VIDIOLINGUA_SOURCE_LANGUAGE"] = source_language

        asr_engine = asr_env.get("VIDIOLINGUA_ASR_ENGINE", "faster_whisper")
        asr_model = asr_env.get("VIDIOLINGUA_WHISPER_MODEL", os.environ.get("VIDIOLINGUA_WHISPER_MODEL", "base"))
        asr_cache_hit = False
        asr_cache_dir = PROJECT_ROOT / ".cache" / "asr"
        asr_cache_dir.mkdir(parents=True, exist_ok=True)
        asr_cache_path = asr_cache_dir / f"{_asr_cache_key(video_path, source_language=source_language, engine=asr_engine, model=asr_model)}.json"
        asr_output_path = asr_out / f"{video_path.stem}_transcription.json"
        if _env_false("VIDIOLINGUA_ENABLE_ASR_CACHE") or not _copy_cached_asr(asr_cache_path, asr_output_path, video_file=asr_in / video_path.name):
            # ASR runs on the isolated ASR Python runtime.
            _run_stage(
                "ASR",
                [_whisperx_python(), str(PROJECT_ROOT / "asr" / "run_asr.py")],
                str(PROJECT_ROOT),
                env=asr_env,
            )
            generated_asr = sorted(asr_out.glob("*.json"))
            if generated_asr and not _env_false("VIDIOLINGUA_ENABLE_ASR_CACHE"):
                try:
                    shutil.copy2(generated_asr[0], asr_cache_path)
                    print(f"[Pipeline] ASR cache stored: {asr_cache_path.name}")
                except Exception as cache_err:
                    print(f"[Pipeline] ASR cache store skipped: {cache_err}")
        else:
            asr_cache_hit = True
            print(f"[Pipeline] ASR cache hit: {asr_cache_path.name}")
            job_manifest.register_warning(manifest_path, "ASR cache hit; reused transcript for identical source video/settings.", stage="asr")

        # Parse ASR output for detected language and segment count. Speaker
        # count is handled by asr.speaker_analysis so "not run" never becomes 0.
        detected_lang = None
        detected_conf = None
        segment_count = 0
        asr_json_paths = list(asr_out.glob("*.json"))
        for f in asr_out.iterdir():
            if f.is_file() and f.suffix.lower() == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    detected_lang = data.get("language")
                    detected_conf = data.get("language_confidence")
                    segments = data.get("segments", [])
                    segment_count += len(segments)
                except Exception:
                    pass
        asr_output_files = sum(1 for f in asr_out.iterdir() if f.is_file())
        lang_names = {
            "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
            "de": "German", "ja": "Japanese", "zh": "Chinese",
            "ar": "Arabic", "pt": "Portuguese", "kn": "Kannada",
            "ta": "Tamil", "bn": "Bengali", "te": "Telugu", "ml": "Malayalam",
            "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi", "or": "Odia",
            "od": "Odia",
        }
        if asr_json_paths:
            job_manifest.register_artifact(manifest_path, "asr_json", sorted(asr_json_paths)[0], stage="asr", kind="json", role="output")
        if captions_requested:
            try:
                from backend.captions import generate_source_captions_from_asr

                caption_result = generate_source_captions_from_asr(
                    sorted(asr_json_paths)[0] if asr_json_paths else None,
                    job_dir / "captions",
                )
                caption_language = caption_result.language_code or detected_lang or source_language or "und"
                for warning in caption_result.warnings:
                    job_manifest.register_warning(manifest_path, f"Caption generation: {warning}", stage="asr")
                for artifact in caption_result.artifacts:
                    if artifact.path.is_file():
                        caption_artifact_paths.append(artifact.path)
                        job_manifest.register_artifact(
                            manifest_path,
                            f"source_original_{artifact.format}",
                            artifact.path,
                            stage="asr",
                            kind=artifact.format,
                            role="output",
                            metadata={
                                "source": "asr_original",
                                "languageCode": caption_language,
                                "cueCount": caption_result.cue_count,
                            },
                        )
                        caption_metadata.append(
                            {
                                "kind": "subtitles",
                                "format": artifact.format,
                                "languageCode": caption_language,
                                "label": "Original-language captions"
                                if artifact.format == "vtt"
                                else "Original-language captions download",
                                "source": "asr_original",
                                "url": f"{api_base}/api/result/{job_id}/file/{artifact.path.name}",
                                "cueCount": caption_result.cue_count,
                            }
                        )
                job_store.update_job(
                    job_id,
                    metrics={
                        "captions_requested": True,
                        "captions_generated": bool(caption_result.generated),
                        "caption_cue_count": caption_result.cue_count,
                    },
                    analysis={
                        "source_captions": {
                            "requested": True,
                            "generated": bool(caption_result.generated),
                            "source": "asr_original",
                            "languageCode": caption_language,
                            "cueCount": caption_result.cue_count,
                            "warnings": caption_result.warnings,
                        }
                    },
                )
            except Exception as caption_err:
                job_manifest.register_warning(
                    manifest_path,
                    f"Caption generation failed and the video pipeline will continue: {caption_err}",
                    stage="asr",
                )
                job_store.update_job(
                    job_id,
                    metrics={"captions_requested": True, "captions_generated": False},
                    analysis={
                        "source_captions": {
                            "requested": True,
                            "generated": False,
                            "source": "asr_original",
                            "warnings": [str(caption_err)],
                        }
                    },
                )
        job_store.update_job(
            job_id,
            stage="asr",
            progress=18,
            metrics={
                "asr_segments": segment_count,
                "asr_cache_hit": asr_cache_hit,
                "asr_engine": asr_engine,
                "asr_output_files": asr_output_files,
                "speaker_analysis_status": "pending",
                "captions_requested": captions_requested,
                "captions_generated": bool(caption_metadata),
            },
            analysis={
                "speaker_analysis": {
                    "status": "pending",
                    "reason": "ASR transcript is ready; optional speaker analysis is still being prepared.",
                    "segment_count": segment_count,
                },
                "run_evidence": {
                    "source_language": lang_names.get(detected_lang, detected_lang),
                    "target_language": ",".join(languages),
                    "translation_backend": None,
                    "voice_backend": None,
                    "fallback_used": False,
                    "generic_fallback_used": False,
                },
            },
            source_language=lang_names.get(detected_lang, detected_lang),
            source_language_confidence=detected_conf,
        )
        speaker_voice_backend = "sarvam" if sarvam_targets and not xtts_targets else "xtts" if xtts_targets else "configured"
        speaker_report = None
        run_blocking_speaker_analysis = bool(
            asr_json_paths
            and (
                _env_true("VIDIOLINGUA_ENABLE_BLOCKING_SPEAKER_ANALYSIS")
                or _env_true("VIDIOLINGUA_ENABLE_FULL_SPEAKER_ANALYSIS")
                or (auto_reference_requested and sarvam_targets and not xtts_targets)
                or (cloning_required and xtts_targets and auto_reference_requested)
            )
        )
        if asr_json_paths and not run_blocking_speaker_analysis:
            job_manifest.register_warning(
                manifest_path,
                (
                    "Full PyAnnote speaker analysis skipped on the critical path. "
                    "Set VIDIOLINGUA_ENABLE_BLOCKING_SPEAKER_ANALYSIS=true when "
                    "speaker-profile artifacts are required."
                ),
                stage="asr",
            )
        if run_blocking_speaker_analysis:
            speaker_report_path = speaker_analysis_dir / "speaker_analysis_report.json"
            speaker_timeout = _env_int("VIDIOLINGUA_SPEAKER_ANALYSIS_TIMEOUT_SEC", 120, minimum=10)
            try:
                primary_asr_json = sorted(asr_json_paths)[0]
                _run_stage(
                    "Speaker analysis",
                    [
                        _whisperx_python(),
                        "-m",
                        "speaker_analysis.report",
                        "--audio",
                        str(video_path),
                        "--asr-json",
                        str(primary_asr_json),
                        "--output-dir",
                        str(speaker_analysis_dir),
                        "--target-language",
                        languages[0] if languages else "",
                        "--voice-backend",
                        speaker_voice_backend,
                        "--enriched-asr-output",
                        str(primary_asr_json),
                    ],
                    str(PROJECT_ROOT),
                    env=asr_env,
                    timeout_sec=speaker_timeout,
                )
                if speaker_report_path.is_file():
                    speaker_report = json.loads(speaker_report_path.read_text(encoding="utf-8"))
                    for artifact_key, artifact_path in (speaker_report.get("artifacts") or {}).items():
                        job_manifest.register_artifact(
                            manifest_path,
                            artifact_key,
                            artifact_path,
                            stage="asr",
                            kind="json" if str(artifact_path).lower().endswith(".json") else "audio",
                            role="output",
                        )
            except Exception as speaker_stage_err:
                job_manifest.register_warning(
                    manifest_path,
                    f"Speaker analysis stage did not complete: {speaker_stage_err}",
                    stage="asr",
                )
                if _env_true("VIDIOLINGUA_FAIL_ON_DIARIZATION_ERROR"):
                    raise
        from asr.speaker_analysis import analyze_speakers_from_asr

        speaker_analysis = (
            (speaker_report or {}).get("summary")
            if isinstance((speaker_report or {}).get("summary"), dict)
            else analyze_speakers_from_asr(asr_json_paths)
        )
        if sarvam_targets and not xtts_targets and speaker_analysis.get("status") not in {"computed", "defaulted"}:
            labeled_segments = _apply_default_single_speaker_labels(sorted(asr_json_paths))
            default_reason = (
                "Speaker diarization/profile detection was unavailable, so this Sarvam managed-TTS run "
                f"uses the default male speaker preset '{_default_sarvam_male_speaker()}'."
            )
            default_voice_plan = _write_default_sarvam_voice_plan(
                speaker_analysis_dir / "voice_assignment_plan.json",
                target_language=languages[0] if languages else "",
                reason=default_reason,
                segment_count=labeled_segments or segment_count,
            )
            _write_default_sarvam_voice_plan(
                speaker_analysis_dir / "sarvam_voice_plan.json",
                target_language=languages[0] if languages else "",
                reason=default_reason,
                segment_count=labeled_segments or segment_count,
            )
            job_manifest.register_artifact(
                manifest_path,
                "voice_assignment_plan",
                speaker_analysis_dir / "voice_assignment_plan.json",
                stage="asr",
                kind="json",
                role="output",
            )
            job_manifest.register_artifact(
                manifest_path,
                "sarvam_voice_plan",
                speaker_analysis_dir / "sarvam_voice_plan.json",
                stage="asr",
                kind="json",
                role="output",
            )
            speaker_analysis = {
                **speaker_analysis,
                "status": "defaulted",
                "speakers_detected": 1,
                "speaker_count": 1,
                "source": "default_single_speaker",
                "reason": default_reason,
                "segment_count": labeled_segments or speaker_analysis.get("segment_count") or segment_count,
                "speaker_labels": ["SPEAKER_00"],
                "speaker_reference_count": 0,
                "voice_assignment_status": "defaulted",
                "visual_analysis_status": "unavailable",
                "sarvam_voice_plan_speakers": default_voice_plan.get("speakers", []),
                "warnings": list(
                    dict.fromkeys(
                        [
                            *(speaker_analysis.get("warnings") or []),
                            "Speaker diarization/profile analysis unavailable; default male Sarvam voice preset applied.",
                        ]
                    )
                ),
            }
        speaker_count = speaker_analysis.get("speakers_detected")

        try:
            from voice.prosody_presets import hubert_enabled, prosody_engine_enabled

            if prosody_engine_enabled() and asr_json_paths:
                from voice.prosody_analysis import analyze_source_prosody

                source_prosody_path = prosody_dir / "source_prosody_profile.json"
                source_prosody_profile = analyze_source_prosody(
                    video_path,
                    asr_json_path=sorted(asr_json_paths)[0],
                    output_path=source_prosody_path,
                )
                job_manifest.register_artifact(
                    manifest_path,
                    "source_prosody_profile",
                    source_prosody_path,
                    stage="asr",
                    kind="json",
                    role="output",
                    metadata=_prosody_summary(source_prosody_profile),
                )
                if hubert_enabled():
                    from voice.hubert_prosody import extract_hubert_features

                    hubert_timeout = _env_int("VIDIOLINGUA_HUBERT_TIMEOUT_SEC", 90, minimum=5)
                    print(f"[Pipeline] Optional HuBERT source feature extraction timeout={hubert_timeout}s")
                    source_hubert_features = extract_hubert_features(
                        audio_path=video_path,
                        segments=source_prosody_profile.get("segments") if isinstance(source_prosody_profile.get("segments"), list) else [],
                        output_dir=prosody_dir / "source_hubert_features",
                        timeout_sec=hubert_timeout,
                    )
                    hubert_features_path = prosody_dir / "source_hubert_features" / "hubert_features.json"
                    job_manifest.register_artifact(
                        manifest_path,
                        "source_hubert_features",
                        hubert_features_path,
                        stage="asr",
                        kind="json",
                        role="output",
                        metadata={
                            "status": source_hubert_features.get("status"),
                            "model": source_hubert_features.get("model"),
                            "embedding_dim": source_hubert_features.get("embedding_dim"),
                        },
                    )
        except Exception as prosody_err:
            job_manifest.register_warning(manifest_path, f"Prosody analysis did not complete: {prosody_err}", stage="asr")
            print(f"[Pipeline] Prosody analysis skipped: {prosody_err}")
            from voice.prosody_presets import fail_on_prosody_error

            if fail_on_prosody_error():
                raise

        # Replace the broad first-30s fallback with ASR-guided speech references.
        # This improves speaker similarity without changing ASR, translation, or
        # lipsync contracts: TTS still receives WAV paths through env vars.
        reference_analysis = initial_reference
        if voice_sample_path and xtts_targets:
            reference_analysis = _reference_audio_analysis(
                voice_sample_path,
                "uploaded" if user_supplied_voice_sample else "auto_extract",
            )
            if not reference_analysis.get("validation_passed"):
                raise RuntimeError(
                    "Uploaded XTTS reference audio failed validation. "
                    f"{reference_analysis.get('reason') or 'Upload a clean 6-30 second reference.'}"
                )
        elif not user_supplied_voice_sample and cloning_required and xtts_targets:
            if not auto_reference_requested:
                raise RuntimeError(
                    "XTTS speaker-reference dubbing needs either a reference audio file or auto-extract from the uploaded video."
                )
            try:
                from voice.reference_extractor import extract_reference_audio

                reference_analysis = extract_reference_audio(
                    video_path,
                    speaker_analysis_dir / "references",
                    asr_json_paths=asr_json_paths,
                )
                voice_sample_path = str(reference_analysis["path"])
                job_store.update_job(job_id, voice_sample_path=voice_sample_path)
                job_manifest.update_job_metadata(manifest_path, extracted_reference_path=voice_sample_path)
                job_manifest.register_artifact(manifest_path, "reference_audio", voice_sample_path, stage="asr", kind="audio", role="output")
                reference_metadata_path = Path(voice_sample_path).with_name("auto_reference_metadata.json")
                if reference_metadata_path.is_file():
                    job_manifest.register_artifact(manifest_path, "reference_metadata", reference_metadata_path, stage="asr", kind="json", role="output")
                print(f"[Pipeline] Auto reference ready for XTTS: {voice_sample_path}")
            except Exception as ref_err:
                raise RuntimeError(
                    "Automatic reference extraction failed. Upload a clean 6-30 second reference clip. "
                    f"Details: {ref_err}"
                ) from ref_err
        elif sarvam_targets and user_supplied_voice_sample:
            reference_analysis = _reference_audio_analysis(voice_sample_path, "uploaded")
            if not reference_analysis.get("validation_passed"):
                reference_analysis["warning"] = (
                    "Uploaded reference audio could not be validated as an XTTS-style clone reference. "
                    "Sarvam will continue as managed TTS and use the default voice/profile path."
                )
        elif sarvam_targets and not xtts_targets:
            if auto_reference_requested and speaker_analysis.get("status") == "defaulted":
                reference_analysis = {
                    "mode": "auto_extract",
                    "status": "defaulted",
                    "path": None,
                    "duration_sec": None,
                    "sample_rate": None,
                    "channels": None,
                    "peak": None,
                    "validation_passed": None,
                    "reason": (
                        "Auto-analysis could not determine a speaker profile, so Sarvam uses the "
                        f"default male managed-TTS speaker '{_default_sarvam_male_speaker()}'."
                    ),
                    "warnings": ["Default male Sarvam voice preset applied because speaker profiling was unavailable."],
                }
            else:
                reference_analysis = (
                    _sarvam_auto_extract_analysis(speaker_report, speaker_analysis_dir)
                    if auto_reference_requested
                    else _reference_not_required_analysis()
                )

        speaker_labels = speaker_analysis.get("speaker_labels")
        if cloning_required and xtts_targets and isinstance(speaker_labels, list) and len(speaker_labels) > 1:
            try:
                speaker_ref_paths = _build_speaker_reference_wavs(
                    video_path,
                    sorted(asr_json_paths),
                    job_dir / "speaker_references",
                )
                for speaker_label, ref_path in speaker_ref_paths.items():
                    job_manifest.register_artifact(
                        manifest_path,
                        f"speaker_reference_{speaker_label.lower()}",
                        ref_path,
                        stage="asr",
                        kind="audio",
                        role="output",
                    )
                if speaker_ref_paths:
                    speaker_analysis = {
                        **speaker_analysis,
                        "speaker_reference_count": len(speaker_ref_paths),
                        "reason": (
                            f"ASR output contains speaker labels. Built {len(speaker_ref_paths)} per-speaker "
                            "reference WAVs for XTTS segment routing."
                        ),
                    }
            except Exception as speaker_ref_err:
                job_manifest.register_warning(
                    manifest_path,
                    f"Per-speaker XTTS references could not be built: {speaker_ref_err}",
                    stage="asr",
                )
                if _env_true("VIDIOLINGUA_REQUIRE_PER_SPEAKER_REFS"):
                    raise

        _clear_dir(trans_in)
        for f in asr_out.iterdir():
            if f.is_file():
                shutil.copy2(f, trans_in / f.name)

        job_store.update_job(
            job_id,
            stage="asr",
            progress=25,
            metrics={
                "asr_segments": segment_count,
                "asr_cache_hit": asr_cache_hit,
                "asr_engine": asr_engine,
                "speakers_detected": speaker_count,
                "speaker_analysis_status": speaker_analysis.get("status"),
                "asr_output_files": asr_output_files,
                "reference_mode": reference_analysis.get("mode"),
                "reference_audio_validation_passed": reference_analysis.get("validation_passed"),
                "prosody_profile_status": (source_prosody_profile or {}).get("summary", {}).get("status") if isinstance((source_prosody_profile or {}).get("summary"), dict) else None,
                "prosody_average_speech_rate_wpm": (source_prosody_profile or {}).get("global", {}).get("speech_rate_wpm") if isinstance((source_prosody_profile or {}).get("global"), dict) else None,
                "prosody_pause_count": (source_prosody_profile or {}).get("global", {}).get("pause_count") if isinstance((source_prosody_profile or {}).get("global"), dict) else None,
                "hubert_feature_status": (source_hubert_features or {}).get("status"),
                "captions_requested": captions_requested,
                "captions_generated": bool(caption_metadata),
                "caption_cue_count": caption_metadata[0].get("cueCount") if caption_metadata else 0,
            },
            analysis={
                "speaker_analysis": speaker_analysis,
                "reference_audio": reference_analysis,
                "prosodyElocution": _prosody_summary(source_prosody_profile, None, source_hubert_features),
                "run_evidence": {
                    "source_language": lang_names.get(detected_lang, detected_lang),
                    "target_language": ",".join(languages),
                    "translation_backend": None,
                    "voice_backend": None,
                    "fallback_used": False,
                    "generic_fallback_used": False,
                },
            },
            source_language=lang_names.get(detected_lang, detected_lang),
            source_language_confidence=detected_conf,
        )
        job_manifest.complete_stage(
            manifest_path,
            "asr",
            output_artifacts=[*sorted(asr_out.glob("*.json")), *caption_artifact_paths],
            logs=_manifest_stage_logs(logs_dir, "ASR"),
        )

        # ----------------------------------------------------------------
        # Stage 2: Translation (Llama-3 | Google fallback)
        # ----------------------------------------------------------------
        current_manifest_stage = "translation"
        job_manifest.start_stage(manifest_path, "translation", input_artifacts=sorted(trans_in.glob("*.json")), logs=_manifest_stage_logs(logs_dir, "Translation"))
        job_store.update_job(job_id, stage="translation", progress=35)
        _clear_dir(trans_out)

        if not any(f.is_file() for f in trans_in.iterdir()):
            raise RuntimeError(
                "Translation: no ASR output in translation input. "
                "Ensure ASR stage completed and produced transcription JSON."
            )

        trans_env = os.environ.copy()
        trans_env["VIDIOLINGUA_TARGET_LANGUAGES"] = ",".join(languages)
        trans_env["VIDIOLINGUA_TRANSLATION_INPUT_DIR"] = str(trans_in)
        trans_env["VIDIOLINGUA_TRANSLATION_OUTPUT_DIR"] = str(trans_out)
        trans_env["VIDIOLINGUA_STAGE_LOG_DIR"] = str(logs_dir)
        trans_env["VIDIOLINGUA_JOB_ID"] = job_id
        trans_env["VIDIOLINGUA_JOB_DIR"] = str(job_dir)
        # Pass through translation engine preference
        # Default: google; set VIDIOLINGUA_TRANSLATION_ENGINE=llama3 to use Llama-3

        # Translation uses TTS python since it has deep-translator
        _run_stage(
            "Translation",
            [_tts_python(),
             str(PROJECT_ROOT / "translation" / "run_translate.py")],
            str(PROJECT_ROOT),
            env=trans_env,
        )

        all_translation_stage_files = [f for f in trans_out.iterdir() if f.is_file()]
        trans_output_files = [f for f in all_translation_stage_files if _is_translation_payload(f)]
        translation_qa_report_files = [
            f
            for f in all_translation_stage_files
            if f.suffix.lower() == ".json"
            and (f.name.lower() == "translation_qa_report.json" or f.name.lower().endswith(".translation_qa_report.json"))
        ]
        linguistic_integrity_report_files = [
            f
            for f in all_translation_stage_files
            if f.suffix.lower() == ".json"
            and (f.name.lower() == "linguistic_integrity_report.json" or f.name.lower().endswith(".linguistic_integrity_report.json"))
        ]
        if not trans_output_files:
            raise RuntimeError(
                "Translation produced no output. "
                "Check VIDIOLINGUA_TARGET_LANGUAGES and that deep-translator is installed."
            )
        translation_evidence = _load_translation_evidence(trans_output_files)
        job_manifest.set_routing_decision(
            manifest_path,
            selected_translation_backend=translation_evidence.get("translation_backend"),
            fallback_used=bool(translation_evidence.get("translation_fallback_used", False)),
            fallback_reason=translation_evidence.get("translation_fallback_reason"),
        )
        _clear_dir(tts_in)
        try:
            from voice.prosody_presets import selected_preset_name, prosody_engine_enabled

            if prosody_engine_enabled() and source_prosody_profile and trans_output_files:
                from voice.prosody_transfer import apply_plan_to_translation_payload, build_tts_prosody_plan

                plan_source = sorted(trans_output_files)[0]
                translation_payload = json.loads(plan_source.read_text(encoding="utf-8"))
                plan_lang = translation_payload.get("language") or (languages[0] if languages else "")
                planned_voice_backend = "sarvam" if _lang_base(plan_lang) in sarvam_targets else "xtts" if _lang_base(plan_lang) in xtts_targets else "configured"
                tts_prosody_plan = build_tts_prosody_plan(
                    source_prosody_profile,
                    translation_payload,
                    target_language=plan_lang,
                    voice_backend=planned_voice_backend,
                    preset_name=selected_preset_name(),
                    output_path=prosody_dir / "tts_prosody_plan.json",
                    hubert_source_reference=(source_hubert_features or {}).get("global_embedding_path"),
                )
                job_manifest.register_artifact(
                    manifest_path,
                    "tts_prosody_plan",
                    prosody_dir / "tts_prosody_plan.json",
                    stage="translation",
                    kind="json",
                    role="output",
                    metadata=_prosody_summary(source_prosody_profile, tts_prosody_plan, source_hubert_features),
                )
                for f in trans_output_files:
                    payload = json.loads(f.read_text(encoding="utf-8"))
                    if f == plan_source:
                        payload = apply_plan_to_translation_payload(payload, tts_prosody_plan)
                    _safe_write_json(tts_in / f.name, payload)
            else:
                for f in trans_output_files:
                    shutil.copy2(f, tts_in / f.name)
        except Exception as plan_err:
            job_manifest.register_warning(manifest_path, f"Prosody TTS plan did not complete: {plan_err}", stage="translation")
            print(f"[Pipeline] Prosody plan skipped: {plan_err}")
            from voice.prosody_presets import fail_on_prosody_error

            if fail_on_prosody_error():
                raise
            for f in trans_output_files:
                shutil.copy2(f, tts_in / f.name)
        job_store.update_job(
            job_id,
            stage="translation",
            progress=50,
            metrics={
                "translation_files": len(trans_output_files),
                "target_language_count": len(languages),
                "translation_qa_reports": len(translation_qa_report_files),
                "linguistic_integrity_reports": len(linguistic_integrity_report_files),
                "prosody_plan_status": (tts_prosody_plan or {}).get("status"),
                "prosody_preset": (tts_prosody_plan or {}).get("preset"),
                "prosody_duration_pressure": (tts_prosody_plan or {}).get("global", {}).get("duration_pressure") if isinstance((tts_prosody_plan or {}).get("global"), dict) else None,
                "prosody_max_duration_pressure_ratio": (tts_prosody_plan or {}).get("global", {}).get("max_duration_pressure_ratio") if isinstance((tts_prosody_plan or {}).get("global"), dict) else None,
                **translation_evidence,
            },
            analysis={
                "prosodyElocution": _prosody_summary(source_prosody_profile, tts_prosody_plan, source_hubert_features),
                "run_evidence": {
                    "source_language": translation_evidence.get("translation_source_language") or lang_names.get(detected_lang, detected_lang),
                    "target_language": translation_evidence.get("target_language") or ",".join(languages),
                    "translation_backend": translation_evidence.get("translation_backend"),
                    "voice_backend": None,
                    "fallback_used": bool(translation_evidence.get("translation_fallback_used", False)),
                    "generic_fallback_used": False,
                },
                "translationQA": _translation_qa_summary_from_evidence(translation_evidence),
                "linguisticIntegrity": _linguistic_integrity_summary_from_evidence(translation_evidence),
            },
        )
        if trans_output_files:
            job_manifest.register_artifact(manifest_path, "translation_json", sorted(trans_output_files)[0], stage="translation", kind="json", role="output")
        if translation_qa_report_files:
            job_manifest.register_artifact(
                manifest_path,
                "translation_qa_report",
                sorted(translation_qa_report_files)[0],
                stage="translation",
                kind="json",
                role="output",
                metadata=_translation_qa_summary_from_evidence(translation_evidence),
            )
        if linguistic_integrity_report_files:
            job_manifest.register_artifact(
                manifest_path,
                "linguistic_integrity_report",
                sorted(linguistic_integrity_report_files)[0],
                stage="translation",
                kind="json",
                role="output",
                metadata=_linguistic_integrity_summary_from_evidence(translation_evidence),
            )
        job_manifest.complete_stage(
            manifest_path,
            "translation",
            output_artifacts=[*trans_output_files, *translation_qa_report_files, *linguistic_integrity_report_files],
            logs=_manifest_stage_logs(logs_dir, "Translation"),
        )
        try:
            responsible_ai_bundle = generate_compliance_bundle(
                job_dir=job_dir,
                job_id=job_id,
                context=_responsible_ai_context(
                    languages=languages,
                    voice_options=voice_options,
                    voice_backend="XTTS" if xtts_targets and cloning_required else "Sarvam" if sarvam_targets else None,
                    translation_backend=translation_evidence.get("translation_backend"),
                    reference_audio_used=bool(voice_sample_path),
                    xtts_speaker_reference_used=bool(xtts_targets and cloning_required),
                    managed_tts_used=bool(sarvam_targets and not xtts_targets),
                    lip_sync_or_visual_modification_used=False,
                    final_mp4_replaces_original_audio=False,
                ),
                input_video_path=video_path,
                mode=os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only"),
                raise_on_block=True,
                final=False,
            )
            _register_compliance_artifacts(manifest_path, responsible_ai_bundle, stage="translation")
            job_store.update_job(job_id, responsible_ai=responsible_ai_bundle.get("summary"))
        except Exception as compliance_error:
            if os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only").strip().lower() == "strict":
                raise
            job_manifest.register_warning(manifest_path, f"Responsible AI translation-stage reports did not complete: {compliance_error}", stage="translation")

        # ----------------------------------------------------------------
        # Stage 3: TTS (Coqui XTTSv2 | Hume | legacy gTTS)
        # ----------------------------------------------------------------
        current_manifest_stage = "voice_generation"
        job_manifest.start_stage(manifest_path, "voice_generation", input_artifacts=sorted(tts_in.glob("*.json")), logs=_manifest_stage_logs(logs_dir, "TTS"))
        job_store.update_job(job_id, stage="tts", progress=60)
        _clear_dir(tts_out)

        tts_env = os.environ.copy()
        tts_env["VIDIOLINGUA_TTS_INPUT_DIR"] = str(tts_in)
        tts_env["VIDIOLINGUA_TTS_OUTPUT_DIR"] = str(tts_out)
        tts_env["VIDIOLINGUA_STAGE_LOG_DIR"] = str(logs_dir)
        tts_env["VIDIOLINGUA_VOICE_OPTIONS"] = json.dumps(voice_options or {})
        if sarvam_targets and not xtts_targets and speaker_analysis.get("status") == "defaulted":
            tts_env["VIDIOLINGUA_SARVAM_SPEAKER"] = _default_sarvam_male_speaker()
        voice_assignment_plan_path = speaker_analysis_dir / "voice_assignment_plan.json"
        if voice_assignment_plan_path.is_file():
            tts_env["VIDIOLINGUA_VOICE_ASSIGNMENT_PLAN"] = str(voice_assignment_plan_path)
        _apply_xtts_quality_defaults(tts_env)
        if tts_prosody_plan and isinstance(tts_prosody_plan.get("backend_controls"), dict):
            controls = tts_prosody_plan["backend_controls"]
            if controls.get("temperature") is not None:
                tts_env["VIDIOLINGUA_XTTS_TEMP"] = str(controls.get("temperature"))
                tts_env["VIDIOLINGUA_SARVAM_TEMPERATURE"] = str(controls.get("temperature"))
            if controls.get("repetition_penalty") is not None:
                tts_env["VIDIOLINGUA_XTTS_REPETITION_PENALTY"] = str(controls.get("repetition_penalty"))
            if controls.get("max_chars") is not None:
                tts_env["VIDIOLINGUA_XTTS_MAX_CHARS"] = str(controls.get("max_chars"))
            if controls.get("crossfade_ms") is not None:
                tts_env["VIDIOLINGUA_XTTS_CROSSFADE_MS"] = str(controls.get("crossfade_ms"))
            if controls.get("pace") is not None:
                tts_env["VIDIOLINGUA_SARVAM_PACE"] = str(controls.get("pace"))
            if controls.get("speaker"):
                tts_env["VIDIOLINGUA_SARVAM_SPEAKER"] = str(controls.get("speaker"))
            tts_env["VIDIOLINGUA_PROSODY_PRESET_USED"] = str(tts_prosody_plan.get("preset") or "")
        if cloning_required:
            tts_env["VOICE_ENGINE"] = "xtts"
            tts_env["VIDIOLINGUA_TTS_ENGINE"] = "xtts"
            tts_env["XTTS_MODEL"] = "tts_models/multilingual/multi-dataset/xtts_v2"
            tts_env["VIDIOLINGUA_XTTS_MODEL"] = "tts_models/multilingual/multi-dataset/xtts_v2"
            if resolved_xtts_model_path:
                tts_env["VIDIOLINGUA_XTTS_MODEL_PATH"] = str(resolved_xtts_model_path)
            tts_env["VOICE_CLONING_REQUIRED"] = "true"
            tts_env["VIDIOLINGUA_REQUIRE_VOICE_CLONE"] = "true"
            tts_env["ALLOW_GENERIC_TTS_FALLBACK"] = "false"
            tts_env["XTTS_LANGUAGE"] = (languages[0] if languages else detected_lang or "en")
            tts_env["VIDIOLINGUA_VOICE_INTERMEDIATE_DIR"] = str(job_dir / "outputs" / "intermediate")
            tts_env["VIDIOLINGUA_FORCE_VOICE_REGENERATE"] = (
                os.environ.get("VIDIOLINGUA_FORCE_VOICE_REGENERATE", "true")
            )
        if voice_sample_path:
            voice_sample_sidecar = Path(voice_sample_path).with_suffix(".txt")
            if not voice_sample_sidecar.is_file():
                reference_text = _read_reference_text_from_env()
                if reference_text:
                    voice_sample_sidecar.write_text(reference_text, encoding="utf-8")
                    tts_env["VIDIOLINGUA_REFERENCE_TEXT"] = reference_text
                    print("[Pipeline] Voice reference transcript source: explicit env/CLI")
                elif _requires_indicf5_reference_text(languages):
                    print("[Pipeline] Voice reference transcript source: missing for IndicF5")
                    raise RuntimeError(
                        "IndicF5 requires the exact transcript of the reference audio. "
                        "Provide --reference-text, --reference-text-path, "
                        "VIDIOLINGUA_REFERENCE_TEXT, or VIDIOLINGUA_REFERENCE_TEXT_PATH. "
                        "The pipeline will not guess this transcript."
                    )
                else:
                    try:
                        ref_text_parts = []
                        for f in asr_out.glob("*.json"):
                            data = json.loads(f.read_text(encoding="utf-8"))
                            ref_text_parts.extend(
                                (s.get("text") or "").strip()
                                for s in data.get("segments", [])
                                if (s.get("text") or "").strip()
                            )
                        if ref_text_parts:
                            voice_sample_sidecar.write_text(
                                " ".join(ref_text_parts),
                                encoding="utf-8",
                            )
                            print("[Pipeline] Voice reference transcript source: ASR sidecar for non-IndicF5 use")
                    except Exception as ref_text_err:
                        print(f"[Pipeline] Voice reference transcript skipped: {ref_text_err}")
            else:
                try:
                    sidecar_text = voice_sample_sidecar.read_text(encoding="utf-8").strip()
                    if sidecar_text:
                        tts_env["VIDIOLINGUA_REFERENCE_TEXT"] = sidecar_text
                    print(f"[Pipeline] Voice reference transcript source: sidecar {voice_sample_sidecar}")
                except Exception as ref_text_err:
                    if _requires_indicf5_reference_text(languages):
                        raise RuntimeError(f"Could not read IndicF5 reference transcript sidecar: {ref_text_err}") from ref_text_err
                    print(f"[Pipeline] Voice reference transcript sidecar skipped: {ref_text_err}")

            tts_env["VIDIOLINGUA_VOICE_SAMPLE"] = voice_sample_path
            tts_env["SPEAKER_REFERENCE_AUDIO"] = voice_sample_path
            if os.environ.get("VIDIOLINGUA_REFERENCE_TEXT_PATH", "").strip():
                tts_env["VIDIOLINGUA_REFERENCE_TEXT_PATH"] = os.environ["VIDIOLINGUA_REFERENCE_TEXT_PATH"]
            if not tts_env.get("VIDIOLINGUA_TTS_ENGINE", "").strip():
                tts_env["VIDIOLINGUA_TTS_ENGINE"] = "auto"
            try:
                speakers = set()
                for f in asr_out.glob("*.json"):
                    data = json.loads(f.read_text(encoding="utf-8"))
                    speakers.update(
                        s.get("speaker")
                        for s in data.get("segments", [])
                        if s.get("speaker")
                    )
                if speakers and xtts_targets:
                    if speaker_ref_paths:
                        refs_for_tts = speaker_ref_paths
                    elif len(speakers) == 1 or _env_true("VIDIOLINGUA_ALLOW_SINGLE_REFERENCE_FOR_ALL_SPEAKERS"):
                        refs_for_tts = {speaker: voice_sample_path for speaker in sorted(speakers)}
                    else:
                        raise RuntimeError(
                            "Multiple speakers detected but per-speaker references are missing. "
                            "Provide per-speaker references, enable validated extraction/use, or set "
                            "VIDIOLINGUA_ALLOW_SINGLE_REFERENCE_FOR_ALL_SPEAKERS=true for explicit report-only reuse."
                        )
                    tts_env["VIDIOLINGUA_SPEAKER_REFS_JSON"] = json.dumps(refs_for_tts)
            except Exception as speaker_ref_err:
                print(f"[Pipeline] Speaker ref mapping skipped: {speaker_ref_err}")
                if cloning_required:
                    raise
        elif cloning_required:
            raise RuntimeError(
                "Voice cloning is required, but no validated speaker reference audio is available for TTS."
            )

        # TTS runs on TTS Python
        _run_stage(
            "TTS",
            [_tts_python(), str(PROJECT_ROOT / "tts" / "run_tts.py")],
            str(PROJECT_ROOT),
            env=tts_env,
        )
        tts_files = sorted(tts_out.glob("*.wav"))
        phonetic_report_files = [
            f
            for f in tts_out.iterdir()
            if f.is_file()
            and f.suffix.lower() == ".json"
            and (f.name.lower() == "phonetic_resolution_report.json" or f.name.lower().endswith(".phonetic_resolution_report.json"))
        ]
        phonetic_evidence = _load_phonetic_evidence(sorted(phonetic_report_files))
        if tts_files:
            job_manifest.register_artifact(manifest_path, "tts_wav", tts_files[0], stage="voice_generation", kind="wav", role="output")
        if phonetic_report_files:
            job_manifest.register_artifact(
                manifest_path,
                "phonetic_resolution_report",
                sorted(phonetic_report_files)[0],
                stage="voice_generation",
                kind="json",
                role="output",
                metadata=_phonetic_resolution_summary_from_evidence(phonetic_evidence),
            )
        job_manifest.complete_stage(
            manifest_path,
            "voice_generation",
            output_artifacts=[*tts_files, *phonetic_report_files],
            logs=_manifest_stage_logs(logs_dir, "TTS"),
        )
        current_manifest_stage = "audio_validation"
        job_manifest.start_stage(manifest_path, "audio_validation", input_artifacts=tts_files)
        video_duration = _probe_duration(video_path)
        print(
            "[Pipeline] Duration diagnostics: TTS uses per-segment ffmpeg atempo "
            "to match translated segment timestamps."
        )
        print(f"[Pipeline] Duration diagnostics: original_video={video_duration:.2f}s")
        tts_total_duration = 0.0
        for tts_file in tts_files:
            tts_duration = _probe_duration(tts_file)
            tts_total_duration += max(0.0, tts_duration)
            print(
                f"[Pipeline] Duration diagnostics: generated_tts={tts_file.name} "
                f"duration={tts_duration:.2f}s diff_vs_video={tts_duration - video_duration:+.2f}s"
            )
            if abs(tts_duration - video_duration) > 1.0:
                print(
                    f"[Pipeline] WARNING: generated TTS duration differs from video by "
                    f"{tts_duration - video_duration:+.2f}s."
                )
        _clear_dir(lipsync_in)
        for f in tts_out.iterdir():
            if f.is_file():
                shutil.copy2(f, lipsync_in / f.name)
        shutil.copy2(video_path, lipsync_in / video_path.name)
        voice_evidence = _voice_route_evidence(languages, cloning_required)
        job_manifest.set_routing_decision(
            manifest_path,
            selected_voice_backend=voice_evidence.get("voice_backend"),
            fallback_used=bool(translation_evidence.get("translation_fallback_used", False)) or bool(voice_evidence.get("generic_fallback_used", False)),
            fallback_reason=None,
            indicf5_enabled=False,
            generic_fallback_allowed=_env_true("ALLOW_GENERIC_TTS_FALLBACK"),
        )
        audio_validation = _tts_audio_validation_analysis(tts_files)
        try:
            from voice.prosody_presets import hubert_enabled, prosody_engine_enabled

            if prosody_engine_enabled() and source_prosody_profile and tts_files:
                from prosody.adapter_infer import build_prosody_validation_report, validate_adapter_for_job
                from voice.prosody_analysis import analyze_source_prosody

                tts_profile_path = prosody_dir / "dub_prosody_profile.json"
                tts_profile = analyze_source_prosody(
                    tts_files[0],
                    asr_json_path=sorted(asr_json_paths)[0] if asr_json_paths else None,
                    output_path=tts_profile_path,
                )
                prosody_validation_report = build_prosody_validation_report(
                    source_profile=source_prosody_profile,
                    tts_profile=tts_profile,
                    output_path=prosody_dir / "prosody_validation_report.json",
                )
                job_manifest.register_artifact(
                    manifest_path,
                    "prosody_validation_report",
                    prosody_dir / "prosody_validation_report.json",
                    stage="audio_validation",
                    kind="json",
                    role="output",
                    metadata=_prosody_summary(source_prosody_profile, tts_prosody_plan, prosody_validation_report),
                )
                if hubert_enabled():
                    hubert_prosody_report = validate_adapter_for_job(
                        job_dir,
                        PROJECT_ROOT / "models" / "prosody_hubert_adapter",
                        prosody_dir / "hubert_prosody_report.json",
                    )
                    job_manifest.register_artifact(
                        manifest_path,
                        "hubert_prosody_report",
                        prosody_dir / "hubert_prosody_report.json",
                        stage="audio_validation",
                        kind="json",
                        role="output",
                        metadata=_prosody_summary(source_prosody_profile, tts_prosody_plan, hubert_prosody_report),
                    )
        except Exception as prosody_validation_err:
            job_manifest.register_warning(manifest_path, f"Prosody validation did not complete: {prosody_validation_err}", stage="audio_validation")
            print(f"[Pipeline] Prosody validation skipped: {prosody_validation_err}")
            from voice.prosody_presets import fail_on_prosody_error

            if fail_on_prosody_error():
                raise
        job_store.update_job(
            job_id,
            stage="tts",
            progress=75,
            metrics={
                "tts_files": len(tts_files),
                "tts_total_duration_s": round(tts_total_duration, 3),
                "source_video_duration_s": round(video_duration, 3),
                "tts_duration_delta_s": round(tts_total_duration - video_duration, 3),
                "audio_validation_passed": bool(audio_validation.get("validation_passed")),
                "tts_wav_sample_rate": audio_validation.get("sample_rate"),
                "tts_wav_peak": audio_validation.get("peak"),
                "tts_normalization_applied": audio_validation.get("normalization_applied"),
                "sarvam_speaker": _default_sarvam_male_speaker() if sarvam_targets and not xtts_targets and speaker_analysis.get("status") == "defaulted" else None,
                "prosody_validation_status": (prosody_validation_report or {}).get("status"),
                "hubert_prosody_status": (hubert_prosody_report or {}).get("status"),
                "hubert_prosody_similarity_score": (hubert_prosody_report or {}).get("global", {}).get("prosody_similarity_score_0_100") if isinstance((hubert_prosody_report or {}).get("global"), dict) else None,
                "hubert_adapter_status": (hubert_prosody_report or {}).get("adapter_status"),
                "hubert_adapter_confidence": (hubert_prosody_report or {}).get("global", {}).get("confidence") if isinstance((hubert_prosody_report or {}).get("global"), dict) else None,
                **voice_evidence,
                **phonetic_evidence,
            },
            analysis={
                "audio_validation": audio_validation,
                "phoneticResolution": _phonetic_resolution_summary_from_evidence(phonetic_evidence),
                "prosodyElocution": _prosody_summary(source_prosody_profile, tts_prosody_plan, hubert_prosody_report or prosody_validation_report),
                "run_evidence": {
                    "source_language": translation_evidence.get("translation_source_language") or lang_names.get(detected_lang, detected_lang),
                    "target_language": translation_evidence.get("target_language") or ",".join(languages),
                    "translation_backend": translation_evidence.get("translation_backend"),
                    "voice_backend": voice_evidence.get("voice_backend"),
                    "fallback_used": bool(translation_evidence.get("translation_fallback_used", False)) or bool(voice_evidence.get("generic_fallback_used", False)),
                    "generic_fallback_used": bool(voice_evidence.get("generic_fallback_used", False)),
                },
            },
        )
        normalized_wavs = sorted((job_dir / "outputs" / "intermediate").glob("*clean*.wav"))
        if normalized_wavs:
            job_manifest.register_artifact(manifest_path, "normalized_tts_wav", normalized_wavs[0], stage="audio_validation", kind="wav", role="output")
        job_manifest.complete_stage(manifest_path, "audio_validation", output_artifacts=tts_files)

        # ----------------------------------------------------------------
        # Stage 4: LipSync (SadTalker → Wav2Lip → ffmpeg) + GFPGAN + BGM
        # ----------------------------------------------------------------
        current_manifest_stage = "lipsync_mux"
        job_manifest.start_stage(manifest_path, "lipsync_mux", input_artifacts=[video_path, *tts_files], logs=_manifest_stage_logs(logs_dir, "Lipsync"))
        job_store.update_job(job_id, stage="lipsync", progress=85)
        _clear_dir(lipsync_out)

        lipsync_env = os.environ.copy()
        lipsync_env["VIDIOLINGUA_LIPSYNC_INPUT_DIR"] = str(lipsync_in)
        lipsync_env["VIDIOLINGUA_LIPSYNC_OUTPUT_DIR"] = str(lipsync_out)
        lipsync_env["VIDIOLINGUA_STAGE_LOG_DIR"] = str(logs_dir)
        lipsync_mode = _lipsync_mode()
        visual_lipsync_requested = lipsync_mode in {"wav2lip_optional", "wav2lip_required"}
        lipsync_env["VIDIOLINGUA_LIPSYNC_MODE"] = lipsync_mode
        lipsync_env["VIDIOLINGUA_VISUAL_LIPSYNC_REQUESTED"] = "true" if visual_lipsync_requested else "false"
        alignment_evidence = _alignment_level_analysis(asr_json_paths)
        if alignment_evidence.get("alignment_warnings"):
            for warning in alignment_evidence.get("alignment_warnings") or []:
                job_manifest.register_warning(manifest_path, str(warning), stage="lipsync_mux")
        # Pass BGM path to lipsync stage for remixing
        if bgm_path and Path(bgm_path).is_file():
            lipsync_env["VIDIOLINGUA_BGM_PATH"] = str(bgm_path)
        # Explicitly pass lip-sync settings so the subprocess inherits them.
        musetalk_dir = os.environ.get("VIDIOLINGUA_MUSETALK_DIR", "").strip()
        if musetalk_dir and lipsync_mode != "ffmpeg_mux":
            lipsync_env["VIDIOLINGUA_MUSETALK_DIR"] = musetalk_dir
        musetalk_ckpt = os.environ.get("VIDIOLINGUA_MUSETALK_CHECKPOINT_DIR", "").strip()
        if musetalk_ckpt and lipsync_mode != "ffmpeg_mux":
            lipsync_env["VIDIOLINGUA_MUSETALK_CHECKPOINT_DIR"] = musetalk_ckpt
        wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
        if not wav2lip_dir and visual_lipsync_requested:
            default_wav2lip_dir = PROJECT_ROOT / "ml" / "Wav2Lip"
            if (default_wav2lip_dir / "inference.py").is_file():
                wav2lip_dir = str(default_wav2lip_dir)
        if wav2lip_dir and visual_lipsync_requested:
            lipsync_env["VIDIOLINGUA_WAV2LIP_DIR"] = wav2lip_dir
        wav2lip_ckpt = os.environ.get("VIDIOLINGUA_WAV2LIP_CHECKPOINT", "").strip()
        if not wav2lip_ckpt and visual_lipsync_requested:
            default_wav2lip_ckpt = PROJECT_ROOT / "ml" / "Wav2Lip" / "checkpoints" / "wav2lip_gan.pth"
            if default_wav2lip_ckpt.is_file():
                wav2lip_ckpt = str(default_wav2lip_ckpt)
        if wav2lip_ckpt and visual_lipsync_requested:
            lipsync_env["VIDIOLINGUA_WAV2LIP_CHECKPOINT"] = wav2lip_ckpt
        wav2lip_preflight = _wav2lip_preflight_report(wav2lip_dir, wav2lip_ckpt) if visual_lipsync_requested else {
            "ok": False,
            "selected_python": None,
            "wav2lip_dir": wav2lip_dir or str(PROJECT_ROOT / "ml" / "Wav2Lip"),
            "checkpoint_path": wav2lip_ckpt,
            "checkpoint_exists": bool(wav2lip_ckpt and Path(wav2lip_ckpt).is_file()),
            "errors": [],
            "warnings": ["Visual lip-sync was not requested; Wav2Lip preflight was skipped."],
        }
        wav2lip_preflight_path = lipsync_out / "wav2lip_preflight.json"
        _safe_write_json(wav2lip_preflight_path, wav2lip_preflight)
        job_manifest.register_artifact(
            manifest_path,
            "wav2lip_preflight",
            wav2lip_preflight_path,
            stage="lipsync_mux",
            kind="json",
            role="output",
            metadata={
                "ok": bool(wav2lip_preflight.get("ok")),
                "selected_python": wav2lip_preflight.get("selected_python"),
                "checkpoint_exists": wav2lip_preflight.get("checkpoint_exists"),
            },
        )
        wav2lip_error = _summarize_error(wav2lip_preflight.get("errors"))
        lipsync_env["VIDIOLINGUA_WAV2LIP_PREFLIGHT_OK"] = "true" if wav2lip_preflight.get("ok") else "false"
        if wav2lip_error:
            lipsync_env["VIDIOLINGUA_WAV2LIP_ERROR"] = wav2lip_error
        if visual_lipsync_requested and not wav2lip_preflight.get("ok") and lipsync_mode == "wav2lip_required":
            raise RuntimeError(f"Wav2Lip required mode failed preflight: {wav2lip_error or 'unknown preflight error'}")
        if visual_lipsync_requested and wav2lip_preflight.get("ok"):
            lipsync_env["VIDIOLINGUA_WAV2LIP_PYTHON"] = str(wav2lip_preflight.get("selected_python"))
            lipsync_env.setdefault("VIDIOLINGUA_WAV2LIP_RESIZE_FACTOR", "2")
            lipsync_env.setdefault("VIDIOLINGUA_WAV2LIP_FACE_BATCH_SIZE", "4")
            lipsync_env.setdefault("VIDIOLINGUA_WAV2LIP_BATCH_SIZE", "16")
            lipsync_env.setdefault("VIDIOLINGUA_LIPSYNC_ENGINE", "wav2lip")
            if lipsync_mode == "wav2lip_required":
                lipsync_env.setdefault("VIDIOLINGUA_REQUIRE_VISUAL_LIPSYNC", "true")
        else:
            lipsync_env["VIDIOLINGUA_LIPSYNC_ENGINE"] = "ffmpeg"

        # Lip-sync uses MuseTalk's env; the script falls back to ffmpeg when no backend is configured.
        _run_stage(
            "Lipsync",
            [_lipsync_python(), str(PROJECT_ROOT / "lipsync" / "run_lipsync.py")],
            str(PROJECT_ROOT),
            env=lipsync_env,
            timeout_sec=int(os.environ.get("VIDIOLINGUA_LIPSYNC_TIMEOUT_SEC", "300")),
        )
        lipsync_method = None
        lipsync_summary: dict = {}
        lipsync_stdout = logs_dir / "lipsync.stdout.log"
        if lipsync_stdout.is_file():
            try:
                for line in lipsync_stdout.read_text(encoding="utf-8", errors="replace").splitlines():
                    if "Method used:" in line:
                        lipsync_method = line.rsplit(":", 1)[-1].strip().lower() or None
            except Exception:
                lipsync_method = None
        lipsync_summary_path = lipsync_out / "lipsync_summary.json"
        if lipsync_summary_path.is_file():
            try:
                lipsync_summary = json.loads(lipsync_summary_path.read_text(encoding="utf-8"))
                if isinstance(lipsync_summary.get("outputs"), list) and lipsync_summary["outputs"]:
                    first_summary = next((item for item in lipsync_summary["outputs"] if isinstance(item, dict)), {})
                    if first_summary.get("method"):
                        lipsync_method = str(first_summary.get("method")).lower()
            except Exception:
                lipsync_summary = {}
        lipsync_outputs = list(lipsync_out.iterdir())
        print(f"[Pipeline] Lipsync output files: {[f.name for f in lipsync_outputs if f.is_file()]}")
        final_mp4_count = 0
        final_mp4_size_mb = 0.0
        final_mp4_duration = 0.0
        final_media_metadata: dict = {}
        for f in lipsync_outputs:
            if f.is_file():
                shutil.copy2(f, results_dir / f.name)
                if f.suffix.lower() == ".mp4":
                    final_mp4_count += 1
                    final_mp4_size_mb += f.stat().st_size / (1024 * 1024)
                    final_duration = _probe_duration(f)
                    final_media_metadata = _probe_media_metadata(f)
                    final_mp4_duration = max(final_mp4_duration, final_duration)
                    print(
                        f"[Pipeline] Duration diagnostics: final_mp4={f.name} "
                        f"duration={final_duration:.2f}s diff_vs_video={final_duration - video_duration:+.2f}s"
                    )
                    if abs(final_duration - video_duration) > 1.0:
                        print(
                            f"[Pipeline] WARNING: final MP4 duration differs from original video by "
                            f"{final_duration - video_duration:+.2f}s."
                        )
                    job_manifest.register_artifact(manifest_path, "final_mp4", results_dir / f.name, stage="lipsync_mux", kind="mp4", role="output")
        time.sleep(0.5)  # ensure filesystem flush before scan
        first_lipsync_output = {}
        if isinstance(lipsync_summary.get("outputs"), list):
            first_lipsync_output = next((item for item in lipsync_summary["outputs"] if isinstance(item, dict)), {})
        visual_fallback_used = bool(
            first_lipsync_output.get("fallback_used")
            or (visual_lipsync_requested and (lipsync_method or "unknown") == "ffmpeg")
            or (visual_lipsync_requested and not wav2lip_preflight.get("ok"))
        )
        lipsync_warnings = []
        lipsync_errors = []
        for source in (wav2lip_preflight, lipsync_summary, first_lipsync_output):
            if isinstance(source.get("warnings"), list):
                lipsync_warnings.extend(str(item) for item in source.get("warnings") or [])
            if isinstance(source.get("errors"), list):
                lipsync_errors.extend(str(item) for item in source.get("errors") or [])
        if alignment_evidence.get("alignment_warnings"):
            lipsync_warnings.extend(str(item) for item in alignment_evidence.get("alignment_warnings") or [])
        lipsync_analysis = {
            "method": lipsync_method or "unknown",
            "visual_sync_applied": lipsync_method in {"wav2lip", "musetalk", "sadtalker"},
            "visual_sync_requested": visual_lipsync_requested,
            "mode": lipsync_mode,
            "fallback_used": visual_fallback_used,
            "wav2lip_preflight_ok": bool(wav2lip_preflight.get("ok")),
            "wav2lip_python": wav2lip_preflight.get("selected_python"),
            "checkpoint_exists": bool(wav2lip_preflight.get("checkpoint_exists")),
            "alignment_level": alignment_evidence.get("alignment_level"),
            "alignment_word_count": alignment_evidence.get("alignment_word_count"),
            "alignment_word_coverage_ratio": alignment_evidence.get("alignment_word_coverage_ratio"),
            "lse_c_status": "not_installed",
            "lse_d_status": "not_installed",
            "source_video_duration_s": first_lipsync_output.get("source_video_duration_s") or round(video_duration, 3),
            "generated_audio_duration_s": first_lipsync_output.get("generated_audio_duration_s"),
            "prepared_audio_duration_s": first_lipsync_output.get("prepared_audio_duration_s"),
            "audio_padded_sec": first_lipsync_output.get("audio_padded_sec"),
            "audio_trimmed_sec": first_lipsync_output.get("audio_trimmed_sec"),
            "final_mp4_duration_s": round(final_mp4_duration, 3),
            "duration_delta_s": round(final_mp4_duration - video_duration, 3),
            "wav2lip_error": first_lipsync_output.get("wav2lip_error") or wav2lip_error,
            "warnings": list(dict.fromkeys(lipsync_warnings)),
            "errors": list(dict.fromkeys(lipsync_errors)),
        }
        lipsync_metrics = {
            "lipsync_output_files": sum(1 for f in lipsync_outputs if f.is_file()),
            "lipsync_method": lipsync_method or "unknown",
            "lipsync_visual_sync_applied": lipsync_method in {"wav2lip", "musetalk", "sadtalker"},
            "visual_lipsync_requested": visual_lipsync_requested,
            "lipsync_mode": lipsync_mode,
            "lipsync_fallback_used": visual_fallback_used,
            "wav2lip_preflight_ok": bool(wav2lip_preflight.get("ok")),
            "wav2lip_python": wav2lip_preflight.get("selected_python"),
            "wav2lip_checkpoint_exists": bool(wav2lip_preflight.get("checkpoint_exists")),
            "wav2lip_error": first_lipsync_output.get("wav2lip_error") or wav2lip_error,
            "alignment_level": alignment_evidence.get("alignment_level"),
            "alignment_word_count": alignment_evidence.get("alignment_word_count"),
            "alignment_word_coverage_ratio": alignment_evidence.get("alignment_word_coverage_ratio"),
            "prepared_audio_duration_s": first_lipsync_output.get("prepared_audio_duration_s"),
            "audio_padded_sec": first_lipsync_output.get("audio_padded_sec"),
            "audio_trimmed_sec": first_lipsync_output.get("audio_trimmed_sec"),
            "final_mp4_count": final_mp4_count,
            "final_mp4_size_mb": round(final_mp4_size_mb, 3),
            "final_mp4_duration_s": round(final_mp4_duration, 3),
            "final_duration_delta_s": round(final_mp4_duration - video_duration, 3),
            **final_media_metadata,
        }
        job_store.update_job(
            job_id,
            stage="lipsync",
            progress=95,
            metrics=lipsync_metrics,
            analysis={
                "output_inspection": _output_inspection_analysis(results_dir, lipsync_metrics),
                "lipsync": lipsync_analysis,
            },
        )
        job_manifest.complete_stage(
            manifest_path,
            "lipsync_mux",
            output_artifacts=sorted(lipsync_out.glob("*.mp4")),
            logs=_manifest_stage_logs(logs_dir, "Lipsync"),
        )
        current_manifest_stage = "output_validation"
        final_mp4s = sorted(path for path in results_dir.glob("*.mp4") if "_dubbed_" in path.stem)
        job_manifest.start_stage(manifest_path, "output_validation", input_artifacts=final_mp4s)
        job_manifest.complete_stage(manifest_path, "output_validation", output_artifacts=final_mp4s)
        final_local_mp4_for_compliance = final_mp4s[0] if final_mp4s else None
        try:
            responsible_ai_bundle = generate_compliance_bundle(
                job_dir=job_dir,
                job_id=job_id,
                context=_responsible_ai_context(
                    languages=languages,
                    voice_options=voice_options,
                    voice_backend=(job_store.get_job(job_id) or {}).get("metrics", {}).get("voice_backend"),
                    translation_backend=(job_store.get_job(job_id) or {}).get("metrics", {}).get("translation_backend"),
                    reference_audio_used=bool(voice_sample_path),
                    xtts_speaker_reference_used=bool(xtts_targets and cloning_required),
                    managed_tts_used=bool(sarvam_targets and not xtts_targets),
                    lip_sync_or_visual_modification_used=True,
                    final_mp4_replaces_original_audio=bool(final_local_mp4_for_compliance),
                ),
                input_video_path=video_path,
                final_video_path=final_local_mp4_for_compliance,
                audio_path=tts_files[0] if tts_files else None,
                mode=os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only"),
                raise_on_block=True,
                final=True,
            )
            _register_compliance_artifacts(manifest_path, responsible_ai_bundle, stage="output_validation")
            job_store.update_job(job_id, responsible_ai=responsible_ai_bundle.get("summary"))
        except Exception as compliance_error:
            if os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only").strip().lower() == "strict":
                raise
            job_manifest.register_warning(manifest_path, f"Responsible AI final reports did not complete: {compliance_error}", stage="output_validation")

        # ----------------------------------------------------------------
        # Build result for frontend
        # ----------------------------------------------------------------
        localized = []
        print(f"[Pipeline] Scanning results_dir: {[f.name for f in results_dir.iterdir() if f.is_file()]}")
        for f in results_dir.iterdir():
            if f.suffix.lower() == ".mp4" and "_dubbed_" in f.stem:
                lang_code = f.stem.split("_dubbed_")[-1]
                localized.append({
                    "language": lang_names.get(lang_code, lang_code),
                    "url": f"{api_base}/api/result/{job_id}/file/{f.name}",
                    "captions": caption_metadata if caption_metadata else [],
                })
        total_time = int(time.time() - start_time)
        accumulated_metrics = (job_store.get_job(job_id) or {}).get("metrics") or {}
        final_metrics = {
            **accumulated_metrics,
            "totalTime": total_time,
            "languagesProcessed": len(localized),
            "bgmPreserved": bgm_path is not None,
            "speakersDetected": speaker_count,
            "validation_passed": bool(localized) and bool(accumulated_metrics.get("output_validation_passed", True)),
            "fallback_used": bool(accumulated_metrics.get("translation_fallback_used", False)) or bool(accumulated_metrics.get("generic_fallback_used", False)),
            "captionsRequested": captions_requested,
            "captionsGenerated": bool(caption_metadata),
        }
        final_analysis = {
            **((job_store.get_job(job_id) or {}).get("analysis") or {}),
            "run_evidence": {
                "source_language": accumulated_metrics.get("translation_source_language") or lang_names.get(detected_lang, detected_lang),
                "target_language": accumulated_metrics.get("target_language") or ",".join(languages),
                "translation_backend": accumulated_metrics.get("translation_backend"),
                "voice_backend": accumulated_metrics.get("voice_backend"),
                "fallback_used": bool(final_metrics.get("fallback_used", False)),
                "generic_fallback_used": bool(accumulated_metrics.get("generic_fallback_used", False)),
                "total_elapsed_sec": total_time,
            },
            "advanced_metrics": _advanced_metric_requirements(),
        }
        translation_qa_summary = final_analysis.get("translationQA") if isinstance(final_analysis.get("translationQA"), dict) else _translation_qa_summary_from_evidence(accumulated_metrics)
        linguistic_integrity_summary = final_analysis.get("linguisticIntegrity") if isinstance(final_analysis.get("linguisticIntegrity"), dict) else _linguistic_integrity_summary_from_evidence(accumulated_metrics)
        phonetic_resolution_summary = final_analysis.get("phoneticResolution") if isinstance(final_analysis.get("phoneticResolution"), dict) else _phonetic_resolution_summary_from_evidence(accumulated_metrics)
        responsible_ai_summary = (responsible_ai_bundle or {}).get("summary") or (job_store.get_job(job_id) or {}).get("responsibleAI")
        if responsible_ai_summary:
            final_analysis["responsibleAI"] = responsible_ai_summary

        if not localized:
            result_payload = {
                "jobId": job_id,
                "originalVideo": f"{api_base}/api/result/{job_id}/file/input_video.mp4",
                "localizedVideos": [],
                "metrics": final_metrics,
                "analysis": final_analysis,
                "metricsReport": None,
                "translationQA": translation_qa_summary,
                "linguisticIntegrity": linguistic_integrity_summary,
                "phoneticResolution": phonetic_resolution_summary,
                "responsibleAI": responsible_ai_summary,
                "captionsRequested": captions_requested,
                "captions": caption_metadata,
                "manifestPath": str(manifest_path),
                "manifestSummary": job_manifest.build_manifest_summary(manifest_path),
                "error": (
                    "No dubbed videos were produced. "
                    "Ensure ffmpeg is installed and on PATH, and run: pip install gTTS. "
                    "Check the backend terminal for stage errors."
                ),
            }
            (job_dir / "pipeline_result.json").write_text(
                json.dumps(result_payload, indent=2),
                encoding="utf-8",
            )
            job_manifest.register_artifact(manifest_path, "pipeline_result", job_dir / "pipeline_result.json", stage="complete", kind="json", role="output")
            current_manifest_stage = "metrics_evaluation"
            job_manifest.start_stage(manifest_path, "metrics_evaluation", input_artifacts=[job_dir / "pipeline_result.json"])
            metrics_report = _build_metrics_report_for_job(job_dir)
            result_payload["metricsReport"] = metrics_report
            metrics_report_path = job_dir / "evaluation" / "metrics_report.json"
            job_manifest.register_artifact(manifest_path, "metrics_report", metrics_report_path, stage="metrics_evaluation", kind="json", role="output")
            job_manifest.complete_stage(manifest_path, "metrics_evaluation", output_artifacts=[metrics_report_path])
            job_manifest.start_stage(manifest_path, "complete")
            job_manifest.set_final_result(
                manifest_path,
                final_status="failed",
                final_mp4_path=None,
                duration_sec=final_metrics.get("final_mp4_duration_s") if isinstance(final_metrics.get("final_mp4_duration_s"), (int, float)) else None,
                file_size_bytes=None,
                validation_passed=False,
                user_facing_error=result_payload.get("error"),
            )
            job_manifest.complete_stage(manifest_path, "complete", output_artifacts=[job_dir / "pipeline_result.json", metrics_report_path])
            result_payload["manifestSummary"] = job_manifest.build_manifest_summary(manifest_path)
            result_payload["status"] = "failed"
            result_payload["terminal"] = True
            result_payload["stage"] = "complete"
            job_store.mark_job_terminal(
                job_id,
                status="failed",
                stage="error",
                error_summary=result_payload.get("error"),
                metrics_report=metrics_report,
                result=result_payload,
                result_path=str(job_dir / "pipeline_result.json"),
            )
            job_store.update_job(
                job_id,
                metrics=final_metrics,
                analysis=final_analysis,
                responsible_ai=responsible_ai_summary,
            )
        else:
            result_payload = {
                "jobId": job_id,
                "originalVideo": f"{api_base}/api/result/{job_id}/file/input_video.mp4",
                "localizedVideos": localized,
                "metrics": final_metrics,
                "analysis": final_analysis,
                "metricsReport": None,
                "translationQA": translation_qa_summary,
                "linguisticIntegrity": linguistic_integrity_summary,
                "phoneticResolution": phonetic_resolution_summary,
                "responsibleAI": responsible_ai_summary,
                "captionsRequested": captions_requested,
                "captions": caption_metadata,
                "manifestPath": str(manifest_path),
                "manifestSummary": job_manifest.build_manifest_summary(manifest_path),
            }
            (job_dir / "pipeline_result.json").write_text(
                json.dumps(result_payload, indent=2),
                encoding="utf-8",
            )
            job_manifest.register_artifact(manifest_path, "pipeline_result", job_dir / "pipeline_result.json", stage="complete", kind="json", role="output")
            current_manifest_stage = "metrics_evaluation"
            job_manifest.start_stage(manifest_path, "metrics_evaluation", input_artifacts=[job_dir / "pipeline_result.json"])
            metrics_report = _build_metrics_report_for_job(job_dir)
            result_payload["metricsReport"] = metrics_report
            metrics_report_path = job_dir / "evaluation" / "metrics_report.json"
            job_manifest.register_artifact(manifest_path, "metrics_report", metrics_report_path, stage="metrics_evaluation", kind="json", role="output")
            job_manifest.complete_stage(manifest_path, "metrics_evaluation", output_artifacts=[metrics_report_path])
            final_local_mp4 = final_mp4s[0] if final_mp4s else None
            job_manifest.start_stage(manifest_path, "complete")
            job_manifest.set_final_result(
                manifest_path,
                final_status="completed",
                final_mp4_path=final_local_mp4,
                duration_sec=final_metrics.get("final_mp4_duration_s") if isinstance(final_metrics.get("final_mp4_duration_s"), (int, float)) else None,
                file_size_bytes=final_local_mp4.stat().st_size if final_local_mp4 and final_local_mp4.is_file() else None,
                validation_passed=bool(final_metrics.get("validation_passed")),
                user_facing_error=None,
            )
            job_manifest.complete_stage(manifest_path, "complete", output_artifacts=[job_dir / "pipeline_result.json", metrics_report_path, final_local_mp4])
            result_payload["manifestSummary"] = job_manifest.build_manifest_summary(manifest_path)
            job_store.update_job(
                job_id,
                stage="complete",
                progress=100,
                metrics=final_metrics,
                analysis=final_analysis,
                metrics_report=metrics_report,
                responsible_ai=responsible_ai_summary,
                result=result_payload,
            )
        try:
            (job_dir / "pipeline_result.json").write_text(
                json.dumps(result_payload, indent=2),
                encoding="utf-8",
            )
        except Exception as write_result_error:
            print(f"[Pipeline] Could not write pipeline_result.json: {write_result_error}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        err_msg = repr(e)
        if not err_msg.strip():
            err_msg = "Pipeline failed (see backend logs)."
        failed_manifest_stage = current_manifest_stage or "complete"
        try:
            responsible_ai_bundle = generate_compliance_bundle(
                job_dir=job_dir,
                job_id=job_id,
                context=_responsible_ai_context(
                    languages=languages,
                    voice_options=voice_options,
                    voice_backend=(job_store.get_job(job_id) or {}).get("metrics", {}).get("voice_backend"),
                    translation_backend=(job_store.get_job(job_id) or {}).get("metrics", {}).get("translation_backend"),
                    reference_audio_used=bool(voice_sample_path),
                    xtts_speaker_reference_used=bool(xtts_targets and cloning_required),
                    managed_tts_used=bool(sarvam_targets and not xtts_targets),
                    lip_sync_or_visual_modification_used=False,
                    final_mp4_replaces_original_audio=False,
                ),
                input_video_path=video_path,
                mode=os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only"),
                raise_on_block=False,
                final=False,
            )
            _register_compliance_artifacts(manifest_path, responsible_ai_bundle, stage=failed_manifest_stage)
            job_store.update_job(job_id, responsible_ai=responsible_ai_bundle.get("summary"))
        except Exception as compliance_error:
            print(f"[Pipeline] Responsible AI failure report skipped: {compliance_error}")
        job_manifest.fail_stage(
            manifest_path,
            failed_manifest_stage,
            err_msg,
            logs=_manifest_stage_logs(logs_dir, failed_manifest_stage.replace("_", " ")),
        )
        existing_analysis = (job_store.get_job(job_id) or {}).get("analysis") or {}
        responsible_ai_summary = (responsible_ai_bundle or {}).get("summary") or (job_store.get_job(job_id) or {}).get("responsibleAI")
        if responsible_ai_summary:
            existing_analysis = {**existing_analysis, "responsibleAI": responsible_ai_summary}
        try:
            job_manifest.start_stage(manifest_path, "metrics_evaluation", input_artifacts=[job_dir / "pipeline_result.json"])
            metrics_report = _build_metrics_report_for_job(job_dir)
            metrics_report_path = job_dir / "evaluation" / "metrics_report.json"
            job_manifest.register_artifact(manifest_path, "metrics_report", metrics_report_path, stage="metrics_evaluation", kind="json", role="output")
            job_manifest.complete_stage(manifest_path, "metrics_evaluation", output_artifacts=[metrics_report_path])
        except Exception as metrics_error:
            metrics_report = {"status": "error", "reason": f"Metrics report could not be built: {metrics_error}"}
            job_manifest.fail_stage(manifest_path, "metrics_evaluation", f"Metrics report could not be built: {metrics_error}")
        job_manifest.set_final_result(
            manifest_path,
            final_status="failed",
            final_mp4_path=None,
            validation_passed=False,
            user_facing_error=err_msg,
        )
        failure_status = "timeout" if "timeout" in err_msg.lower() or "timed out" in err_msg.lower() else "failed"
        result_payload = {
            "jobId": job_id,
            "status": failure_status,
            "terminal": True,
            "stage": failed_manifest_stage,
            "originalVideo": "",
            "localizedVideos": [],
            "metrics": {"totalTime": 0, "languagesProcessed": 0},
            "analysis": existing_analysis,
            "metricsReport": metrics_report,
            "translationQA": existing_analysis.get("translationQA") if isinstance(existing_analysis.get("translationQA"), dict) else None,
            "linguisticIntegrity": existing_analysis.get("linguisticIntegrity") if isinstance(existing_analysis.get("linguisticIntegrity"), dict) else None,
            "phoneticResolution": existing_analysis.get("phoneticResolution") if isinstance(existing_analysis.get("phoneticResolution"), dict) else None,
            "responsibleAI": responsible_ai_summary,
            "captionsRequested": captions_requested if "captions_requested" in locals() else False,
            "captions": caption_metadata if "caption_metadata" in locals() else [],
            "manifestPath": str(manifest_path),
            "manifestSummary": job_manifest.build_manifest_summary(manifest_path),
            "error": err_msg,
            "errorSummary": err_msg,
        }
        try:
            (job_dir / "pipeline_result.json").write_text(
                json.dumps(result_payload, indent=2),
                encoding="utf-8",
            )
        except Exception as write_result_error:
            print(f"[Pipeline] Could not write failure pipeline_result.json: {write_result_error}")
        job_store.mark_job_terminal(
            job_id,
            status=failure_status,
            stage="timeout" if failure_status == "timeout" else "error",
            error_summary=err_msg,
            metrics_report=metrics_report,
            result=result_payload,
            result_path=str(job_dir / "pipeline_result.json"),
        )
        print(f"[Pipeline] Job {job_id} failed: {repr(e)}")


def _apply_cli_mode(mode: str) -> None:
    mode = (mode or "practical").lower()
    os.environ["VIDIOLINGUA_PIPELINE_MODE"] = mode
    if mode == "strict":
        os.environ["VIDIOLINGUA_REQUIRE_VOICE_CLONE"] = "true"
        os.environ["VOICE_CLONING_REQUIRED"] = "true"
        os.environ["ALLOW_GENERIC_TTS_FALLBACK"] = "false"
        os.environ["VIDIOLINGUA_TTS_ENGINE"] = "xtts"
        os.environ["VIDIOLINGUA_REQUIRE_UVR5"] = "true"
    elif mode == "debug":
        os.environ["ALLOW_GENERIC_TTS_FALLBACK"] = "true"
        os.environ["VOICE_CLONING_REQUIRED"] = "false"
        os.environ["VIDIOLINGUA_REQUIRE_VOICE_CLONE"] = "false"
        os.environ["VIDIOLINGUA_TTS_ENGINE"] = "legacy"
        os.environ["VIDIOLINGUA_USE_UVR5"] = "false"
        os.environ["VIDIOLINGUA_LIPSYNC_ENGINE"] = "ffmpeg"
    else:
        os.environ["VIDIOLINGUA_REQUIRE_VOICE_CLONE"] = "true"
        os.environ["VOICE_CLONING_REQUIRED"] = "true"
        os.environ["ALLOW_GENERIC_TTS_FALLBACK"] = "false"
        os.environ["VIDIOLINGUA_TTS_ENGINE"] = "xtts"
        os.environ.setdefault("VIDIOLINGUA_REQUIRE_UVR5", "false")
        os.environ.setdefault("VIDIOLINGUA_REQUIRE_GFPGAN", "false")


def _parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the VideoLingua video localization pipeline.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--target-language", default="fr")
    parser.add_argument("--reference", default=None)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--mode", choices=["strict", "practical", "debug"], default="practical")
    parser.add_argument("--output-dir", default="outputs/french_official_test")
    parser.add_argument("--source-language", default=None)
    parser.add_argument("--reference-text", default=None)
    parser.add_argument("--reference-text-path", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_cli_args(argv)
    _apply_cli_mode(args.mode)
    if args.model_path:
        os.environ["VIDIOLINGUA_XTTS_MODEL_PATH"] = str(_normalize_xtts_model_dir(Path(args.model_path)).resolve())
    if args.reference:
        os.environ["SPEAKER_REFERENCE_AUDIO"] = str(Path(args.reference).resolve())
        os.environ["VIDIOLINGUA_VOICE_SAMPLE"] = str(Path(args.reference).resolve())
    if args.reference_text:
        os.environ["VIDIOLINGUA_REFERENCE_TEXT"] = args.reference_text
    if args.reference_text_path:
        os.environ["VIDIOLINGUA_REFERENCE_TEXT_PATH"] = str(Path(args.reference_text_path).resolve())

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    global JOBS_DIR
    JOBS_DIR = output_dir.parent
    job_id = output_dir.name
    video = Path(args.video)
    if not video.is_absolute():
        video = PROJECT_ROOT / video

    voice_options = {"cloned": args.mode != "debug"}
    job_store.create_job(
        job_id,
        str(video),
        [args.target_language],
        source_language=args.source_language,
        voice_options=voice_options,
        voice_sample_path=str(Path(args.reference).resolve()) if args.reference else None,
    )
    try:
        run_pipeline(
            job_id,
            str(video),
            [args.target_language],
            source_language=args.source_language,
            voice_options=voice_options,
            voice_sample_path=str(Path(args.reference).resolve()) if args.reference else None,
            run_source="cli",
        )
    except Exception as exc:
        try:
            metrics_report = _build_metrics_report_for_job(output_dir)
        except Exception as metrics_error:
            metrics_report = {"status": "error", "reason": f"Metrics report could not be built: {metrics_error}"}
        job_store.update_job(job_id, stage="error", progress=0, error=str(exc))
        job_store.update_job(
            job_id,
            metrics_report=metrics_report,
            result={
                "jobId": job_id,
                "originalVideo": "",
                "localizedVideos": [],
                "metrics": {"totalTime": 0, "languagesProcessed": 0},
                "analysis": (job_store.get_job(job_id) or {}).get("analysis") or {},
                "metricsReport": metrics_report,
                "error": str(exc),
            },
        )
        print(f"[Pipeline] Job {job_id} failed before stage execution: {exc}")
    job = job_store.get_job(job_id) or {}
    result = job.get("result") or {}
    result_path = output_dir / "pipeline_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[Pipeline] Result metadata: {result_path}")
    return 0 if job.get("stage") == "complete" and not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
