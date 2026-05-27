# Deep Technical Architecture Research - 2026-05-06

Workspace: `D:\Vidiolingua`

This document records the repo-backed research used to extend the existing
`NEW_Frontend\app\architecture\page.tsx` page. It is intentionally evidence
oriented: verified means observed in source, docs, command logs, or safe
read-only runtime probes; inferred means derived from verified code paths but
not validated by running the full media pipeline in this pass.

## 1. Verified Package / Module Layout

Verified from `rg --files`, source reads, and README/docs:

| Package / folder | Verified role | Key files inspected |
| --- | --- | --- |
| `NEW_Frontend` | Active Next.js frontend. Uploads media, polls status/results, displays architecture/backends/evidence pages. | `app\architecture\page.tsx`, `app\differentiators\page.tsx`, `lib\api.ts`, navigation/footer components |
| `backend` | FastAPI app, in-memory job store, pipeline orchestration, durable manifest helper. | `main.py`, `pipeline_runner.py`, `job_store.py`, `job_manifest.py` |
| `asr` | ASR stage. Extracts 16 kHz mono WAV, prefers WhisperX, can use PyAnnote diarization, falls back to faster-whisper unless WhisperX is required. | `run_asr.py`, `speaker_analysis.py` |
| `translation` | Translation contracts, strict router, engines, cache, QA/integrity validation, stage runner. | `run_translate.py`, `router.py`, `base.py`, `engines\indictrans2_engine.py`, `validation\*`, `cache\*` |
| `tts` | Timing-aware TTS stage runner. Converts translated segment JSON into timestamp-aligned WAV. | `run_tts.py` |
| `voice` | Voice policy, backend adapters, audio validation, phonetic/prosody layers. | `router.py`, `base.py`, `engines\xtts_engine.py`, `engines\sarvam_engine.py`, `engines\indicf5_engine.py`, `audio_validation.py`, `phonetic_resolution.py`, `prosody_analysis.py`, `prosody_transfer.py`, `hubert_prosody.py` |
| `workers` | Isolated subprocess worker entry points for heavy or fragile runtimes. | `indictrans2_worker.py`, `xtts_worker.py`, `indicf5_worker.py`, `hubert_prosody_worker.py` |
| `prosody` | HuBERT adapter training/inference and prosody validation helpers. | `adapter_train.py`, `adapter_infer.py`, `adapter_model.py`, `adapter_evaluation.py` |
| `speaker_analysis` | Diarization, speaker-to-ASR mapping, reference candidates, Sarvam voice plans, reports. | `report.py`, `diarization.py`, `speaker_mapping.py`, `speaker_profiles.py`, `sarvam_voice_selection.py` |
| `evaluation` | Metrics report builder over existing job artifacts; reports missing evaluators honestly. | `report_builder.py`, `metrics.py`, `audio_metrics.py`, `media_metrics.py` |
| `compliance` | Responsible AI/provenance sidecars and Synthetic Media Compliance Passport. | `compliance_passport.py`, `provenance_manifest.py`, `fingerprinting.py`, `audit_ledger.py` |
| `tools` | Safe validation, inspection, export, and utility CLIs. | `create_multilingual_export.py`, `validate_*`, `inspect_pipeline_config.py` |

## 2. Verified Runtime / Venv List And Purpose

Safe metadata probes found these runtime directories: `.venv`, `.venv311`,
`.uv_python`, `.venv_asr`, `.venv_tts`, `.venv_bgm`, `.venv_api`,
`.venv_indictrans2`, `.venv_indicf5`, `.venv_prosody`.

The frontend section focuses on the active architecture-critical runtimes:

| Runtime | Verified purpose | Verified key packages / state |
| --- | --- | --- |
| `.venv_api` | Lightweight FastAPI/orchestration runtime. It should avoid eager heavy model imports. | Python 3.11.11, FastAPI 0.136.1, Uvicorn 0.46.0, requests 2.33.1, no torch/TTS/transformers/numpy detected. |
| `.venv_tts` | Known-good XTTS/Coqui voice runtime. Protected to preserve French XTTS path. | Python 3.11.11, TTS 0.22.0, torch 2.5.1+cpu, torchaudio 2.5.1+cpu, transformers 4.46.3, numpy 1.26.4, CUDA unavailable. |
| `.venv_indictrans2` | CUDA IndicTrans2 translation worker runtime. | Python 3.11.11, torch 2.5.1+cu121, torchaudio 2.5.1+cu121, torchvision 0.20.1+cu121, transformers 4.51.3, IndicTransToolkit/indictranstoolkit 1.1.1, numpy 2.2.6, CUDA true on RTX 4050. |
| `.venv_indicf5` | Quarantined/local experimental IndicF5 runtime. It exists but current production routing keeps IndicF5 disabled/local_disabled. | Python 3.11.11, torch 2.5.1+cu121, torchvision 0.20.1+cu121, torchaudio 2.5.1+cu121, transformers 4.57.6, f5-tts 1.1.20, numpy 2.4.3, CUDA true. |
| `.venv_prosody` | HuBERT/prosody feature extraction and adapter runtime. | Python 3.11.11, torch metadata 2.11.0 and import reports 2.11.0+cpu, transformers 5.8.0, numpy 2.4.4, soundfile 0.13.1, CUDA unavailable. |
| `.venv_asr` | ASR/diarization runtime used by pipeline ASR stage. Included as supporting architecture evidence even though not requested for frontend cards. | Python 3.11.11, whisperx 3.8.5, faster-whisper 1.2.1, torch 2.8.0+cpu, pyannote.audio 4.0.4, transformers 4.57.6. |
| `.uv_python` | Workspace-local CPython used by setup scripts to create 3.11 venvs. | `D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe`, Python 3.11.11. |

## 3. Verified Worker Scripts

| Worker | Caller | Verified behavior |
| --- | --- | --- |
| `workers\indictrans2_worker.py` | `translation\engines\indictrans2_engine.py` via `.venv_indictrans2` Python. | Reads request JSON, loads local/HF IndicTrans2 model, maps language codes to FLORES/script codes, uses CUDA fp16 when available, writes response JSON, clears CUDA cache before exit. |
| `workers\xtts_worker.py` | Worker entry point exists; direct production TTS path currently uses `tts\run_tts.py` -> voice router -> XTTS service. | Reads request JSON, calls `voice.router.synthesize_voice` with `preferred_engine=xtts`, writes metadata/response JSON. |
| `workers\indicf5_worker.py` | `voice\engines\indicf5_engine.py` when IndicF5 is explicitly enabled. | Validates request/reference text/model files, supports diagnose/load-only/no-generate flags, configures workspace-local caches, reports errors as JSON. It can load local IndicF5 only when routing policy enables it. |
| `workers\hubert_prosody_worker.py` | `voice\hubert_prosody.py` via `.venv_prosody` Python. | Extracts 16 kHz WAV with ffmpeg, loads `facebook/hubert-base-ls960`, writes global and segment embeddings plus `hubert_features.json`. |

## 4. Verified Command Flow

### Frontend To Backend

Verified in `NEW_Frontend\lib\api.ts`:

1. `uploadVideo()` posts `FormData` to `POST /api/upload`.
2. It sends `video`, `languages`, `voiceOptions`, optional `voiceSample`,
   optional evaluation references, and `responsibleAIConsent`.
3. `getJobStatus()` polls `GET /api/job-status/{jobId}`.
4. `getResult()` reads `GET /api/result/{jobId}`.
5. `createMultilingualExport()` calls `POST /api/multilingual-export`.

### FastAPI To Pipeline

Verified in `backend\main.py`:

1. `/api/upload` validates video upload and target language codes.
2. XTTS target languages require a `voiceSample` or `autoReference=true`.
3. Job state is created through `backend.job_store.create_job`.
4. `run_pipeline_background()` is imported from `backend.pipeline_runner` and
   launched for the job.

### Pipeline Runner To Stages

Verified in `backend\pipeline_runner.py`:

1. `job_manifest.create_manifest()` creates `<job_dir>\job_manifest.json`.
2. `_run_stage()` executes subprocess stages with `capture_output=True`,
   UTF-8 decoding, and optional stage log files.
3. ASR runs `asr\run_asr.py` using the configured ASR Python.
4. Translation runs `translation\run_translate.py`.
5. TTS runs `tts\run_tts.py` using `.venv_tts`.
6. Lip-sync/mux runs `lipsync\run_lipsync.py`.
7. Metrics are built through `evaluation.report_builder`.
8. Compliance bundles are generated at upload/routing, translation, final, and
   failure points when enabled.

### IndicTrans2 Worker Call

Verified in `translation\engines\indictrans2_engine.py`:

```text
translation/run_translate.py
-> translation.router.translate()
-> IndicTrans2Engine.translate()
-> .venv_indictrans2\Scripts\python.exe -m workers.indictrans2_worker
-> request.json / response.json
```

The engine uses a workspace temp root under
`outputs\validation\indictrans2_worker_tmp` and workspace-local Hugging Face
caches under `.hf_cache`.

## 5. Verified Dependency Isolation Reasons

| Reason | Evidence |
| --- | --- |
| API runtime should stay lightweight. | `.venv_api` metadata has FastAPI/Uvicorn/requests and no torch/TTS/transformers/numpy. `pipeline_runner.py` uses subprocess stage calls instead of loading all models into FastAPI. |
| XTTS dependency versions are fragile and protected. | `COMMAND_LOG.md`, `docs\VALIDATE_WORKING_XTTS_PIPELINE.md`, and `docs\PHASE3B_INDICTRANS2_INSTALL_REPORT_2026-04-29.md` record `.venv_tts` torch 2.5.1+cpu, TTS 0.22.0, transformers 4.46.3, and repeated checks to preserve BeamSearchScorer/import compatibility. |
| IndicTrans2 needs a separate CUDA/model runtime. | `requirements-indictrans2.txt`, `scripts\setup_indictrans2_env.ps1`, `docs\INDICTRANS2_SETUP.md`, and Phase 3B report state `.venv_indictrans2` must stay outside `.venv_tts`, uses CUDA/fp16/batch size 1, and releases memory by worker process exit. |
| IndicF5 must be quarantined. | `docs\PHASE3C_INDICF5_INSTALL_REPORT_2026-04-29.md`, `docs\PHASE3C_INDICF5_COMPAT_FIX_REPORT_2026-04-29.md`, `docs\VOICE_BACKENDS.md`, `.env.example`, and `voice\router.py` all record disabled/local_disabled status and prior load/API mismatch/timeouts. |
| HuBERT/prosody should not disturb XTTS/IndicTrans2. | `voice\hubert_prosody.py` explicitly searches `.venv_prosody` and returns `status=unavailable` when absent. `docs\PROSODY_ELOCUTION_ENGINE_REPORT_2026-05-05.md` records isolated HuBERT feature extraction. |

## 6. Known Historical Failures / Conflicts

Verified from docs and command log:

- Python PATH pointed to Python 3.13.1 during IndicTrans2 setup, while the
  project needed Python 3.11; `.uv_python\cpython-3.11.11...` was used.
- IndicTrans2 model access initially failed with a gated Hugging Face 401 until
  access/authentication were completed.
- IndicTrans2 initially hit Windows cache/temp path problems; the engine now
  uses workspace-local temp and HF module caches.
- XTTS protection checks repeatedly validated `.venv_tts` and `models\xtts_v2`
  after other runtime work.
- IndicF5 local generation was blocked by `load_model()` API mismatch, later a
  `torch.device` compatibility issue, and prior timeout/memory risk. Current
  production path keeps it disabled/local experimental.
- Speaker diarization had a PyAnnote token argument mismatch; code now inspects
  constructor signatures and avoids logging token values.
- Corepack cache permission issues have appeared in previous frontend lint/build
  attempts; if they recur, report the exact error instead of reinstalling.

## 7. Current Model / Runtime Versions Found

Verified runtime package versions are recorded fully in
`docs\RUNTIME_ENVIRONMENT_MATRIX_2026-05-06.md`.

Verified model/runtime identifiers from code/docs:

- XTTS model ID: `tts_models/multilingual/multi-dataset/xtts_v2`.
- Protected local XTTS model directory: `models\xtts_v2`.
- IndicTrans2 default model: `ai4bharat/indictrans2-en-indic-dist-200M`.
- IndicF5 default model: `ai4bharat/IndicF5`, disabled/local experimental.
- HuBERT feature model: `facebook/hubert-base-ls960`.
- Sarvam TTS endpoint: `https://api.sarvam.ai/text-to-speech`.
- Sarvam configured defaults in source/examples: model `bulbul:v3`, speaker
  `shubh`, sample rate `24000`, output codec `wav`, timeout `120`.

## 8. Verified vs Inferred Boundaries

Verified:

- The source files and docs listed above exist and contain the policies and call
  paths summarized here.
- The active local env files are `backend\.env` and `NEW_Frontend\.env.local`;
  `.env` is absent in this workspace.
- `backend\.env` contains a `SARVAM_API_KEY` key, but its value was not read or
  printed. `NEW_Frontend\.env.local` contains `NEXT_PUBLIC_API_URL` and no
  `NEXT_PUBLIC_*SARVAM*` key.
- Protected output/model folders were not modified during this research pass.

Inferred:

- The subprocess split is a deliberate memory-release strategy because worker
  processes exit after model use; this is directly true for subprocess workers
  but not benchmarked in this pass.
- The frontend can display Mermaid-equivalent diagrams without adding Mermaid by
  using styled React data/cards; Mermaid source files are still stored in docs.

Needs verification:

- Current full end-to-end behavior for a new upload was not re-run by design.
- Current frontend browser rendering was not checked until after the page edit.
- Historical outputs may not contain `job_manifest.json` unless generated after
  the manifest phase or explicitly retrofitted; current docs say historical
  absence is expected.

## 9. Frontend Architecture-Page Integration Plan

Update only `NEW_Frontend\app\architecture\page.tsx`.

Plan:

1. Preserve all existing imports, top hero, interactive diagram, architecture
   flow, OTT export section, lane cards, CTA, animated code, and footer.
2. Add a new section below the current architecture content and before
   `AnimatedPipelineCodeSection`.
3. Use local React data arrays and lucide icons; do not add dependencies.
4. Include runtime cards, package/component/deployment visual maps, worker-call
   sequence, artifact flow, engineering decision table, and enablement summary.
5. Label uncertainty carefully using `Verified`, `Inferred`, and
   `Needs verification`.
6. Keep secrets out of the frontend. Mention only key presence/policy, not
   values.
7. Link to Mermaid sources as repository path labels rather than trying to
   render raw Mermaid in the UI.

