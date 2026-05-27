"""
Text-to-Speech (TTS) Module — Timing-Aware, Voice-Cloning Edition

CRITICAL UPGRADE: Per-segment timing enforcement.
  - Each translated segment has a start/end timestamp (from WhisperX).
  - We generate TTS audio for EACH segment individually.
  - We time-stretch each segment audio with ffmpeg atempo to fit EXACTLY
    within its original duration (end - start seconds).
  - Segments are placed at their correct timestamps in a silence track.
  - Gap between segments is filled with silence to preserve natural pauses.

Result: dubbed audio is perfectly in sync with the original video timeline.

TTS Engine:
  VIDIOLINGUA_TTS_ENGINE=auto   -> XTTS where supported, IndicF5 only for XTTS-unsupported Indian languages
  VIDIOLINGUA_TTS_ENGINE=indicf5 -> AI4Bharat IndicF5 for supported Indian languages
  VIDIOLINGUA_TTS_ENGINE=xtts   → Coqui XTTSv2 (zero-shot voice cloning)
  VIDIOLINGUA_TTS_ENGINE=hume   → Hume AI cloud
  VIDIOLINGUA_TTS_ENGINE=legacy → gTTS + ElevenLabs fallback
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Fix Windows cp1252 terminal encoding - allow all Unicode in print()
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.hume_tts_service import synthesize_to_wav as hume_synthesize_to_wav
from voice.base import (
    VoiceSynthesisRequest,
    indicf5_supports_language,
    normalize_voice_language,
    sarvam_supports_language,
    xtts_supports_language,
)
from voice.router import select_voice_engine
from voice.phonetic_resolution import analyze_phonetic_resolution, write_phonetic_resolution_report
from voice.pronunciation_dictionary import load_pronunciation_dictionary

INPUT_DIR = Path(os.environ.get("VIDIOLINGUA_TTS_INPUT_DIR", Path(__file__).parent / "input"))
OUTPUT_DIR = Path(os.environ.get("VIDIOLINGUA_TTS_OUTPUT_DIR", Path(__file__).parent / "output"))
logger = logging.getLogger(__name__)

_VALID_ENGINES = {"auto", "sarvam", "indicf5", "xtts", "hume", "legacy"}
_XTTS_SUPPORTED_LANGS = {
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
    "nl", "cs", "ar", "zh", "hu", "ko", "ja",
}
_INDICF5_SUPPORTED_LANGS = {
    "as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te",
}
_SARVAM_SUPPORTED_LANGS = {
    "bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te",
}
_LOGGED_ENGINE = False

# ──────────────────────────────────────────────────────────────────────────────
# Engine selection
# ──────────────────────────────────────────────────────────────────────────────

def _get_tts_engine() -> str:
    configured = (
        os.environ.get("VIDIOLINGUA_VOICE_ENGINE", "").strip().lower()
        or os.environ.get("VIDIOLINGUA_TTS_ENGINE", "").strip().lower()
    )
    if configured:
        return configured if configured in _VALID_ENGINES else "legacy"

    # If the pipeline extracted or received a speaker reference, prefer local
    # zero-shot cloning by default. This preserves voice similarity without
    # requiring the UI to explicitly pass voiceOptions.cloned=true.
    if os.environ.get("VIDIOLINGUA_VOICE_SAMPLE", "").strip():
        return "auto"

    engine = "legacy"
    return engine if engine in _VALID_ENGINES else "legacy"


def _lang_base(language_code: str) -> str:
    return (language_code or "en").lower().replace("_", "-").split("-")[0]


def _xtts_supports(language_code: str) -> bool:
    return _lang_base(language_code) in _XTTS_SUPPORTED_LANGS


def _indicf5_supports(language_code: str) -> bool:
    return _lang_base(language_code) in _INDICF5_SUPPORTED_LANGS


def _sarvam_supports(language_code: str) -> bool:
    return _lang_base(language_code) in _SARVAM_SUPPORTED_LANGS


def _indic_voice_backend() -> str:
    backend = os.environ.get("VIDIOLINGUA_INDIC_VOICE_BACKEND", "sarvam").strip().lower()
    return backend if backend in {"sarvam", "indicf5", "disabled"} else "sarvam"


def _select_engine_for_language(language_code: str) -> str:
    return _select_engine_for_request(
        language_code=language_code,
        output_path=Path(os.devnull),
        speaker_wav=os.environ.get("VIDIOLINGUA_VOICE_SAMPLE", "").strip()
        or os.environ.get("SPEAKER_REFERENCE_AUDIO", "").strip()
        or None,
        reference_text=_resolve_reference_text(None, required=False),
        voice_options=None,
    )


def _select_engine_for_request(
    *,
    language_code: str,
    output_path: Path,
    speaker_wav: Optional[str],
    reference_text: Optional[str],
    voice_options: Optional[dict],
) -> str:
    configured = _get_tts_engine()
    cloning_required = _requires_cloned_voice(voice_options)
    lang = normalize_voice_language(language_code)
    preferred = configured
    sarvam_managed_route = (
        _indic_voice_backend() == "sarvam"
        and sarvam_supports_language(lang)
        and not xtts_supports_language(lang)
    )

    if sarvam_managed_route and configured in {"hume", "legacy", "xtts"}:
        preferred = "auto"

    if not cloning_required and configured in {"hume", "legacy"} and not sarvam_managed_route:
        print(
            "[TTS] Route: "
            f"target_language={lang} configured_engine={configured} "
            f"selected_engine={configured} cloning_required=false "
            f"fallback_used=false output_path={output_path}"
        )
        return configured
    if not cloning_required and configured == "auto" and not speaker_wav and not sarvam_managed_route:
        print(
            "[TTS] Route: "
            f"target_language={lang} configured_engine=auto selected_engine=legacy "
            f"cloning_required=false fallback_used=false output_path={output_path}"
        )
        return "legacy"

    # Historical practical mode forces VIDIOLINGUA_TTS_ENGINE=xtts. Keep that
    # for XTTS languages, but let configured Indian languages use the Indic
    # voice backend.
    if (
        configured == "xtts"
        and not xtts_supports_language(lang)
        and (sarvam_supports_language(lang) or indicf5_supports_language(lang))
    ):
        preferred = "auto"

    request = VoiceSynthesisRequest(
        text="route probe",
        target_language=lang,
        output_path=Path(output_path),
        reference_audio_path=Path(speaker_wav) if speaker_wav else None,
        reference_text=reference_text,
        preferred_engine=preferred,
        cloning_required=cloning_required,
        allow_generic_fallback=_allow_generic_fallback(),
        allow_xtts_to_indicf5_fallback=_env_true("VIDIOLINGUA_ALLOW_XTTS_TO_INDICF5_FALLBACK", True),
    )
    selected = select_voice_engine(request)
    print(
        "[TTS] Route: "
        f"target_language={lang} "
        f"configured_engine={configured} "
        f"preferred_engine={preferred} "
        f"selected_engine={selected} "
        f"xtts_supported={xtts_supports_language(lang)} "
        f"sarvam_supported={sarvam_supports_language(lang)} "
        f"indicf5_supported={indicf5_supports_language(lang)} "
        f"cloning_required={cloning_required} "
        f"reference_audio={speaker_wav or ''} "
        f"reference_text_present={bool((reference_text or '').strip())} "
        f"fallback_used=false "
        f"managed_tts={str(selected == 'sarvam').lower()} "
        f"exact_voice_clone={str(selected != 'sarvam').lower()} "
        f"speaker_preservation={'not_supported' if selected == 'sarvam' else 'reference_conditioned'} "
        f"output_path={output_path}"
    )
    return selected



def _log_engine_once(engine: str) -> None:
    global _LOGGED_ENGINE
    if not _LOGGED_ENGINE:
        print(f"[TTS] Engine: {engine.upper()}")
        _LOGGED_ENGINE = True


def _requires_cloned_voice(voice_options: Optional[dict]) -> bool:
    required2 = os.environ.get("VIDIOLINGUA_CLONING_REQUIRED", "").strip().lower()
    if required2:
        return required2 in {"1", "true", "yes", "on"}
    required = os.environ.get("VOICE_CLONING_REQUIRED", "").strip().lower()
    if required:
        return required in {"1", "true", "yes", "on"}
    if os.environ.get("VIDIOLINGUA_REQUIRE_VOICE_CLONE", "").strip().lower() == "true":
        return True
    if os.environ.get("ALLOW_GENERIC_TTS_FALLBACK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    if os.environ.get("VIDIOLINGUA_TTS_ENGINE", "").strip().lower() in {"legacy", "hume"}:
        return False
    # Project default: cloned voice is required unless explicitly disabled.
    if not voice_options or "cloned" not in voice_options:
        return True
    return bool((voice_options or {}).get("cloned"))


def _allow_generic_fallback() -> bool:
    return (
        os.environ.get("VIDIOLINGUA_ALLOW_GENERIC_TTS_FALLBACK", "").strip().lower()
        or os.environ.get("ALLOW_GENERIC_TTS_FALLBACK", "").strip().lower()
    ) in {
        "1", "true", "yes", "on"
    }


def _env_true(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _phonetic_resolution_enabled() -> bool:
    return _env_true("VIDIOLINGUA_ENABLE_PHONETIC_RESOLUTION", True)


def _use_tts_prepared_text() -> bool:
    return _env_true("VIDIOLINGUA_USE_TTS_PREPARED_TEXT", True)


def _resolve_reference_text(speaker_wav: Optional[str], required: bool = False) -> Optional[str]:
    env_text = os.environ.get("VIDIOLINGUA_REFERENCE_TEXT", "").strip()
    if env_text:
        return env_text
    legacy_env_text = os.environ.get("VIDIOLINGUA_VOICE_SAMPLE_TEXT", "").strip()
    if legacy_env_text:
        return legacy_env_text
    path_value = os.environ.get("VIDIOLINGUA_REFERENCE_TEXT_PATH", "").strip()
    if path_value:
        path = Path(path_value)
        if not path.is_file():
            raise RuntimeError(f"Configured VIDIOLINGUA_REFERENCE_TEXT_PATH does not exist: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
        raise RuntimeError(f"Configured VIDIOLINGUA_REFERENCE_TEXT_PATH is empty: {path}")
    if speaker_wav:
        sidecar = Path(speaker_wav).with_suffix(".txt")
        if sidecar.is_file():
            text = sidecar.read_text(encoding="utf-8").strip()
            if text:
                return text
            if required:
                raise RuntimeError(f"Reference text sidecar is empty: {sidecar}")
    if required:
        raise RuntimeError(
            "IndicF5 requires reference text. Provide --reference-text, "
            "--reference-text-path, VIDIOLINGUA_REFERENCE_TEXT, or "
            "VIDIOLINGUA_REFERENCE_TEXT_PATH. Do not substitute target text."
        )
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Low-level ffmpeg helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ffmpeg_convert_to_wav(src: str, output_path: Path, sample_rate: int = 22050) -> None:
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", src,
         "-acodec", "pcm_s16le", "-ar", str(sample_rate), "-ac", "1",
         str(output_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg convert failed: {r.stderr or r.stdout or r.returncode}")


def _get_audio_duration(wav_path: Path) -> float:
    """Return duration in seconds of a WAV file using ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(wav_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _warn_if_aggressive_stretch(segment_index: int, actual_s: float, target_s: float) -> None:
    if actual_s <= 0 or target_s <= 0:
        return
    tempo = actual_s / target_s
    if tempo > 1.35:
        print(
            f"  [TTS] WARNING: seg {segment_index} requires speedup ratio {tempo:.2f}; "
            "speech may feel rushed."
        )
    elif tempo < 0.75:
        print(
            f"  [TTS] WARNING: seg {segment_index} requires slowdown ratio {tempo:.2f}; "
            "speech may feel stretched."
        )


def _time_stretch_wav(input_wav: Path, target_duration_s: float, output_wav: Path) -> None:
    """
    Time-stretch input_wav to fit target_duration_s using ffmpeg atempo.

    atempo range is 0.5–2.0 per filter; chain multiple for extremes.
    tempo = actual / target   (speeds up if TTS is longer than slot)
    """
    actual = _get_audio_duration(input_wav)
    if actual <= 0 or target_duration_s <= 0:
        import shutil
        shutil.copy2(input_wav, output_wav)
        return

    tempo = actual / target_duration_s
    print(
        f"  [TTS] stretch: actual={actual:.2f}s target={target_duration_s:.2f}s "
        f"tempo={tempo:.3f}"
    )
    # Clamp: don't stretch more than 3× or compress more than 3× — sounds unnatural
    tempo = max(0.33, min(3.0, tempo))

    # Build atempo filter chain (each filter handles 0.5–2.0)
    filters = []
    t = tempo
    while t > 2.0:
        filters.append("atempo=2.0")
        t /= 2.0
    while t < 0.5:
        filters.append("atempo=0.5")
        t /= 0.5
    filters.append(f"atempo={t:.6f}")
    filter_str = ",".join(filters)

    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_wav),
         "-filter:a", filter_str,
         "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
         str(output_wav)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"atempo stretch failed: {r.stderr or r.stdout}")


def _exact_segment_timing_enabled() -> bool:
    raw = os.environ.get("VIDIOLINGUA_EXACT_SEGMENT_TIMING", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _pad_or_trim_wav_to_duration(
    input_wav: Path,
    target_duration_s: float,
    output_wav: Path,
    *,
    sample_rate: int = 22050,
    tolerance_s: float = 0.03,
) -> dict:
    actual = _get_audio_duration(input_wav)
    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    if actual <= 0 or target_duration_s <= 0:
        import shutil
        shutil.copy2(input_wav, output_wav)
        final = _get_audio_duration(output_wav)
        return {
            "post_atempo_duration": round(actual, 3),
            "final_duration": round(final, 3),
            "padded_sec": 0.0,
            "trimmed_sec": 0.0,
        }

    diff = target_duration_s - actual
    if abs(diff) <= tolerance_s:
        import shutil
        shutil.copy2(input_wav, output_wav)
    else:
        audio_filter = f"apad,atrim=0:{target_duration_s:.6f},asetpts=PTS-STARTPTS"
        r = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(input_wav),
                "-af", audio_filter,
                "-acodec", "pcm_s16le",
                "-ar", str(sample_rate),
                "-ac", "1",
                str(output_wav),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            raise RuntimeError(f"segment pad/trim failed: {r.stderr or r.stdout}")
    final = _get_audio_duration(output_wav)
    return {
        "post_atempo_duration": round(actual, 3),
        "final_duration": round(final, 3),
        "padded_sec": round(max(0.0, diff), 3),
        "trimmed_sec": round(max(0.0, -diff), 3),
    }


def _make_silence(duration_s: float, output_wav: Path, sample_rate: int = 22050) -> None:
    """Generate a silence WAV of the given duration."""
    if duration_s <= 0:
        duration_s = 0.01
    r = subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono",
         "-t", f"{duration_s:.6f}",
         "-acodec", "pcm_s16le",
         str(output_wav)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"Silence generation failed: {r.stderr}")


def _concat_wavs(wav_paths: list[Path], output_wav: Path) -> None:
    """Concatenate a list of WAV files in order using ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
        dir=output_wav.parent,
    ) as f:
        for p in wav_paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")
        list_file = f.name
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_file,
             "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
             str(output_wav)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {r.stderr or r.stdout}")
    finally:
        Path(list_file).unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Per-engine single-segment synthesis
# ──────────────────────────────────────────────────────────────────────────────

def _get_voice_settings(voice_options: dict) -> dict:
    gender = (voice_options or {}).get("gender", "neutral")
    emotion = (voice_options or {}).get("emotion", "neutral")
    style = 0.2
    if emotion == "happy":
        style = 0.5
    elif emotion == "sad":
        style = 0.15
    elif emotion == "excited":
        style = 0.7
    stability = 0.4 if gender == "male" else 0.35 if gender == "female" else 0.3
    return {"stability": stability, "similarity_boost": 0.75,
            "style": style, "use_speaker_boost": True}


def _elevenlabs_request(api_key: str, method: str, url: str, **kwargs):
    import requests
    headers = kwargs.pop("headers", {})
    headers["xi-api-key"] = api_key
    headers["accept"] = "application/json"
    return requests.request(method, url, headers=headers, timeout=120, **kwargs)


def _create_elevenlabs_voice(api_key: str, sample_path: str, name: str) -> str:
    url = "https://api.elevenlabs.io/v1/voices/add"
    with open(sample_path, "rb") as f:
        resp = _elevenlabs_request(api_key, "POST", url,
                                   files={"files": f},
                                   data={"name": name, "description": "VidioLingua clone"})
    if resp.status_code >= 300:
        raise RuntimeError(f"ElevenLabs voice create failed: {resp.text}")
    return resp.json().get("voice_id")


def _elevenlabs_tts(api_key, voice_id, text, model_id, mp3_path, voice_settings):
    import requests
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    resp = _elevenlabs_request(api_key, "POST", url,
                                json={"text": text, "model_id": model_id,
                                      "voice_settings": voice_settings},
                                headers={"accept": "audio/mpeg"})
    if resp.status_code >= 300:
        raise RuntimeError(f"ElevenLabs TTS failed: {resp.text}")
    with open(mp3_path, "wb") as f:
        f.write(resp.content)


def _synthesize_legacy(text: str, language_code: str, output_path: Path,
                       voice_options=None, voice_id: Optional[str] = None,
                       allow_elevenlabs: bool = True) -> Path:
    if not text.strip():
        _make_silence(0.1, output_path)
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=output_path.parent) as tmp:
        mp3_path = tmp.name
    try:
        api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("VIDIOLINGUA_ELEVENLABS_API_KEY")
        model_id = os.environ.get("VIDIOLINGUA_ELEVENLABS_MODEL", "eleven_multilingual_v2")
        if allow_elevenlabs and api_key and voice_id:
            settings = _get_voice_settings(voice_options or {})
            _elevenlabs_tts(api_key, voice_id, text, model_id, mp3_path, settings)
        else:
            try:
                from gtts import gTTS
            except ImportError as e:
                raise RuntimeError("Install gTTS: pip install gTTS") from e
            gTTS(text=text, lang=language_code, slow=False).save(mp3_path)
        _ffmpeg_convert_to_wav(mp3_path, output_path)
    finally:
        Path(mp3_path).unlink(missing_ok=True)
    return output_path


def _synthesize_indicf5(text: str, language_code: str, output_path: Path,
                        voice_options=None, voice_id: Optional[str] = None,
                        speaker_wav: Optional[str] = None,
                        reference_text: Optional[str] = None) -> Path:
    from app.services import indicf5_tts_service

    return indicf5_tts_service.synthesize_to_wav(
        text=text,
        output_path=output_path,
        voice_options=voice_options,
        voice_id=voice_id,
        speaker_wav=speaker_wav,
        language_code=language_code,
        ref_text=reference_text,
    )


def _synthesize_sarvam(text: str, language_code: str, output_path: Path,
                       voice_options=None, voice_id: Optional[str] = None,
                       speaker_wav: Optional[str] = None,
                       reference_text: Optional[str] = None,
                       sarvam_speaker: Optional[str] = None) -> Path:
    del voice_options, voice_id, speaker_wav, reference_text
    from voice.engines.sarvam_engine import SarvamEngine

    request = VoiceSynthesisRequest(
        text=text,
        target_language=language_code,
        output_path=output_path,
        preferred_engine="sarvam",
        cloning_required=True,
        allow_generic_fallback=False,
    )
    return SarvamEngine(speaker=sarvam_speaker).synthesize(request).output_path


def _synthesize_xtts(text: str, language_code: str, output_path: Path,
                     voice_options=None, voice_id: Optional[str] = None,
                     speaker_wav: Optional[str] = None) -> Path:
    from app.services import xtts_tts_service
    return xtts_tts_service.synthesize_to_wav(
        text=text, output_path=output_path,
        voice_options=voice_options, voice_id=voice_id,
        speaker_wav=speaker_wav, language_code=language_code,
    )


def synthesize_segment(text: str, language_code: str, output_path: Path,
                       voice_options=None, voice_id: Optional[str] = None,
                       speaker_wav: Optional[str] = None,
                       reference_text: Optional[str] = None,
                       sarvam_speaker: Optional[str] = None) -> Path:
    """Synthesize a single text segment to output_path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not text or not text.strip():
        _make_silence(0.1, output_path)
        return output_path

    engine = _select_engine_for_request(
        language_code=language_code,
        output_path=output_path,
        speaker_wav=speaker_wav,
        reference_text=reference_text,
        voice_options=voice_options,
    )
    sarvam_managed_route = (
        _indic_voice_backend() == "sarvam"
        and sarvam_supports_language(language_code)
        and not xtts_supports_language(language_code)
    )
    if sarvam_managed_route and engine != "sarvam":
        raise RuntimeError(
            f"Sarvam managed Indian-language TTS is required for '{language_code}', "
            f"but routing selected '{engine}'."
        )
    _log_engine_once(engine)

    if engine == "hume":
        return hume_synthesize_to_wav(text, output_path, voice_options, voice_id=voice_id)
    if engine == "indicf5":
        try:
            return _synthesize_indicf5(text, language_code, output_path,
                                       voice_options, voice_id, speaker_wav, reference_text)
        except Exception as exc:
            if _requires_cloned_voice(voice_options) or not _allow_generic_fallback():
                raise RuntimeError(f"IndicF5 cloned TTS is required but failed: {exc}") from exc
            print(f"[TTS] WARNING: IndicF5 failed ({exc}); generic fallback is explicitly allowed.")
            return _synthesize_legacy(
                text, language_code, output_path, voice_options, voice_id,
                allow_elevenlabs=False,
            )
    if engine == "sarvam":
        try:
            return _synthesize_sarvam(text, language_code, output_path,
                                      voice_options, voice_id, speaker_wav, reference_text, sarvam_speaker)
        except Exception as exc:
            if _requires_cloned_voice(voice_options) or not _allow_generic_fallback():
                raise RuntimeError(f"Sarvam managed Indian-language TTS is required but failed: {exc}") from exc
            print(f"[TTS] WARNING: Sarvam failed ({exc}); generic fallback is explicitly allowed.")
            return _synthesize_legacy(
                text, language_code, output_path, voice_options, voice_id,
                allow_elevenlabs=False,
            )
    if engine == "xtts":
        try:
            return _synthesize_xtts(text, language_code, output_path,
                                    voice_options, voice_id, speaker_wav)
        except Exception as exc:
            if _requires_cloned_voice(voice_options) or not _allow_generic_fallback():
                raise RuntimeError(f"XTTS cloned TTS is required but failed: {exc}") from exc
            print(f"[TTS] WARNING: XTTS failed ({exc}); generic fallback is explicitly allowed.")
            return _synthesize_legacy(text, language_code, output_path, voice_options, voice_id)
    if _requires_cloned_voice(voice_options):
        raise RuntimeError(
            f"Generic TTS fallback is blocked because cloning_required=true. "
            f"Selected/unknown engine was '{engine}'."
        )
    return _synthesize_legacy(text, language_code, output_path, voice_options, voice_id)


# ──────────────────────────────────────────────────────────────────────────────
# CORE: Timing-aware audio assembly
# ──────────────────────────────────────────────────────────────────────────────

def _load_voice_assignment_by_speaker() -> dict[str, dict]:
    raw_json = os.environ.get("VIDIOLINGUA_VOICE_ASSIGNMENT_PLAN_JSON", "").strip()
    raw_path = os.environ.get("VIDIOLINGUA_VOICE_ASSIGNMENT_PLAN", "").strip()
    payload = None
    if raw_json:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid VIDIOLINGUA_VOICE_ASSIGNMENT_PLAN_JSON: {exc}") from exc
    elif raw_path and Path(raw_path).is_file():
        try:
            payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid voice assignment plan JSON at {raw_path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("speakers"), list):
        return {}
    by_speaker: dict[str, dict] = {}
    for item in payload["speakers"]:
        if not isinstance(item, dict):
            continue
        speaker_id = str(item.get("speaker_id") or "").strip()
        if speaker_id:
            by_speaker[speaker_id] = item
    return by_speaker


def generate_timed_audio_from_transcription(
    transcription_data: dict,
    output_path: Path,
    voice_options=None,
    voice_id: Optional[str] = None,
    speaker_wav: Optional[str] = None,
    speaker_refs: Optional[dict[str, str]] = None,
    reference_text: Optional[str] = None,
) -> Path:
    """
    Generate a dubbed audio track where each segment is placed at its exact
    original timestamp. This is what makes the dubbed audio stay in sync.

    Algorithm:
      1. For each segment [start, end, text]:
         a. synthesize TTS audio for `text`
         b. time-stretch the TTS to fit within (end - start) seconds
         c. record a silence gap from previous segment end to this segment start
      2. Concatenate: silence | stretched_seg | silence | stretched_seg | ...
      3. Write final WAV to output_path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    language_code = transcription_data.get("language", "en")
    segments = transcription_data.get("segments", [])
    cloning_required = _requires_cloned_voice(voice_options)
    voice_assignment_by_speaker = _load_voice_assignment_by_speaker()
    timeline_end = max(
        (
            float(seg.get("end", 0.0))
            for seg in segments
            if isinstance(seg, dict)
        ),
        default=0.0,
    )

    if not segments:
        _make_silence(1.0, output_path)
        return output_path

    sarvam_managed_route = (
        _indic_voice_backend() == "sarvam"
        and sarvam_supports_language(language_code)
        and not xtts_supports_language(language_code)
    )
    if cloning_required and not speaker_wav and not speaker_refs and not sarvam_managed_route:
        raise RuntimeError(
            "Voice cloning is required, but no speaker reference WAV was provided to TTS."
        )

    with tempfile.TemporaryDirectory(dir=output_path.parent) as tmpdir:
        tmp = Path(tmpdir)
        pieces: list[Path] = []
        cursor = 0.0  # current timeline position in seconds
        exact_segment_timing = _exact_segment_timing_enabled()
        timing_segments: list[dict] = []

        for i, seg in enumerate(segments):
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", seg_start + 1.0))
            display_text = (seg.get("text") or "").strip()
            prepared_text = (seg.get("tts_prepared_text") or "").strip()
            text = prepared_text if _use_tts_prepared_text() and prepared_text else display_text
            target_dur = max(0.1, seg_end - seg_start)
            timing_record = {
                "segment_index": i,
                "start": round(seg_start, 3),
                "end": round(seg_end, 3),
                "target_duration": round(target_dur, 3),
                "raw_duration": None,
                "atempo_ratio": None,
                "post_atempo_duration": None,
                "final_duration": None,
                "padded_sec": 0.0,
                "trimmed_sec": 0.0,
                "warning": None,
            }
            seg_speaker = str(seg.get("speaker_id") or seg.get("speaker") or "")
            seg_speaker_wav = (
                (speaker_refs or {}).get(seg_speaker)
                or speaker_wav
            )
            sarvam_speaker = None
            if seg_speaker and seg_speaker in voice_assignment_by_speaker:
                sarvam_speaker = voice_assignment_by_speaker[seg_speaker].get("selected_tts_voice")
            seg_reference_text = reference_text or _resolve_reference_text(
                seg_speaker_wav,
                required=_indic_voice_backend() == "indicf5"
                and indicf5_supports_language(language_code)
                and not xtts_supports_language(language_code)
                and cloning_required,
            )
            if cloning_required and not seg_speaker_wav and not sarvam_managed_route:
                raise RuntimeError(
                    f"Voice cloning is required, but segment {i} has no speaker reference."
                )

            # 1. Silence gap before this segment
            gap = seg_start - cursor
            if gap > 0.02:
                silence_file = tmp / f"silence_{i:04d}.wav"
                _make_silence(gap, silence_file)
                pieces.append(silence_file)

            cursor = seg_end  # advance cursor regardless of text

            # 2. Synthesize segment TTS
            raw_wav = tmp / f"raw_{i:04d}.wav"
            if text:
                try:
                    synthesize_segment(text, language_code, raw_wav,
                                       voice_options, voice_id, seg_speaker_wav, seg_reference_text, sarvam_speaker)
                    raw_dur = _get_audio_duration(raw_wav)
                    _warn_if_aggressive_stretch(i, raw_dur, target_dur)
                    safe_text = text[:40].encode('ascii', 'replace').decode('ascii')
                    print(f"  [TTS] seg {i}: '{safe_text}...' | "
                          f"speaker={seg_speaker or 'unknown'} "
                          f"sarvam_voice={sarvam_speaker or ''} "
                          f"chars={len(text)} tts={raw_dur:.2f}s -> target={target_dur:.2f}s")
                except Exception as e:
                    if cloning_required or not _allow_generic_fallback():
                        raise
                    print(f"  [TTS] WARNING: seg {i} synthesis failed ({e!r}), using silence")
                    _make_silence(target_dur, raw_wav)
                    raw_dur = _get_audio_duration(raw_wav)

                # 3. Time-stretch to fit target duration
                stretched_wav = tmp / f"stretched_{i:04d}.wav"
                try:
                    _time_stretch_wav(raw_wav, target_dur, stretched_wav)
                except Exception as e:
                    if cloning_required:
                        raise RuntimeError(f"TTS timing stretch failed for cloned segment {i}: {e}") from e
                    print(f"  [TTS] atempo stretch failed ({e}), using raw")
                    import shutil
                    shutil.copy2(raw_wav, stretched_wav)
                raw_duration = _get_audio_duration(raw_wav)
                post_atempo_duration = _get_audio_duration(stretched_wav)
                timing_record["raw_duration"] = round(raw_duration, 3)
                timing_record["atempo_ratio"] = round(raw_duration / target_dur, 3) if target_dur > 0 else None
                if exact_segment_timing:
                    corrected_wav = tmp / f"corrected_{i:04d}.wav"
                    correction = _pad_or_trim_wav_to_duration(stretched_wav, target_dur, corrected_wav)
                    timing_record.update(correction)
                    final_piece = corrected_wav
                else:
                    timing_record["post_atempo_duration"] = round(post_atempo_duration, 3)
                    timing_record["final_duration"] = round(post_atempo_duration, 3)
                    final_piece = stretched_wav
                if timing_record["atempo_ratio"] and (
                    timing_record["atempo_ratio"] > 1.35 or timing_record["atempo_ratio"] < 0.75
                ):
                    timing_record["warning"] = "aggressive_atempo_ratio"
                timing_segments.append(timing_record)
                pieces.append(final_piece)
            else:
                seg_silence = tmp / f"seg_silence_{i:04d}.wav"
                _make_silence(target_dur, seg_silence)
                silence_duration = _get_audio_duration(seg_silence)
                timing_record.update(
                    {
                        "post_atempo_duration": round(silence_duration, 3),
                        "final_duration": round(silence_duration, 3),
                    }
                )
                timing_segments.append(timing_record)
                pieces.append(seg_silence)

        if not pieces:
            _make_silence(1.0, output_path)
            return output_path

        # 4. Concatenate all pieces
        _concat_wavs(pieces, output_path)

    timing_report_path = output_path.with_suffix(".timing_report.json")
    timing_report_path.write_text(
        json.dumps(
            {
                "exact_segment_timing": _exact_segment_timing_enabled(),
                "segment_count": len(segments),
                "timeline_end": round(timeline_end, 3),
                "segments": timing_segments,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        from voice.audio_validation import validate_generated_audio

        validate_generated_audio(output_path)
    except Exception as exc:
        if cloning_required:
            raise RuntimeError(f"Final TTS WAV failed validation: {exc}") from exc
        print(f"[TTS] WARNING: final WAV validation failed: {exc}")

    final_duration = _get_audio_duration(output_path)
    print(f"[TTS] Final assembled WAV duration: {final_duration:.2f}s")
    if timeline_end > 0:
        diff = final_duration - timeline_end
        print(
            f"[TTS] Duration diagnostics: source_timeline={timeline_end:.2f}s "
            f"final_tts={final_duration:.2f}s diff={diff:+.2f}s "
            "per_segment_atempo=true"
        )
        if abs(diff) > 0.50:
            print(
                f"[TTS] WARNING: final TTS duration differs from source timeline by {diff:+.2f}s."
            )
    print(f"[TTS] Timed audio assembled: {output_path.name} ({len(segments)} segments)")
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Legacy single-blob function (kept for backward compat, not used by main())
# ──────────────────────────────────────────────────────────────────────────────

def generate_audio_from_transcription(transcription_data, output_path,
                                       voice_options=None, voice_id=None):
    """Legacy: joins all segments into one blob. Kept for API compat."""
    return generate_timed_audio_from_transcription(
        transcription_data, output_path, voice_options, voice_id
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    transcription_files = list(INPUT_DIR.glob("*_transcription_*.json"))

    if not transcription_files:
        print(f"No translated transcription files found in {INPUT_DIR}")
        return

    voice_options = {}
    try:
        voice_options = json.loads(os.environ.get("VIDIOLINGUA_VOICE_OPTIONS", "{}"))
    except json.JSONDecodeError:
        voice_options = {}

    voice_sample = os.environ.get("VIDIOLINGUA_VOICE_SAMPLE", "").strip()
    if not voice_sample:
        voice_sample = os.environ.get("SPEAKER_REFERENCE_AUDIO", "").strip()
    default_voice_id = os.environ.get("ELEVENLABS_VOICE_ID") or os.environ.get("VIDIOLINGUA_ELEVENLABS_VOICE_ID")
    voice_id = default_voice_id

    # Resolve speaker WAV for XTTS (auto-sample or explicit)
    speaker_wav = voice_sample if voice_sample and Path(voice_sample).is_file() else None
    if not speaker_wav:
        # Try auto_sample from job directory (set by pipeline_runner)
        auto = os.environ.get("VIDIOLINGUA_VOICE_SAMPLE", "")
        if auto and Path(auto).is_file():
            speaker_wav = auto

    speaker_refs: dict[str, str] = {}
    speaker_refs_json = os.environ.get("VIDIOLINGUA_SPEAKER_REFS_JSON", "").strip()
    if speaker_refs_json:
        try:
            loaded_refs = json.loads(speaker_refs_json)
            if isinstance(loaded_refs, dict):
                speaker_refs = {
                    str(k): str(v)
                    for k, v in loaded_refs.items()
                    if v and Path(str(v)).is_file()
                }
        except json.JSONDecodeError as exc:
            if _requires_cloned_voice(voice_options):
                raise RuntimeError(f"Invalid VIDIOLINGUA_SPEAKER_REFS_JSON: {exc}") from exc
            print(f"[TTS] WARNING: invalid speaker refs JSON ignored: {exc}")

    reference_text = _resolve_reference_text(speaker_wav, required=False)
    pronunciation_dictionary = load_pronunciation_dictionary()
    phonetic_reports: dict[str, dict] = {}

    for transcription_file in transcription_files:
        print(f"\n[TTS] Processing: {transcription_file.name}")
        with open(transcription_file, "r", encoding="utf-8") as f:
            transcription_data = json.load(f)
        if _phonetic_resolution_enabled():
            transcription_data, phonetic_report = analyze_phonetic_resolution(
                transcription_data,
                target_language=transcription_data.get("language"),
                dictionary=pronunciation_dictionary,
            )
            per_file_report = OUTPUT_DIR / f"{transcription_file.stem}.phonetic_resolution_report.json"
            write_phonetic_resolution_report(phonetic_report, per_file_report)
            phonetic_reports[transcription_file.stem] = phonetic_report.to_dict()
            print(
                "[TTS] Phonetic resolution: "
                f"status={phonetic_report.status} risk={phonetic_report.phonetic_risk_score_0_100} "
                f"dictionary_used={phonetic_report.dictionary_used}"
            )
        output_file = OUTPUT_DIR / f"{transcription_file.stem}.wav"
        if os.environ.get("VIDIOLINGUA_FORCE_VOICE_REGENERATE", "").strip().lower() in {"1", "true", "yes", "on"}:
            output_file.unlink(missing_ok=True)
        generate_timed_audio_from_transcription(
            transcription_data, output_file, voice_options, voice_id, speaker_wav, speaker_refs, reference_text
        )
        print(f"[TTS] Saved: {output_file.name}")

    if phonetic_reports:
        aggregate_report = {
            "status": "failed"
            if any(report.get("status") == "failed" for report in phonetic_reports.values())
            else "warning"
            if any(report.get("status") == "warning" for report in phonetic_reports.values())
            else "passed",
            "reports": phonetic_reports,
        }
        (OUTPUT_DIR / "phonetic_resolution_report.json").write_text(
            json.dumps(aggregate_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (OUTPUT_DIR.parent / "phonetic_resolution_report.json").write_text(
            json.dumps(aggregate_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
