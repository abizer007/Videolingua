# Phase 3A Router Integration Report

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Production Files Touched

- `translation/run_translate.py`
- `tts/run_tts.py`
- `app/routers/tts_router.py`
- `backend/pipeline_runner.py`
- `.env.example`
- `tools/validate_translation_router.py`
- `tools/validate_voice_router.py`
- `tools/validate_full_text_to_voice.py`
- `tools/inspect_pipeline_config.py`

## Docs Touched

- `docs/PROJECT_PIPELINE.md`
- `docs/VOICE_BACKENDS.md`
- `docs/TRANSLATION_BACKENDS.md`
- `docs/INDICF5_SETUP.md`
- `docs/INDICTRANS2_SETUP.md`
- `docs/TROUBLESHOOTING.md`

## What Is Now Wired Into Production

- `translation/run_translate.py` calls the translation router for engine selection.
- Supported IndicTrans2 pairs select IndicTrans2 and fail loudly if the worker/env/model is unavailable.
- Unsupported pairs can still use configured legacy Google/deep-translator compatibility, preserving the French practical path.
- `tts/run_tts.py` calls the voice router for cloned backend selection while preserving existing per-segment timing assembly.
- `app/routers/tts_router.py` uses the voice router for API TTS selection.
- `backend/pipeline_runner.py` accepts `--reference-text` and `--reference-text-path` and passes reference text into TTS env.

## What Remains Scaffold-only

- IndicTrans2 model invocation in `workers/indictrans2_worker.py`.
- `.venv_indictrans2` setup.
- IndicF5 separate runtime install in `.venv_indicf5`.
- Actual IndicF5 generation until dependencies/model access are approved.

## Translation Behavior

- `en -> kn`: selects IndicTrans2. Missing worker/env/model fails loudly; no Llama/deep-translator fallback.
- `en -> fr`: does not require IndicTrans2. With `VIDIOLINGUA_TRANSLATION_ENGINE=google`, existing deep-translator behavior is preserved.

## Voice Behavior

- `fr`: selects XTTS when cloning is required.
- `kn`: selects IndicF5 when cloning is required and reference text is present.
- `hi`: selects IndicF5 when cloning is required and reference text is present.
- Missing IndicF5 reference text fails before model loading.

## XTTS Preservation

- `voice/xtts_cloner.py` was not changed in Phase 3A.
- The production XTTS call still goes through `app/services/xtts_tts_service.py`.
- XTTS model path normalization remains directory-safe.
- `.venv_tts` was not modified.

## IndicF5 / IndicTrans2 Failure Mode

- IndicF5 still fails loudly until the separate IndicF5 runtime is installed.
- IndicTrans2 still fails loudly until `.venv_indictrans2` and model invocation are installed.

## Generic Fallback

Generic fallback is blocked when `cloning_required=true`. Legacy/Hume/gTTS remain only for debug or non-cloning modes.

## Indic Parler

No runtime Indic Parler imports or requirements were added.

## Validation Results

- Compileall over `backend asr translation tts lipsync tools voice app workers`: passed.
- `.venv_tts` `BeamSearchScorer` import: passed.
- `.venv_tts` torch sanity: `2.5.1+cpu`, CUDA false, GPU none.
- XTTS model directory check: passed.
- Config inspection: passed; `.venv_indictrans2` is not present, as expected.
- `en -> kn` translation dry-run: selected IndicTrans2, no Llama, no deep-translator.
- `en -> fr` translation dry-run: blocked under `auto` with clear unsupported-pair fallback policy; production env `google` still uses deep-translator for compatibility.
- Kannada voice dry-run: selected IndicF5, no XTTS, no generic fallback.
- French voice dry-run: selected XTTS.
- Hindi voice dry-run: selected IndicF5.
- Kannada missing reference text dry-run: failed clearly before model loading.
- No-Parler runtime scan: no matches.
- French practical regression: first run exposed a production import-path issue in `translation/run_translate.py`; after fixing `sys.path`, rerun passed and wrote `outputs\french_after_phase3a_router_integration_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4`.
- Protected known-good output `outputs\french_official_test` was not overwritten.

## Next Steps For Phase 3B

1. Approve exact `.venv_indictrans2` setup commands.
2. Approve exact `.venv_indicf5` setup commands.
3. Activate worker model invocation after dependencies are installed.
4. Run small model-level validation before any full video pipeline run.
