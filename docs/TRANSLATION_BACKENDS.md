# Translation Backends

Allowed translation priority:

1. IndicTrans2 for supported pairs.
2. Llama/Ollama only for explicit translation requests, unsupported fallback when enabled, or optional post-editing when enabled.
3. deep-translator only as explicit last-resort fallback.

## IndicTrans2

IndicTrans2 is the primary engine for supported language pairs. The router must never silently use Llama/Ollama or deep-translator for a pair supported by IndicTrans2.

Phase 3A production routing now calls the router from `translation/run_translate.py`.
For `en -> kn`, the selected engine is IndicTrans2. If `.venv_indictrans2` or
the model is unavailable, the production stage fails loudly and does not use
Llama/deep-translator.

## Llama/Ollama

Llama/Ollama is allowed for non-translation reasoning/planning and for translation only when explicitly configured or when an unsupported pair allows LLM fallback.

## deep-translator

deep-translator is a last-resort fallback only. It is not the primary translation path for supported IndicTrans2 pairs.

Existing `VIDIOLINGUA_TRANSLATION_ENGINE=google` compatibility is preserved for
unsupported pairs such as `en -> fr`.

## Validation

```powershell
python -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test." --output outputs/validation/router_translation_en_kn.json
```

Expected policy result: IndicTrans2 selected, Llama not used, deep-translator not used.

## Translation QA / Context Layer

VideoLingua now runs a context-preserving translation QA layer after the primary
translation engine. It checks empty segments, segment counts, expansion ratios,
repetition, numbers, named entities, glossary terms, target script, punctuation,
neighboring segment continuity, and translation-memory consistency hints.

This layer is not a trained translation model and does not replace IndicTrans2.
IndicTrans2 remains the primary engine for supported Indic pairs. Optional LLM
post-editing is disabled by default and must be explicitly enabled; it is never
a silent fallback.

Example validation on existing artifacts:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_translation_qa --source-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --translation-json outputs\kannada_sarvam_practical_test_clipfix\translation\output\Vidiolingua_Test_Official_transcription_kn.json --source-language en --target-language kn --output outputs\validation\translation_qa_kn_report.json
```
# 2026-05-05 Linguistic Integrity Addendum

Supported Indic pairs remain routed to IndicTrans2 first. After translation, Vidiolingua now runs a separate linguistic integrity report over the translated segments.

Checks include script ratio, English leakage, empty translations, repetition, expansion ratio, punctuation, number preservation, name/acronym/project-term preservation, and segment alignment.

This is a validation layer around translation output. It is not a trained grammar correction model and it does not introduce silent LLM or deep-translator fallback for IndicTrans2-supported pairs.
