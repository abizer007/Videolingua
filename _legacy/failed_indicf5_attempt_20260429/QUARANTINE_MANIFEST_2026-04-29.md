# IndicF5 Failed Attempt Quarantine Manifest

Date: 2026-04-29
Workspace: `D:\Vidiolingua`
Quarantine folder: `D:\Vidiolingua\_legacy\failed_indicf5_attempt_20260429`

## Reason

These items came from a failed earlier IndicF5 attempt and should not be trusted
for the clean Phase 3C implementation. They were moved or copied here to keep a
recoverable archive without deleting anything permanently.

## Moved Items

| Original path | Quarantined path |
| --- | --- |
| `.venv_indicf5` | `_legacy\failed_indicf5_attempt_20260429\.venv_indicf5` |
| `ml\IndicF5` | `_legacy\failed_indicf5_attempt_20260429\IndicF5` |
| `jobs\codex_hindi_indicf5_test` | `_legacy\failed_indicf5_attempt_20260429\codex_hindi_indicf5_test` |
| `jobs\codex_hindi_indicf5_strict` | `_legacy\failed_indicf5_attempt_20260429\codex_hindi_indicf5_strict` |
| `jobs\indicf5_prompts` | `_legacy\failed_indicf5_attempt_20260429\indicf5_prompts` |
| `jobs\indicf5_smoke.wav` | `_legacy\failed_indicf5_attempt_20260429\indicf5_smoke.wav` |
| `jobs\indicf5_smoke_14s.wav` | `_legacy\failed_indicf5_attempt_20260429\indicf5_smoke_14s.wav` |
| `jobs\indicf5_official_prompt_smoke.wav` | `_legacy\failed_indicf5_attempt_20260429\indicf5_official_prompt_smoke.wav` |
| `jobs\indicf5_user_ref_smoke_after_patch.wav` | `_legacy\failed_indicf5_attempt_20260429\indicf5_user_ref_smoke_after_patch.wav` |
| `jobs\indicf5_openvoice_bridge_smoke.wav` | `_legacy\failed_indicf5_attempt_20260429\indicf5_openvoice_bridge_smoke.wav` |
| `app\services\indicf5_tts_service.py` | `_legacy\failed_indicf5_attempt_20260429\indicf5_tts_service.py` |
| `workers\indicf5_worker.py` | `_legacy\failed_indicf5_attempt_20260429\indicf5_worker.py` |
| `voice\engines\indicf5_engine.py` | `_legacy\failed_indicf5_attempt_20260429\indicf5_engine.py` |
| `requirements-indicf5.txt` | `_legacy\failed_indicf5_attempt_20260429\requirements-indicf5.txt` |

## Copied Items

| Original path | Archive copy |
| --- | --- |
| `docs\INDICF5_SETUP.md` | `_legacy\failed_indicf5_attempt_20260429\archived_old_INDICF5_SETUP.md` |

## Skipped Or Missing Items

None. Every approved quarantine item was present and moved.

## Restore Instructions

Do not restore these files blindly. If a rollback is approved, move the needed
item from this folder back to its original path, then run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
```

The preferred path is to keep these archived and proceed with the fresh
`.venv_indicf5` setup after approval.
