# Phase 3C IndicF5 Remnants Audit

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

Scope: audit only. No files were moved or deleted. No dependencies were installed.

## Summary

The repo contains two different categories of IndicF5 material:

- Router policy and validation code from Phase 3A that is useful and should be reused.
- Failed implementation/runtime remnants that should not be trusted for Phase 3C.

The safest path is to keep the routing policy, quarantine the old runtime attempt after approval, and build a fresh isolated `.venv_indicf5` plus worker-backed implementation.

## Remnants Classification

| Classification | Path | Purpose | Imported/called now | Runtime effect | XTTS risk | Indic Parler? | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KEEP_AND_REUSE | `voice\base.py` | Shared voice contracts and supported language policy. | Imported by router/tools/TTS. | Yes, policy-only. | Low; no model imports. | No. | Reuse supported-language helpers and request/result contracts. |
| KEEP_AND_REUSE | `voice\router.py` | Strict voice router. Requires reference audio/text for IndicF5. | Imported by `tts\run_tts.py`, `app\routers\tts_router.py`, validation tools. | Yes, selection policy. | Low; model imports are lazy. | No. | Reuse as the policy boundary. |
| KEEP_AND_REUSE | `tools\validate_voice_router.py` | Dry-run voice routing validation. | Manual validation tool. | Policy-only unless `--execute`. | Low. | No; explicitly reports `indic_parler_used=false`. | Reuse for Phase 3C light checks. |
| KEEP_AND_REUSE | `tools\inspect_pipeline_config.py` | Config/policy inspection. | Manual validation tool. | Policy-only. | Low. | No; reports `disabled_absent_forbidden`. | Reuse and optionally extend after fresh setup. |
| KEEP_AND_REUSE | `backend\pipeline_runner.py` reference-text plumbing | Passes `--reference-text` / `--reference-text-path` into TTS env and fails clearly when IndicF5 needs transcript. | Production pipeline runner. | Yes, but no model loading. | Low; protects IndicF5 preconditions. | No. | Reuse precondition handling. Do not run full pipeline in Phase 3C plan. |
| KEEP_BUT_FIX | `tts\run_tts.py` IndicF5 route hooks | Production TTS can route unsupported Indian languages to IndicF5. | Production TTS stage. | Yes when target is IndicF5 language. | Medium; currently calls old service if executed. | No. | Keep routing/timing behavior, but change execution to fresh worker after approval. |
| KEEP_BUT_FIX | `app\routers\tts_router.py` IndicF5 route hooks | API TTS path can route to IndicF5. | API service route. | Yes when API TTS requests IndicF5 language. | Medium; currently calls old service if executed. | No. | Keep selection policy, but point execution at fresh worker/service boundary after approval. |
| DEPRECATED_QUARANTINE | `app\services\indicf5_tts_service.py` | Old direct in-process IndicF5 service that imports remote model code and downloads via `snapshot_download`. | Lazily imported by `tts\run_tts.py`, `app\routers\tts_router.py`, and `voice\engines\indicf5_engine.py` only when IndicF5 execution occurs. | Yes if IndicF5 actually runs. | Medium; lazy import protects XTTS, but execution can drag conflicting deps into non-isolated runtime. | No. | Do not build on blindly. Quarantine after approval and replace with clean worker-backed service. |
| DEPRECATED_QUARANTINE | `voice\engines\indicf5_engine.py` | Old voice engine adapter that calls old service directly. | Lazily imported by `voice\router.synthesize_voice` for execution. | Yes if execution occurs. | Medium. | No. | Replace with worker-based adapter after approval. |
| DEPRECATED_QUARANTINE | `workers\indicf5_worker.py` | Old worker that imports project router, which loops back to the old service. | Not used by production paths discovered in this audit. | No unless manually invoked. | Low currently. | No. | Quarantine/replace with fresh isolated worker. |
| DEPRECATED_QUARANTINE | `requirements-indicf5.txt` | Old requirements file. Includes unrelated `deep-translator` and `gTTS`, broad/unpinned packages, and comments from the failed attempt. | Not imported; used only if manually installed. | No current runtime effect. | High if installed into wrong env. | No Parler entries. | Quarantine/replace with a clean minimal requirements file after approval. |
| DEPRECATED_QUARANTINE | `.venv_indicf5` | Existing failed IndicF5 virtualenv. | Referenced by `.env.example` and config inspect path. | No direct runtime effect unless selected/used. | Low if untouched; high if trusted. | Unknown from full internals; not needed. | Quarantine or archive after approval. It was created with Python 3.12.13, not the preferred Python 3.11.11. |
| DEPRECATED_QUARANTINE | `ml\IndicF5` | Local prompt/audio remnants from previous attempt. | Not imported by discovered runtime code. | No. | Low. | No evidence. | Quarantine after approval. |
| DEPRECATED_QUARANTINE | `jobs\codex_hindi_indicf5_test` | Old IndicF5 job artifact folder. | Not imported. | No. | Low. | Unknown; artifact only. | Quarantine after approval. |
| DEPRECATED_QUARANTINE | `jobs\codex_hindi_indicf5_strict` | Old IndicF5 job artifact folder. | Not imported. | No. | Low. | Unknown; artifact only. | Quarantine after approval. |
| DEPRECATED_QUARANTINE | `jobs\indicf5_prompts` | Old prompt/reference artifact folder. | Not imported. | No. | Low. | Unknown; artifact only. | Quarantine after approval. |
| DEPRECATED_QUARANTINE | `jobs\indicf5_*.wav` | Old generated smoke WAVs. | Not imported. | No. | Low. | No. | Quarantine after approval. |
| KEEP_BUT_FIX | `docs\INDICF5_SETUP.md` | Existing setup doc. | Documentation only. | No. | Low. | No. | Supersede with Phase 3C fresh setup docs; update later after approval. |
| KEEP_BUT_FIX | `README.md` IndicF5 section | Older instructions still mention installing IndicF5 in "TTS runtime". | Documentation only. | No. | Low. | No. | Update later; do not rely on it for Phase 3C. |
| KEEP_AND_REUSE | `.env.example` IndicF5 variables | Documents `VIDIOLINGUA_INDICF5_PYTHON`, reference text vars, and routing policy. | Copied by users/env loading. | Yes as config reference. | Low. | No. | Reuse variable names; add fresh model/cache vars later after approval. |
| KEEP_AND_REUSE | `docs\VOICE_BACKENDS.md`, `docs\PROJECT_PIPELINE.md`, `docs\TROUBLESHOOTING.md` | Policy docs: IndicF5 reference transcript required; Indic Parler forbidden. | Documentation only. | No. | Low. | Mentions forbidden Parler only. | Keep policy; update implementation details later. |
| REMOVE_LATER_WITH_APPROVAL | `app\services\__pycache__\indicf5_tts_service*.pyc` | Bytecode from old service. | Python may ignore/recreate. | No meaningful runtime effect. | Low. | Unknown; derived artifact. | Remove only after approval or when quarantining service. |

## Parler Scan

No runtime Indic Parler imports or `parler-tts` requirements were found in the scanned project files/requirements. Current matches are policy/report strings only:

- `tools\inspect_pipeline_config.py`
- `tools\validate_voice_router.py`
- `tools\validate_full_text_to_voice.py`
- `docs\PROJECT_PIPELINE.md`
- `docs\VOICE_BACKENDS.md`
- `docs\TROUBLESHOOTING.md`
- `docs\PHASE3A_ROUTER_INTEGRATION_REPORT_2026-04-29.md`

## Old Env Finding

Existing `.venv_indicf5\pyvenv.cfg` reports:

```text
version = 3.12.13
executable = C:\Users\abize\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

This conflicts with the Phase 3C preference for Python 3.11.11. Treat this env as deprecated.

## Conclusion

Reusable now:

- Voice router policy.
- Shared voice contracts.
- Reference text precondition logic.
- Dry-run validation tools.

Do not reuse blindly:

- Existing direct IndicF5 service.
- Existing IndicF5 worker.
- Existing `.venv_indicf5`.
- Existing `requirements-indicf5.txt`.
- `ml\IndicF5` and `jobs\*indicf5*` artifacts.

Recommended next step: approve quarantine, then create a fresh worker-backed implementation path.
