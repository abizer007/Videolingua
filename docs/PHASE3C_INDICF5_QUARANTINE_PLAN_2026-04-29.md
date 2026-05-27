# Phase 3C IndicF5 Quarantine Plan

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

This is a plan only. No files have been moved or deleted.

## Target Quarantine Directory

```text
D:\Vidiolingua\_legacy\failed_indicf5_attempt_20260429
```

## Items Proposed For Quarantine

```text
.venv_indicf5
ml\IndicF5
jobs\codex_hindi_indicf5_test
jobs\codex_hindi_indicf5_strict
jobs\indicf5_prompts
jobs\indicf5_smoke.wav
jobs\indicf5_smoke_14s.wav
jobs\indicf5_official_prompt_smoke.wav
jobs\indicf5_user_ref_smoke_after_patch.wav
jobs\indicf5_openvoice_bridge_smoke.wav
app\services\indicf5_tts_service.py
workers\indicf5_worker.py
voice\engines\indicf5_engine.py
requirements-indicf5.txt
docs\INDICF5_SETUP.md
```

Notes:

- Runtime policy files such as `voice\router.py`, `voice\base.py`, `tools\validate_voice_router.py`, and `backend\pipeline_runner.py` should not be quarantined.
- `tts\run_tts.py` and `app\routers\tts_router.py` should not be quarantined wholesale because they contain working XTTS and production routing code. Only their IndicF5 execution path should be updated after approval.
- `docs\INDICF5_SETUP.md` can be quarantined or superseded; final choice should be confirmed before moving docs.

## Exact Proposed Move Commands

Do not run until approved.

```powershell
$legacy = "D:\Vidiolingua\_legacy\failed_indicf5_attempt_20260429"
New-Item -ItemType Directory -Force -Path $legacy | Out-Null

Move-Item -LiteralPath "D:\Vidiolingua\.venv_indicf5" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\ml\IndicF5" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\codex_hindi_indicf5_test" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\codex_hindi_indicf5_strict" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\indicf5_prompts" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\indicf5_smoke.wav" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\indicf5_smoke_14s.wav" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\indicf5_official_prompt_smoke.wav" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\indicf5_user_ref_smoke_after_patch.wav" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\jobs\indicf5_openvoice_bridge_smoke.wav" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\app\services\indicf5_tts_service.py" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\workers\indicf5_worker.py" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\voice\engines\indicf5_engine.py" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\requirements-indicf5.txt" -Destination $legacy
Move-Item -LiteralPath "D:\Vidiolingua\docs\INDICF5_SETUP.md" -Destination $legacy
```

## Safer Approved-Move Script Shape

If approved, use a guarded PowerShell script that verifies every source path is inside `D:\Vidiolingua` and every destination path is inside `_legacy\failed_indicf5_attempt_20260429` before moving.

## After Quarantine

Create fresh replacements:

```text
requirements-indicf5.txt
scripts\setup_indicf5_env.ps1
workers\indicf5_worker.py
voice\engines\indicf5_engine.py
docs\INDICF5_SETUP.md
```

Then run compile and router dry-run before any install.

## Decision Point

Awaiting user approval before moving anything.
