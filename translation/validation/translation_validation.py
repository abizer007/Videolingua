"""Lightweight validation for translation requests and results."""

from __future__ import annotations

from translation.base import TranslationError, TranslationRequest, TranslationResult, normalize_language_code


def validate_translation_request(request: TranslationRequest) -> None:
    if not (request.source_text or "").strip():
        raise TranslationError("Translation requires non-empty source_text")
    if not normalize_language_code(request.source_language):
        raise TranslationError("Translation requires source_language")
    if not normalize_language_code(request.target_language):
        raise TranslationError("Translation requires target_language")


def validate_translation_result(result: TranslationResult) -> None:
    if not (result.translated_text or "").strip():
        raise TranslationError("Translation result is empty")
    if result.used_indictrans2 and (result.used_llm or result.used_deep_translator):
        raise TranslationError("Translation result mixed IndicTrans2 with fallback engines")

