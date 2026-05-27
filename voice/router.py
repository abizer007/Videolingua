"""Strict voice backend router."""

from __future__ import annotations

import os
from pathlib import Path

from voice.base import (
    VoiceSynthesisError,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
    indicf5_supports_language,
    normalize_voice_language,
    sarvam_supports_language,
    xtts_supports_language,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "backend" / ".env")
except Exception:
    pass


VALID_VOICE_ENGINES = {"auto", "xtts", "indicf5", "sarvam"}


def normalize_engine_name(engine: str) -> str:
    chosen = (engine or "auto").strip().lower().replace("-", "")
    return chosen if chosen in VALID_VOICE_ENGINES else "auto"


def _require_reference_audio(request: VoiceSynthesisRequest, engine: str) -> None:
    if not request.reference_audio_path or not Path(request.reference_audio_path).is_file():
        raise VoiceSynthesisError(f"{engine} requires a valid reference audio path")


def _require_reference_text(request: VoiceSynthesisRequest, engine: str) -> None:
    if not (request.reference_text or "").strip():
        raise VoiceSynthesisError(f"{engine} requires the exact transcript of the reference audio")


def _env_true(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _indic_voice_backend() -> str:
    backend = os.environ.get("VIDIOLINGUA_INDIC_VOICE_BACKEND", "sarvam").strip().lower()
    return backend if backend in {"sarvam", "indicf5", "disabled"} else "sarvam"


def _sarvam_enabled() -> bool:
    configured = os.environ.get("VIDIOLINGUA_ENABLE_SARVAM", "").strip()
    if configured:
        return _env_true("VIDIOLINGUA_ENABLE_SARVAM")
    return bool(os.environ.get("SARVAM_API_KEY", "").strip())


def _indicf5_execution_enabled() -> bool:
    enabled = _env_true("VIDIOLINGUA_ENABLE_INDICF5") or _env_true("VIDIOLINGUA_INDICF5_ENABLED")
    mode = os.environ.get("VIDIOLINGUA_INDICF5_EXECUTION_MODE", "local_disabled").strip().lower()
    return enabled and mode in {"local_enabled", "enabled"}


def select_voice_engine(request: VoiceSynthesisRequest) -> str:
    preferred = normalize_engine_name(request.preferred_engine)
    language = normalize_voice_language(request.target_language)
    indic_backend = _indic_voice_backend()

    if request.allow_generic_fallback and request.cloning_required:
        raise VoiceSynthesisError("Generic fallback cannot be enabled when cloning_required=true")

    if preferred == "sarvam":
        if not sarvam_supports_language(language):
            raise VoiceSynthesisError(f"Sarvam does not support language '{request.target_language}'")
        if not _sarvam_enabled():
            raise VoiceSynthesisError("Sarvam is selected but VIDIOLINGUA_ENABLE_SARVAM is false or SARVAM_API_KEY is missing")
        return "sarvam"

    if preferred == "xtts":
        if not xtts_supports_language(language):
            raise VoiceSynthesisError(f"XTTS does not support language '{request.target_language}'")
        if request.cloning_required:
            _require_reference_audio(request, "XTTS")
        return "xtts"

    if preferred == "indicf5":
        if not indicf5_supports_language(language):
            raise VoiceSynthesisError(f"IndicF5 does not support language '{request.target_language}'")
        if not _indicf5_execution_enabled():
            raise VoiceSynthesisError(
                "IndicF5 is disabled. Set VIDIOLINGUA_INDIC_VOICE_BACKEND=indicf5, "
                "VIDIOLINGUA_ENABLE_INDICF5=true, and "
                "VIDIOLINGUA_INDICF5_EXECUTION_MODE=local_enabled only after explicit approval."
            )
        _require_reference_audio(request, "IndicF5")
        _require_reference_text(request, "IndicF5")
        return "indicf5"

    if preferred != "auto":
        raise VoiceSynthesisError(f"Unknown voice engine '{request.preferred_engine}'")

    if sarvam_supports_language(language) and indic_backend == "sarvam":
        if not _sarvam_enabled():
            raise VoiceSynthesisError("Sarvam is the configured Indic voice backend but SARVAM_API_KEY is missing or Sarvam is disabled")
        return "sarvam"

    if xtts_supports_language(language):
        if request.cloning_required:
            _require_reference_audio(request, "XTTS")
        return "xtts"

    if indic_backend == "indicf5" and indicf5_supports_language(language):
        if not _indicf5_execution_enabled():
            raise VoiceSynthesisError(
                "IndicF5 is configured but disabled/local_disabled. Use Sarvam or explicitly enable local IndicF5."
            )
        _require_reference_audio(request, "IndicF5")
        _require_reference_text(request, "IndicF5")
        return "indicf5"

    raise VoiceSynthesisError(
        f"No allowed cloned voice backend supports language '{request.target_language}'"
    )


def synthesize_voice(request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
    engine = select_voice_engine(request)
    if engine == "xtts":
        from voice.engines.xtts_engine import XTTSEngine

        result = XTTSEngine().synthesize(request)
    elif engine == "indicf5":
        from voice.engines.indicf5_engine import IndicF5Engine

        result = IndicF5Engine().synthesize(request)
    elif engine == "sarvam":
        from voice.engines.sarvam_engine import SarvamEngine

        result = SarvamEngine().synthesize(request)
    else:
        raise VoiceSynthesisError(f"No voice engine implementation for '{engine}'")

    from voice.audio_validation import validate_generated_audio

    validate_generated_audio(result.output_path)
    return result
