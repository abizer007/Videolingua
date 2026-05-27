"""
TTS router utilities and health endpoint.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

from app.services.hume_tts_service import is_configured as hume_is_configured
from app.services.hume_tts_service import synthesize_to_wav as hume_synthesize_to_wav
from voice.base import (
    VoiceSynthesisRequest,
    indicf5_supports_language,
    normalize_voice_language,
    sarvam_supports_language,
    xtts_supports_language,
)
from voice.router import select_voice_engine

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_ENGINES = {"auto", "sarvam", "indicf5", "xtts", "hume", "legacy"}
_INDICF5_LANGS = {"as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}
_SARVAM_LANGS = {"bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}
_XTTS_LANGS = {
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
    "nl", "cs", "ar", "zh", "hu", "ko", "ja",
}


def get_tts_engine() -> str:
    engine = os.environ.get("VIDIOLINGUA_TTS_ENGINE", "auto").strip().lower()
    return engine if engine in _VALID_ENGINES else "legacy"


def _env_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _cloning_required(voice_options: Optional[dict] = None) -> bool:
    required = os.environ.get("VOICE_CLONING_REQUIRED", "").strip().lower()
    if required:
        return required in {"1", "true", "yes", "on"}
    if _env_true("VIDIOLINGUA_REQUIRE_VOICE_CLONE"):
        return True
    if _env_true("ALLOW_GENERIC_TTS_FALLBACK"):
        return False
    if voice_options and "cloned" in voice_options:
        return bool(voice_options.get("cloned"))
    return True


def _lang_base(language_code: str) -> str:
    return normalize_voice_language(language_code or "en")


def _reference_text(speaker_wav: str | None) -> str | None:
    text = os.environ.get("VIDIOLINGUA_REFERENCE_TEXT", "").strip()
    if text:
        return text
    text_path = os.environ.get("VIDIOLINGUA_REFERENCE_TEXT_PATH", "").strip()
    if text_path:
        path = Path(text_path)
        if not path.is_file():
            raise RuntimeError(f"Configured VIDIOLINGUA_REFERENCE_TEXT_PATH does not exist: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Configured VIDIOLINGUA_REFERENCE_TEXT_PATH is empty: {path}")
        return text
    legacy = os.environ.get("VIDIOLINGUA_VOICE_SAMPLE_TEXT", "").strip()
    if legacy:
        return legacy
    if speaker_wav:
        sidecar = Path(speaker_wav).with_suffix(".txt")
        if sidecar.is_file():
            return sidecar.read_text(encoding="utf-8").strip() or None
    return None


def _indic_voice_backend() -> str:
    backend = os.environ.get("VIDIOLINGUA_INDIC_VOICE_BACKEND", "sarvam").strip().lower()
    return backend if backend in {"sarvam", "indicf5", "disabled"} else "sarvam"


def synthesize_tts(
    text: str,
    language_code: str,
    output_path: Path,
    voice_options: Optional[dict] = None,
    voice_id: Optional[str] = None,
) -> Path:
    engine = get_tts_engine()
    lang = _lang_base(language_code)
    speaker_wav = os.environ.get("SPEAKER_REFERENCE_AUDIO") or os.environ.get("VIDIOLINGUA_VOICE_SAMPLE")
    reference_text = _reference_text(speaker_wav)
    cloning_required = _cloning_required(voice_options)
    preferred = engine
    if not cloning_required and engine in {"hume", "legacy"}:
        logger.info("TTS debug/legacy engine selected: %s", engine)
    elif not cloning_required and engine == "auto" and not speaker_wav:
        engine = "legacy"
        logger.info("TTS debug/legacy engine selected: legacy")
    else:
        if (
            cloning_required
            and engine == "xtts"
            and not xtts_supports_language(lang)
            and (sarvam_supports_language(lang) or indicf5_supports_language(lang))
        ):
            preferred = "auto"
        engine = select_voice_engine(
            VoiceSynthesisRequest(
                text=text,
                target_language=lang,
                output_path=output_path,
                reference_audio_path=Path(speaker_wav) if speaker_wav else None,
                reference_text=reference_text,
                preferred_engine=preferred,
                cloning_required=cloning_required,
                allow_generic_fallback=_env_true("VIDIOLINGUA_ALLOW_GENERIC_TTS_FALLBACK")
                or _env_true("ALLOW_GENERIC_TTS_FALLBACK"),
            )
        )
        logger.info(
            "TTS engine selected: engine=%s target_language=%s xtts_supported=%s "
            "sarvam_supported=%s indicf5_supported=%s cloning_required=%s reference_audio=%s "
            "reference_text_present=%s fallback_used=false managed_tts=%s "
            "exact_voice_clone=%s speaker_preservation=%s output=%s",
            engine,
            lang,
            xtts_supports_language(lang),
            sarvam_supports_language(lang),
            indicf5_supports_language(lang),
            cloning_required,
            speaker_wav,
            bool(reference_text),
            engine == "sarvam",
            engine != "sarvam",
            "not_supported" if engine == "sarvam" else "reference_conditioned",
            output_path,
        )

    if engine == "hume":
        return hume_synthesize_to_wav(text, output_path, voice_options, voice_id)

    if engine == "indicf5":
        from app.services import indicf5_tts_service

        return indicf5_tts_service.synthesize_to_wav(
            text=text,
            language_code=language_code,
            output_path=output_path,
            voice_options=voice_options,
            voice_id=voice_id,
            speaker_wav=speaker_wav,
            ref_text=reference_text,
        )

    if engine == "sarvam":
        from voice.engines.sarvam_engine import SarvamEngine

        return SarvamEngine().synthesize(
            VoiceSynthesisRequest(
                text=text,
                target_language=language_code,
                output_path=output_path,
                preferred_engine="sarvam",
                cloning_required=True,
                allow_generic_fallback=False,
            )
        ).output_path

    if engine == "xtts":
        from app.services import xtts_tts_service

        return xtts_tts_service.synthesize_to_wav(
            text=text,
            language_code=language_code,
            output_path=output_path,
            voice_options=voice_options,
            voice_id=voice_id,
            speaker_wav=speaker_wav,
        )

    if _cloning_required(voice_options):
        raise RuntimeError("Generic TTS fallback is disabled because voice cloning is required")

    from tts.run_tts import _synthesize_legacy

    return _synthesize_legacy(text, language_code, output_path, voice_options, voice_id)


@router.get("/tts-health")
@router.get("/api/tts-health")
def tts_health():
    return {
        "engine": get_tts_engine(),
        "indic_voice_backend": _indic_voice_backend(),
        "sarvam_configured": bool(os.environ.get("SARVAM_API_KEY", "").strip()),
        "sarvam_languages": sorted(_SARVAM_LANGS),
        "hume_configured": hume_is_configured(),
    }
