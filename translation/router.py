"""Strict translation router.

The router enforces the project policy: IndicTrans2 is primary for supported
language pairs, while Llama/Ollama and deep-translator require explicit
configuration and are never silent fallbacks for supported IndicTrans2 pairs.
"""

from __future__ import annotations

from .base import (
    TranslationRequest,
    TranslationResult,
    UnsupportedLanguagePairError,
    indictrans2_supports_pair,
    normalize_language_code,
)


VALID_TRANSLATION_ENGINES = {"auto", "indictrans2", "llama", "llama3", "ollama", "deep_translator", "google"}


def normalize_engine_name(engine: str) -> str:
    chosen = (engine or "auto").strip().lower().replace("-", "_")
    if chosen == "google":
        return "deep_translator"
    if chosen in {"llama3", "ollama"}:
        return "llama"
    return chosen if chosen in VALID_TRANSLATION_ENGINES else "auto"


def select_translation_engine(request: TranslationRequest) -> str:
    preferred = normalize_engine_name(request.preferred_engine)
    source = normalize_language_code(request.source_language)
    target = normalize_language_code(request.target_language)
    supported_indic_pair = indictrans2_supports_pair(source, target)

    if source == target:
        return "identity"

    if preferred == "indictrans2":
        if not supported_indic_pair:
            raise UnsupportedLanguagePairError(
                f"IndicTrans2 does not support translation pair {source}->{target}"
            )
        return "indictrans2"

    if preferred == "llama":
        return "llama"

    if preferred == "deep_translator":
        return "deep_translator"

    if preferred != "auto":
        raise UnsupportedLanguagePairError(f"Unknown translation engine '{request.preferred_engine}'")

    if supported_indic_pair:
        return "indictrans2"
    if request.allow_llm_fallback:
        return "llama"
    if request.allow_deep_translator_fallback:
        return "deep_translator"
    raise UnsupportedLanguagePairError(
        f"No translation engine allowed for unsupported pair {source}->{target}. "
        "Enable allow_llm_fallback or allow_deep_translator_fallback explicitly."
    )


def translate(request: TranslationRequest) -> TranslationResult:
    engine = select_translation_engine(request)
    source = normalize_language_code(request.source_language)
    target = normalize_language_code(request.target_language)

    if engine == "identity":
        return TranslationResult(
            engine="identity",
            source_language=source,
            target_language=target,
            source_text=request.source_text,
            translated_text=request.source_text,
            used_indictrans2=False,
            used_llm=False,
            used_deep_translator=False,
            fallback_used=False,
            metadata={"reason": "source and target languages match"},
        )
    if engine == "indictrans2":
        from .engines.indictrans2_engine import IndicTrans2Engine

        return IndicTrans2Engine().translate(request)
    if engine == "llama":
        from .engines.llama_engine import LlamaTranslationEngine

        return LlamaTranslationEngine().translate(request)
    if engine == "deep_translator":
        from .engines.deep_translator_engine import DeepTranslatorEngine

        return DeepTranslatorEngine().translate(request)
    raise UnsupportedLanguagePairError(f"No translation engine implementation for '{engine}'")

