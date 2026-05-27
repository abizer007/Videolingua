"""deep-translator adapter used only as explicit last-resort fallback."""

from __future__ import annotations

from translation.base import TranslationRequest, TranslationResult, normalize_language_code


class DeepTranslatorEngine:
    name = "deep_translator"

    def translate(self, request: TranslationRequest) -> TranslationResult:
        from translation.run_translate import _translate_google

        source = normalize_language_code(request.source_language)
        target = normalize_language_code(request.target_language)
        translated = _translate_google(request.source_text, source, target)
        return TranslationResult(
            engine=self.name,
            source_language=source,
            target_language=target,
            source_text=request.source_text,
            translated_text=translated,
            used_indictrans2=False,
            used_llm=False,
            used_deep_translator=True,
            fallback_used=True,
            metadata={"explicit_or_allowed_fallback": True, "segment_id": request.segment_id},
        )

