"""Shared voice synthesis contracts and language policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class VoiceSynthesisError(RuntimeError):
    """Base error for voice routing and synthesis failures."""


XTTS_SUPPORTED_LANGS = {
    "ar",
    "cs",
    "de",
    "en",
    "es",
    "fr",
    "hu",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "ru",
    "tr",
    "zh",
}

INDICF5_SUPPORTED_LANGS = {
    "as",
    "bn",
    "gu",
    "hi",
    "kn",
    "ml",
    "mr",
    "or",
    "pa",
    "ta",
    "te",
}

SARVAM_SUPPORTED_LANGS = {
    "bn",
    "gu",
    "hi",
    "kn",
    "ml",
    "mr",
    "or",
    "pa",
    "ta",
    "te",
}

SARVAM_LANGUAGE_CODES = {
    "bn": "bn-IN",
    "gu": "gu-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "or": "od-IN",
    "pa": "pa-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "en": "en-IN",
}


@dataclass(frozen=True)
class VoiceSynthesisRequest:
    text: str
    target_language: str
    output_path: Path
    reference_audio_path: Optional[Path] = None
    reference_text: Optional[str] = None
    preferred_engine: str = "auto"
    cloning_required: bool = True
    allow_generic_fallback: bool = False
    allow_xtts_to_indicf5_fallback: bool = False
    force_regenerate: bool = False
    segment_id: Optional[str] = None


@dataclass(frozen=True)
class VoiceSynthesisResult:
    engine: str
    output_path: Path
    sample_rate: int
    duration_sec: float
    used_reference_audio: bool
    used_reference_text: bool
    fallback_used: bool
    cache_hit: bool
    metadata: dict = field(default_factory=dict)


def normalize_voice_language(language_code: str) -> str:
    code = (language_code or "").strip().lower().replace("_", "-").split("-")[0]
    if code == "od":
        return "or"
    return code


def xtts_supports_language(language_code: str) -> bool:
    return normalize_voice_language(language_code) in XTTS_SUPPORTED_LANGS


def indicf5_supports_language(language_code: str) -> bool:
    return normalize_voice_language(language_code) in INDICF5_SUPPORTED_LANGS


def sarvam_supports_language(language_code: str, *, include_english: bool = False) -> bool:
    language = normalize_voice_language(language_code)
    return language in SARVAM_SUPPORTED_LANGS or (include_english and language == "en")


def sarvam_target_language_code(language_code: str, *, include_english: bool = False) -> str:
    language = normalize_voice_language(language_code)
    if not sarvam_supports_language(language, include_english=include_english):
        raise VoiceSynthesisError(f"Sarvam does not support language '{language_code}'")
    return SARVAM_LANGUAGE_CODES[language]
