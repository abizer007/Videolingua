"""Shared translation contracts and policy helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


class TranslationError(RuntimeError):
    """Base error for translation routing and engine failures."""


class UnsupportedLanguagePairError(TranslationError):
    """Raised when no configured translation engine may handle a pair."""


SUPPORTED_INDICTRANS2_LANGS = {
    "as",
    "bn",
    "brx",
    "doi",
    "en",
    "gom",
    "gu",
    "hi",
    "kn",
    "ks",
    "mai",
    "ml",
    "mni",
    "mr",
    "ne",
    "or",
    "pa",
    "sa",
    "sat",
    "sd",
    "ta",
    "te",
    "ur",
}

_LANG_ALIASES = {
    "eng": "en",
    "english": "en",
    "hin": "hi",
    "hindi": "hi",
    "kan": "kn",
    "kannada": "kn",
    "oriya": "or",
    "odia": "or",
    "od": "or",
}


@dataclass(frozen=True)
class TranslationRequest:
    source_text: str
    source_language: str
    target_language: str
    preferred_engine: str = "auto"
    allow_llm_fallback: bool = False
    allow_deep_translator_fallback: bool = False
    allow_llm_post_edit: bool = False
    domain: Optional[str] = None
    preserve_timestamps: bool = True
    segment_id: Optional[str] = None


@dataclass(frozen=True)
class TranslationResult:
    engine: str
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    used_indictrans2: bool
    used_llm: bool
    used_deep_translator: bool
    fallback_used: bool
    metadata: dict = field(default_factory=dict)


def normalize_language_code(language: str) -> str:
    code = (language or "").strip().lower().replace("_", "-")
    code = re.split(r"[-.]", code)[0]
    return _LANG_ALIASES.get(code, code)


def indictrans2_supports_language(language: str) -> bool:
    return normalize_language_code(language) in SUPPORTED_INDICTRANS2_LANGS


def indictrans2_supports_pair(source_language: str, target_language: str) -> bool:
    source = normalize_language_code(source_language)
    target = normalize_language_code(target_language)
    if not source or not target or source == target:
        return False
    return source in SUPPORTED_INDICTRANS2_LANGS and target in SUPPORTED_INDICTRANS2_LANGS

