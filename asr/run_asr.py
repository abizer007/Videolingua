"""
Automatic Speech Recognition (ASR) Module — WhisperX + PyAnnote

Upgrade over baseline faster-whisper:
  - WhisperX: provides **word-level** timestamps for perfect timing alignment.
  - PyAnnote: adds **speaker diarization** (who is speaking when).

Output JSON schema:
  {
    "video_file": "...",
    "language": "en",
    "language_confidence": 0.99,
    "segments": [
      {
        "start": 0.0,
        "end": 3.2,
        "text": "Hello world.",
        "speaker": "SPEAKER_00",          # from diarization (may be null)
        "words": [                         # word-level timestamps
          {"word": "Hello", "start": 0.0, "end": 0.5, "score": 0.95},
          {"word": "world.", "start": 0.6, "end": 1.1, "score": 0.92}
        ]
      }
    ]
  }

Fallback chain: WhisperX → faster-whisper (segment-level, no speaker labels)
"""

import json
import os
import subprocess
import tempfile
import inspect
import time
from importlib import metadata
from pathlib import Path

INPUT_DIR = Path(os.environ.get("VIDIOLINGUA_ASR_INPUT_DIR", Path(__file__).parent / "input"))
OUTPUT_DIR = Path(os.environ.get("VIDIOLINGUA_ASR_OUTPUT_DIR", Path(__file__).parent / "output"))

# Whisper model size: "tiny", "base", "small", "medium", "large-v2", "large-v3"
# WhisperX works best with "large-v2" or "large-v3" for accuracy.
WHISPER_MODEL = os.environ.get("VIDIOLINGUA_WHISPER_MODEL", "base")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def extract_audio_ffmpeg(video_path: Path, output_wav: Path) -> None:
    """Extract 16kHz mono WAV for Whisper using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output_wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg extract failed: {r.stderr or r.stdout}")


def _process_with_whisperx(audio_path: Path, forced_language: str | None) -> dict:
    """
    Run WhisperX: transcribe → align (word-level timestamps) → diarize (speaker labels).
    Returns a dict with 'segments', 'language', 'language_confidence'.
    """
    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")
    import whisperx
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    print(f"[ASR] WhisperX — device={device}, model={WHISPER_MODEL}")

    # 1. Transcribe
    model = whisperx.load_model(WHISPER_MODEL, device, compute_type=compute_type)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, language=forced_language, batch_size=16)
    detected_lang = result.get("language", forced_language or "en")
    language_confidence = 0.0

    # 2. Align → word-level timestamps
    try:
        align_model, metadata = whisperx.load_align_model(
            language_code=detected_lang, device=device
        )
        result = whisperx.align(
            result["segments"], align_model, metadata, audio, device,
            return_char_alignments=False,
        )
    except Exception as align_err:
        print(f"[ASR] Word alignment failed (skipping): {align_err}")

    # 3. Diarize → assign speaker labels
    hf_token = (
        os.environ.get("VIDIOLINGUA_PYANNOTE_TOKEN", "").strip()
        or os.environ.get("HUGGINGFACE_TOKEN", "").strip()
        or os.environ.get("HF_TOKEN", "").strip()
        or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    )
    pyannote_model = (
        os.environ.get("VIDIOLINGUA_PYANNOTE_MODEL", "").strip()
        or "pyannote/speaker-diarization-community-1"
    )
    pyannote_version = None
    try:
        pyannote_version = metadata.version("pyannote.audio")
    except metadata.PackageNotFoundError:
        pyannote_version = None
    diarization = {
        "enabled": bool(hf_token),
        "status": "skipped",
        "backend": "pyannote",
        "model": pyannote_model,
        "pyannote_version": pyannote_version,
        "token_present": bool(hf_token),
        "reason": "Set VIDIOLINGUA_PYANNOTE_TOKEN, HUGGINGFACE_TOKEN, HF_TOKEN, or HUGGING_FACE_HUB_TOKEN in backend/.env to enable PyAnnote speaker labels.",
    }
    inline_diarization_enabled = _env_bool("VIDIOLINGUA_ENABLE_INLINE_ASR_DIARIZATION", False)
    diarization["enabled"] = bool(hf_token and inline_diarization_enabled)
    if hf_token and inline_diarization_enabled:
        try:
            diarize_started = time.perf_counter()
            try:
                diarize_pipeline = whisperx.DiarizationPipeline
                assign_word_speakers = whisperx.assign_word_speakers
            except AttributeError:
                from whisperx.diarize import DiarizationPipeline, assign_word_speakers

                diarize_pipeline = DiarizationPipeline
            signature = inspect.signature(diarize_pipeline)
            diarize_kwargs = {"device": device}
            if "model_name" in signature.parameters:
                diarize_kwargs["model_name"] = pyannote_model
            if "token" in signature.parameters:
                diarize_kwargs["token"] = hf_token
            elif "use_auth_token" in signature.parameters:
                diarize_kwargs["use_auth_token"] = hf_token
            elif "auth_token" in signature.parameters:
                diarize_kwargs["auth_token"] = hf_token
            print(
                "[ASR] PyAnnote diarization: "
                f"version={pyannote_version or 'unknown'} model={pyannote_model} "
                f"token_present={bool(hf_token)} device={device}"
            )
            diarize_model = diarize_pipeline(**diarize_kwargs)
            diarize_segments = diarize_model(audio)
            result = assign_word_speakers(diarize_segments, result)
            diarization = {
                "enabled": True,
                "status": "computed",
                "backend": "pyannote",
                "model": pyannote_model,
                "pyannote_version": pyannote_version,
                "token_present": True,
                "device": device,
                "elapsed_sec": round(time.perf_counter() - diarize_started, 3),
                "reason": "PyAnnote diarization completed and speaker labels were assigned when segment overlap was available.",
            }
            print("[ASR] Speaker diarization complete.")
        except Exception as diar_err:
            diarization = {
                "enabled": True,
                "status": "failed",
                "backend": "pyannote",
                "model": pyannote_model,
                "pyannote_version": pyannote_version,
                "token_present": True,
                "device": device,
                "reason": f"PyAnnote diarization failed: {diar_err}",
                "recommended_fix": (
                    f"Use pyannote model '{pyannote_model}' with accepted Hugging Face terms and "
                    "VIDIOLINGUA_PYANNOTE_TOKEN/HUGGINGFACE_TOKEN. The backend also runs a "
                    "separate version-compatible speaker-analysis stage after ASR."
                ),
            }
            print(f"[ASR] Diarization failed: {diar_err}")
    elif hf_token:
        diarization["status"] = "skipped"
        diarization["reason"] = (
            "Inline ASR diarization skipped by default to keep transcription fast. "
            "Set VIDIOLINGUA_ENABLE_INLINE_ASR_DIARIZATION=true to run PyAnnote inside ASR."
        )
        print("[ASR] Inline diarization skipped - VIDIOLINGUA_ENABLE_INLINE_ASR_DIARIZATION is not true.")
    else:
        print("[ASR] Diarization skipped - set VIDIOLINGUA_PYANNOTE_TOKEN, HUGGINGFACE_TOKEN, HF_TOKEN, or HUGGING_FACE_HUB_TOKEN in backend/.env to enable.")

    # 4. Normalise output to canonical schema
    segments_list = []
    for s in result.get("segments", []):
        text = (s.get("text") or "").strip()
        if not text:
            continue
        words = [
            {
                "word": w.get("word", ""),
                "start": round(w.get("start", s.get("start", 0.0)), 3),
                "end": round(w.get("end", s.get("end", 0.0)), 3),
                "score": round(w.get("score", 0.0), 3),
            }
            for w in s.get("words", [])
        ]
        segments_list.append({
            "start": round(s.get("start", 0.0), 2),
            "end": round(s.get("end", 0.0), 2),
            "text": text,
            "speaker": s.get("speaker", None),
            "words": words,
        })

    return {
        "segments": segments_list,
        "language": detected_lang,
        "language_confidence": float(language_confidence),
        "diarization": diarization,
    }


def _process_with_faster_whisper(audio_path: Path, forced_language: str | None) -> dict:
    """Fallback: faster-whisper (segment-level, no speaker labels, no word timestamps)."""
    from faster_whisper import WhisperModel

    print(f"[ASR] Falling back to faster-whisper — device=cpu, model={WHISPER_MODEL}")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=forced_language,
        beam_size=1,
    )
    segments_list = []
    for s in segments_gen:
        text = (s.text or "").strip()
        if text:
            segments_list.append({
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": text,
                "speaker": None,
                "words": [],
            })
    return {
        "segments": segments_list,
        "language": info.language or forced_language or "en",
        "language_confidence": float(getattr(info, "language_probability", 0.0) or 0.0),
        "diarization": {
            "enabled": False,
            "status": "not_available",
            "reason": "faster-whisper fallback does not produce speaker labels.",
        },
    }


def process_video(video_path: Path) -> dict:
    """
    Transcribe video: extract audio, run WhisperX (with diarization), return enriched segments.
    Falls back to faster-whisper if WhisperX is not installed.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = Path(tmp.name)
    try:
        extract_audio_ffmpeg(video_path, audio_path)
        forced_language = os.environ.get("VIDIOLINGUA_SOURCE_LANGUAGE", "").strip() or None

        preferred_engine = os.environ.get("VIDIOLINGUA_ASR_ENGINE", "whisperx").strip().lower().replace("-", "_")
        result = None
        if preferred_engine in {"fast", "faster", "faster_whisper"}:
            try:
                result = _process_with_faster_whisper(audio_path, forced_language)
            except ImportError:
                print("[ASR] faster-whisper not installed - falling back to WhisperX.")

        # Try WhisperX first; fall back to faster-whisper
        if result is None:
            try:
                result = _process_with_whisperx(audio_path, forced_language)
            except ImportError:
                print("[ASR] whisperx not installed â€” using faster-whisper fallback.")
                try:
                    result = _process_with_faster_whisper(audio_path, forced_language)
                except ImportError as e:
                    raise RuntimeError(
                        "ASR requires whisperx or faster-whisper. "
                        "Install with: pip install whisperx"
                    ) from e

            except Exception as e:
                if os.environ.get("VIDIOLINGUA_REQUIRE_WHISPERX", "").strip().lower() in {"1", "true", "yes", "on"}:
                    raise
                print(f"[ASR] WhisperX failed ({e}); using faster-whisper fallback.")
                result = _process_with_faster_whisper(audio_path, forced_language)
        try:
            # Retained only to keep old unreachable block removed by future cleanup.
            pass
        except ImportError:
            print("[ASR] whisperx not installed — using faster-whisper fallback.")
            try:
                result = _process_with_faster_whisper(audio_path, forced_language)
            except ImportError as e:
                raise RuntimeError(
                    "ASR requires whisperx or faster-whisper. "
                    "Install with: pip install whisperx"
                ) from e

        except Exception as e:
            if os.environ.get("VIDIOLINGUA_REQUIRE_WHISPERX", "").strip().lower() in {"1", "true", "yes", "on"}:
                raise
            print(f"[ASR] WhisperX failed ({e}); using faster-whisper fallback.")
            result = _process_with_faster_whisper(audio_path, forced_language)

        segments_list = result["segments"]
        if not segments_list:
            segments_list = [{"start": 0.0, "end": 0.1, "text": "(no speech detected)",
                              "speaker": None, "words": []}]

        return {
            "video_file": str(video_path),
            "segments": segments_list,
            "language": result["language"],
            "language_confidence": result["language_confidence"],
            "diarization": result.get("diarization"),
        }
    finally:
        audio_path.unlink(missing_ok=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_files = (
        list(INPUT_DIR.glob("*.mp4"))
        + list(INPUT_DIR.glob("*.avi"))
        + list(INPUT_DIR.glob("*.mov"))
    )
    if not video_files:
        print(f"No video files found in {INPUT_DIR}")
        return
    for video_file in video_files:
        print(f"Processing: {video_file.name}")
        transcription = process_video(video_file)
        output_file = OUTPUT_DIR / f"{video_file.stem}_transcription.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transcription, f, indent=2, ensure_ascii=False)
        n_segs = len(transcription["segments"])
        speakers = {s["speaker"] for s in transcription["segments"] if s.get("speaker")}
        print(f"Transcription saved: {output_file} ({n_segs} segments, speakers={speakers or 'N/A'})")


if __name__ == "__main__":
    main()
