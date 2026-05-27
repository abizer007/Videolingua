# Phase 3C IndicF5 Quarantine And Fresh Scaffold Report

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Summary

Old failed IndicF5 runtime remnants were moved to
`_legacy\failed_indicf5_attempt_20260429`. Fresh lightweight scaffolding was
created in the runtime paths so imports and compile checks continue to work.

No dependencies were installed. No models were downloaded. No real IndicF5
generation or full video pipeline was run.

## Quarantined

- `.venv_indicf5`
- `ml\IndicF5`
- `jobs\codex_hindi_indicf5_test`
- `jobs\codex_hindi_indicf5_strict`
- `jobs\indicf5_prompts`
- `jobs\indicf5_smoke.wav`
- `jobs\indicf5_smoke_14s.wav`
- `jobs\indicf5_official_prompt_smoke.wav`
- `jobs\indicf5_user_ref_smoke_after_patch.wav`
- `jobs\indicf5_openvoice_bridge_smoke.wav`
- `app\services\indicf5_tts_service.py`
- `workers\indicf5_worker.py`
- `voice\engines\indicf5_engine.py`
- `requirements-indicf5.txt`

`docs\INDICF5_SETUP.md` was copied to
`_legacy\failed_indicf5_attempt_20260429\archived_old_INDICF5_SETUP.md` and then
replaced in-place with fresh instructions.

## Fresh Files Created

- `requirements-indicf5.txt`
- `scripts\setup_indicf5_env.ps1`
- `workers\indicf5_worker.py`
- `voice\engines\indicf5_engine.py`
- `app\services\indicf5_tts_service.py`
- `docs\INDICF5_SETUP.md`

## Scaffold Status

The fresh worker validates request JSON, reference audio, reference text,
workspace-local cache/temp paths, requested device, and `batch_size=1` before
model work. It fails clearly if `.venv_indicf5` dependencies are missing or if
real model invocation is attempted before the install/model phase.

The fresh engine calls the worker subprocess through `VIDIOLINGUA_INDICF5_PYTHON`
or the default `.venv_indicf5\Scripts\python.exe`. It does not import heavy
IndicF5 dependencies in the API/TTS process and does not provide generic
fallback.

The fresh API service wrapper delegates to the engine. It does not call
`snapshot_download` and does not import model code.

## Runtime Import Changes

Old in-process IndicF5 service code is now isolated in `_legacy`. Runtime imports
now point to fresh lightweight wrappers only. XTTS files and models were not
changed.

## Still Needs Approval

- Recreate fresh `.venv_indicf5` using Python 3.11.11.
- Install CUDA PyTorch and clean IndicF5 requirements into `.venv_indicf5`.
- Download or validate access to `ai4bharat/IndicF5`.
- Implement/enable real model invocation after dependency and model validation.

## Protected Assets

- `.venv_tts`: untouched
- `.venv_indictrans2`: untouched
- `models\xtts_v2`: untouched
- `outputs\french_official_test`: untouched

## Validation

Validation commands and results are recorded in `COMMAND_LOG.md`.

Results:

- `compileall backend asr translation tts lipsync tools voice app workers`: passed.
- `tools.inspect_pipeline_config`: passed; `indicf5_python` is now absent as expected until fresh install; `indic_parler` remains `disabled_absent_forbidden`.
- `tools.validate_voice_router` Kannada with reference text: passed; selected `indicf5`, no XTTS, no generic fallback, no Parler, policy-only.
- `tools.validate_voice_router` Kannada without reference text: blocked as expected with `IndicF5 requires the exact transcript of the reference audio`.
- `tools.validate_voice_router` French: passed; selected `xtts`, no IndicF5, no generic fallback.
- XTTS health checks passed: `BeamSearchScorer` import OK; `.venv_tts` torch remains `2.5.1+cpu` with CUDA false.
- No runtime Indic Parler imports or requirements entries were found.

The setup script dry run works through process-local PowerShell execution policy
bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_indicf5_env.ps1
```

Direct script execution was blocked by the machine PowerShell execution policy,
which does not affect the script contents or planned commands.
