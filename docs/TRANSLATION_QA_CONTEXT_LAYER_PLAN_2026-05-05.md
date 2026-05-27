# Translation QA Context Layer Plan - 2026-05-05

## 1. Current Translation Flow

VideoLingua keeps translation as a stage-isolated subprocess. `backend/pipeline_runner.py` copies ASR JSON into a per-job `translation/input` folder, runs `translation/run_translate.py`, then copies produced translation JSON into `tts/input`.

The translation JSON keeps the existing downstream shape:

- `video_file`
- `segments[]` with `id`, `start`, `end`, `text`, `speaker`, and `words`
- `language`
- `source_language`
- `translation_engine`
- `translation_policy`

Pipeline metadata is collected from translation JSON by `_load_translation_evidence()` and surfaced through `job_store`, `pipeline_result.json`, `job_manifest.json`, and the frontend.

## 2. Where IndicTrans2 Is Used

`translation/router.py` selects IndicTrans2 for supported IndicTrans2 language pairs when `preferred_engine=auto`. `translation/run_translate.py` calls this router for each segment. For supported pairs such as `en -> kn`, `IndicTrans2Engine` shells out to `workers.indictrans2_worker` through the isolated `.venv_indictrans2` Python configured by `VIDIOLINGUA_INDICTRANS2_PYTHON`.

If IndicTrans2 is selected and unavailable, the translation stage fails loudly. It must not silently fall back to Llama/Ollama or deep-translator for supported pairs.

## 3. Llama/Ollama And deep-translator Role

Llama/Ollama and deep-translator remain allowed only in the existing explicit roles:

- unsupported translation pairs when the matching fallback flag is explicitly enabled;
- direct explicit engine selection where policy allows it;
- optional post-editing after primary translation only when explicitly enabled.

They do not replace IndicTrans2 for supported Indic pairs. This phase must not claim new model training or promote an LLM as the primary translator.

## 4. Proposed QA/Post-Edit Architecture

Add a stdlib-first validation layer after primary translation:

```text
ASR segments
-> primary translation router output
-> translation QA/context analysis
-> translation_qa_report.json
-> backend metrics/analysis/manifest/API
-> frontend translation integrity UI
-> TTS receives the same translation JSON unless critical QA failure stops the job
```

The central API will be:

```python
analyze_translation_segments(
    source_segments,
    translated_segments,
    source_language,
    target_language,
    glossary=None,
    context_window_size=2,
    enable_post_edit=False,
    post_edit_engine=None,
)
```

This returns a serializable report with status, checks, segment reports, warnings, errors, glossary state, translation-memory hits, and post-edit metadata.

## 5. Data / Schema Changes

Add `translation_qa` to each translation JSON:

- `status`
- compact check summary
- warning/error counts
- report filename/path if available
- `post_edit_used=false` unless explicitly run

Write a full report to:

```text
<translation output dir>\translation_qa_report.json
```

For per-job pipeline runs that means:

```text
<job_dir>\translation\output\translation_qa_report.json
```

Expose a compact API shape as `translationQA`:

- `status`
- `checksPassed`
- `warningsCount`
- `errorsCount`
- `emptySegments`
- `scriptMatch`
- `numberIssues`
- `entityIssues`
- `expansionRatioWarnings`
- `reportPath`

Use artifact names rather than sensitive local paths in frontend-facing surfaces when possible.

## 6. Files To Add / Modify

Add:

- `translation/validation/translation_quality.py`
- `translation/validation/entity_preservation.py`
- `translation/validation/script_checks.py`
- `translation/validation/glossary.py`
- `translation/validation/context_window.py`
- `translation/validation/translation_memory.py`
- `translation/cache/translation_memory.py`
- `config/translation_glossary.example.json`
- `tools/validate_translation_qa.py`
- `docs/TRANSLATION_QA_CONTEXT_LAYER_REPORT_2026-05-05.md`

Modify:

- `translation/run_translate.py`
- `backend/pipeline_runner.py`
- `backend/job_manifest.py` if a summary/artifact hook is needed
- `backend/job_store.py`
- `evaluation/report_builder.py`
- `NEW_Frontend/lib/types.ts`
- `NEW_Frontend/app/pipeline/page.tsx`
- `NEW_Frontend/components/vidiolingua/pipeline-timeline.tsx`
- `NEW_Frontend/app/results/page.tsx`
- `NEW_Frontend/app/architecture/page.tsx`
- `NEW_Frontend/app/backends/page.tsx`
- `NEW_Frontend/app/page.tsx` or a homepage component
- requested docs and `COMMAND_LOG.md`

## 7. Glossary Support

Glossary JSON will be optional and loaded from:

1. `--glossary` in validation CLI and future direct CLIs;
2. `VIDIOLINGUA_TRANSLATION_GLOSSARY`;
3. no glossary when absent.

Initial behavior is conservative:

- validate that configured terms appear or are reasonably preserved;
- detect preserve terms as named entities;
- include glossary domain and missing-term warnings in the report;
- avoid aggressive placeholder substitution in production translation.

Placeholder pre-protection can be added later after focused testing, but this phase will not mutate source text before IndicTrans2 by default.

## 8. Translation Memory

Add a lightweight JSONL memory helper under `translation/cache/translation_memory.py`.

Key fields:

- source language
- target language
- normalized source text hash
- glossary hash
- translation engine
- optional domain

Value fields:

- translated text
- quality status
- created timestamp

In this phase the memory is a reporting and consistency hint layer. It can count repeated segment hits and record successful translations, but it must not override the router or replace freshly produced primary translations unless a later safe policy is explicitly added.

## 9. Context-Window Checks

The QA layer will inspect neighboring source/translation segments with a default window size of 2:

- abrupt empty or missing neighbor;
- repeated translations across adjacent unrelated source segments;
- named entities introduced earlier and later lost;
- consistency warnings for glossary/entity preservation.

These are heuristics, not claims of human-level discourse understanding.

## 10. Optional LLM Post-Edit Gate

Environment gates:

```text
VIDIOLINGUA_ENABLE_LLM_POST_EDIT=false
VIDIOLINGUA_LLM_POST_EDIT_ENGINE=ollama
VIDIOLINGUA_LLM_POST_EDIT_MODEL=
```

Default is disabled. If enabled later, post-editing runs only after primary translation and must record:

- `post_edit_used=true`
- engine/model
- before/after metadata
- skipped/unavailable reason when requested but unavailable

For this phase, implementation should be scaffolded and loudly disabled unless the gate is explicitly true. It must not create silent LLM fallback and must not replace IndicTrans2.

## 11. Frontend Reflection

No separate page is needed. Add visible but restrained surfaces:

- pipeline page/timeline: Translation QA pending/running/completed plus checks for script, empty segment, numbers/entities, expansion ratio, glossary, and memory;
- results page: a "Translation integrity" or "Context QA" evidence panel with status and issue counts;
- architecture page: QA layer shown as part of the translation router;
- backends/feature areas: short mention of translation integrity checks without model-training claims;
- homepage: small feature mention that names, numbers, scripts, and segment context are checked.

## 12. Validation Plan

Run light checks only:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_translation_qa --source-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --translation-json outputs\kannada_sarvam_practical_test_clipfix\translation\output\Vidiolingua_Test_Official_transcription_kn.json --source-language en --target-language kn --output outputs\validation\translation_qa_kn_report.json
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\translation_qa_router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\translation_qa_router_fr.wav --dry-run
```

Frontend:

```powershell
cd D:\Vidiolingua\NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

Do not run the full pipeline or regenerate protected proof artifacts.

## 13. Risks And Rollback Notes

Risks:

- over-brittle QA could stop valid translations;
- script checks can produce false positives for proper nouns or romanized terms;
- number/entity preservation is heuristic without heavy NER;
- historical outputs may lack QA metadata;
- optional post-editing must stay visibly disabled unless explicitly enabled.

Rollback:

- remove the QA call after translation;
- stop registering `translation_qa_report.json`;
- leave the primary translation router untouched;
- keep translation JSON shape compatible for TTS.

Protected state notes:

- no `.venv_*` mutation;
- no model files touched;
- no protected output regeneration;
- no Sarvam key exposure;
- no IndicF5 load;
- no Indic Parler;
- no generic fallback.
