# Translation QA Context Layer Report - 2026-05-05

## 1. What Was Added

Added a context-preserving translation QA and post-edit layer around the existing translation router. The layer runs after primary translation, writes JSON QA reports, and surfaces a compact `translationQA` summary through backend job status/result metadata and the frontend.

## 2. What It Improves

The layer checks practical translation integrity signals:

- segment count alignment
- empty translated segments
- target-script match
- number preservation
- lightweight named-entity/proper-noun preservation
- glossary preservation
- expansion-ratio anomalies
- repeated translations and repeated tokens/punctuation
- sentence-boundary punctuation loss
- neighboring segment continuity
- translation-memory consistency hints

## 3. What It Does Not Claim

This is not a trained translation model. It does not replace IndicTrans2. It does not claim perfect context-aware or human-level translation. Optional LLM post-editing is disabled by default and was not used in validation.

## 4. QA Checks Implemented

Implemented in `translation/validation`:

- `translation_quality.py`: central report builder and summary schema
- `entity_preservation.py`: numbers, simple dates/currency/percent tokens, acronyms, mixed-case terms, and capitalized phrases
- `script_checks.py`: Kannada, Devanagari, Tamil, Telugu, Bengali, Malayalam, Gujarati, Gurmukhi, Odia, Arabic, Cyrillic, Chinese, Japanese, and Korean script ratios
- `glossary.py`: optional glossary loading, hashing, and preservation checks
- `context_window.py`: neighboring segment repetition and context entity checks
- `translation_memory.py`: memory-hit and consistency reporting

## 5. Glossary Support

Added example glossary:

```text
config\translation_glossary.example.json
```

Runtime lookup supports:

```text
VIDIOLINGUA_TRANSLATION_GLOSSARY=config\translation_glossary.json
```

The current implementation validates glossary terms conservatively. It does not aggressively replace terms with placeholders before IndicTrans2.

## 6. Translation Memory Support

Added:

```text
translation\cache\translation_memory.py
```

The memory is JSONL-based and keyed by source language, target language, normalized source hash, glossary hash, translation engine, and optional domain. In this phase it is a reporting/consistency hint layer only. It does not override router output.

## 7. Optional LLM Post-Edit Status

Supported configuration gates:

```text
VIDIOLINGUA_ENABLE_LLM_POST_EDIT=false
VIDIOLINGUA_LLM_POST_EDIT_ENGINE=ollama
VIDIOLINGUA_LLM_POST_EDIT_MODEL=
```

Default is disabled. If requested before a post-edit engine is wired, the QA report records a loud skipped warning. LLM post-editing was not used in validation.

## 8. Pipeline Integration

`translation/run_translate.py` now runs QA after translation and writes:

```text
<translation_output>\translation_qa_report.json
<translation_output>\<source_stem>_<target>.translation_qa_report.json
```

Translation JSON receives a compact `translation_qa` summary. `backend/pipeline_runner.py` excludes QA reports from TTS input, registers the QA report as a manifest artifact, and exposes QA metrics/analysis.

## 9. API / Frontend Integration

API status/result can include:

```text
translationQA
```

Frontend additions:

- pipeline page: `Translation integrity`
- pipeline timeline: translation QA details during the translation stage
- results page: `Translation integrity`
- architecture/backends/home sections: QA layer and integrity checks described as guardrails

## 10. Validation Results On Kannada Output

Command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_translation_qa --source-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --translation-json outputs\kannada_sarvam_practical_test_clipfix\translation\output\Vidiolingua_Test_Official_transcription_kn.json --source-language en --target-language kn --output outputs\validation\translation_qa_kn_report.json
```

Result:

- report created: `outputs\validation\translation_qa_kn_report.json`
- status: `warning`
- segment count: `1/1`
- empty translations: `0`
- Kannada script check: passed
- number issues: `0`
- entity warnings: `1`
- errors: `0`

## 11. Remaining Limitations

- Entity preservation is heuristic and does not use heavy NER.
- Transliteration can look like a missing Roman entity even when a translation is acceptable.
- Script thresholds are conservative and may need language/domain tuning.
- Translation memory is advisory only.
- Optional LLM post-editing is scaffolded, not active by default.

## 12. Roadmap

- stronger NER or transliteration-aware entity matching
- COMET/QE model integration where dependencies and runtime policy allow it
- human review workflow for warnings
- domain glossary editor
- context-aware post-edit model gated behind explicit configuration
