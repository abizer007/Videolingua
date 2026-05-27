# Job Manifest Orchestration Plan - 2026-05-05

## 1. Current Job And Status Implementation

VideoLingua currently tracks live API jobs in `backend/job_store.py` with an
in-memory dictionary keyed by `jobId`. The store exposes:

- `stage`, `progress`, `currentLanguage`, `languages`, `sourceLanguage`, and
  `error`.
- `metrics`, `analysis`, and `metricsReport`.
- `stageHistory` with start/completion times and durations.
- `result` once the pipeline reaches a terminal state.

`backend/main.py` provides:

- `POST /api/upload`
- `GET /api/job-status/{job_id}`
- `GET /api/result/{job_id}`
- `GET /api/result/{job_id}/file/{filename}`

`backend/pipeline_runner.py` creates per-job directories, updates `job_store`
around ASR, translation, TTS, lipsync, completion, and error handling, then
writes `pipeline_result.json`.

Known current limitation: job status is lost on backend restart because the job
store is memory-only.

## 2. Current `pipeline_result.json` Structure

Historical known-good outputs currently use a compact result payload:

```json
{
  "jobId": "french_official_test",
  "originalVideo": "http://localhost:8000/api/result/french_official_test/file/input_video.mp4",
  "localizedVideos": [
    {
      "language": "French",
      "url": "http://localhost:8000/api/result/french_official_test/file/Vidiolingua_Test_Official_dubbed_fr.mp4",
      "confidence": 0.88
    }
  ],
  "metrics": {
    "totalTime": 305,
    "languagesProcessed": 1,
    "bgmPreserved": false,
    "speakersDetected": 0
  }
}
```

Newer pipeline runs add richer `metrics`, `analysis`, and `metricsReport`
payloads while preserving the same top-level result contract:

- `jobId`
- `originalVideo`
- `localizedVideos`
- `metrics`
- `analysis`
- `metricsReport`
- optional `error`

The manifest must not replace or mutate `pipeline_result.json`; it will be a
separate durable sidecar referenced from result/status payloads.

## 3. Proposed `job_manifest.json` Schema

The file will live at:

```text
<job_dir>\job_manifest.json
```

Top-level sections:

```text
schema_version
job
inputs
routing
stages
artifacts
recovery
result
warnings
errors
```

`job`:

- `job_id`
- `created_at`
- `updated_at`
- `pipeline_version`
- `run_source`
- `requested_by`

`inputs`:

- `input_video_path`
- `input_video_hash`
- `reference_audio_path`
- `auto_reference_enabled`
- `extracted_reference_path`
- `target_language`
- `source_language`
- `mode`
- `output_dir`

`routing`:

- `selected_translation_backend`
- `selected_voice_backend`
- `xtts_supported`
- `sarvam_supported`
- `indicf5_enabled`
- `generic_fallback_allowed`
- `fallback_used`
- `fallback_reason`

`stages` includes:

- `receive_upload`
- `prepare_audio`
- `asr`
- `translation`
- `voice_generation`
- `audio_validation`
- `lipsync_mux`
- `output_validation`
- `metrics_evaluation`
- `complete`

Each stage tracks:

- `status`
- `started_at`
- `ended_at`
- `elapsed_sec`
- `attempt_count`
- `can_retry`
- `can_resume_from_here`
- `error_message`
- `warning_messages`
- `input_artifacts`
- `output_artifacts`
- `logs`

`artifacts` maps stable artifact keys to metadata:

- `source_video`
- `extracted_audio`
- `asr_json`
- `translation_json`
- `tts_wav`
- `normalized_tts_wav`
- `reference_audio`
- `reference_metadata`
- `final_mp4`
- `ffprobe_report`
- `metrics_report`
- `pipeline_result`
- `stage_logs`

`recovery`:

- `last_completed_stage`
- `failed_stage`
- `retry_count_total`
- `max_retries`
- `resume_supported`
- `resume_command_hint`
- `retry_failed_stage_hint`

`result`:

- `final_status`
- `final_mp4_path`
- `duration_sec`
- `file_size_bytes`
- `validation_passed`
- `user_facing_error`

## 4. Files To Modify

Runtime:

- `backend/job_manifest.py`
- `backend/pipeline_runner.py`
- `backend/job_store.py`
- `backend/main.py`
- `tools/validate_job_manifest.py`

Frontend:

- `NEW_Frontend/lib/types.ts`
- `NEW_Frontend/components/vidiolingua/pipeline-timeline.tsx`
- `NEW_Frontend/app/pipeline/page.tsx`
- `NEW_Frontend/app/results/page.tsx`

Docs:

- `docs/JOB_MANIFEST_ORCHESTRATION_REPORT_2026-05-05.md`
- `docs/PROJECT_PIPELINE.md`
- `docs/FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md`
- `docs/AUTOMATIC_BACKEND_EVALUATION_PROCESS_2026-05-05.md`
- `COMMAND_LOG.md`

## 5. How Current Behavior Is Preserved

- Manifest writes are side effects only. They do not feed into routing,
  subprocess command construction, or media generation.
- Manifest write failures are logged but should not mask the pipeline's real
  stage error.
- `pipeline_result.json` remains intact and remains the primary legacy result
  contract.
- No model paths, virtual environments, protected outputs, or secrets are
  mutated.
- No new dependency is introduced; helpers use Python stdlib only.
- No local IndicF5 load is introduced.
- No generic fallback is added.

## 6. How Manifest Updates Happen Per Stage

At job start:

- create manifest
- register input video and optional uploaded reference audio
- mark `receive_upload` complete
- record initial routing policy booleans

Around each stage:

- call `start_stage(stage)`
- register input artifacts just before stage execution
- call `complete_stage(stage)` and register outputs after success
- call `fail_stage(stage, error)` if an exception is raised

Stage mapping from current runner boundaries:

- `receive_upload`: job directory/input setup and original video copy
- `prepare_audio`: optional UVR5/BGM extraction and pre-ASR reference prep
- `asr`: WhisperX/ASR subprocess and speaker/reference analysis
- `translation`: translation subprocess and translation evidence
- `voice_generation`: TTS subprocess and generated WAV discovery
- `audio_validation`: TTS WAV duration/audio checks currently performed after TTS
- `lipsync_mux`: lipsync/mux subprocess and result MP4 copy
- `output_validation`: final MP4 ffprobe/stream checks from existing metrics
- `metrics_evaluation`: `evaluation/metrics_report.json` creation
- `complete`: terminal result payload creation

## 7. Retry And Resume Metadata Representation

This phase records retry/resume readiness only. It does not execute a resume.

When a stage completes:

- `recovery.last_completed_stage` is set to that stage.
- completed stages get `can_resume_from_here=true` if their artifacts are useful
  resume checkpoints.

When a stage fails:

- `recovery.failed_stage` is set.
- the stage stores `error_message`.
- `result.final_status` becomes `failed`.
- `resume_command_hint` says resume execution is planned and artifacts can be
  inspected through the manifest.
- `retry_failed_stage_hint` names the failed stage but does not claim retry is
  executable yet.

`resume_supported` remains `false` until a real resume engine exists.

## 8. What Will Not Be Implemented Yet

- Persistent SQLite/Postgres job database.
- Redis/Celery worker queue.
- Actual resume execution from the last checkpoint.
- Actual retry-only-failed-stage execution.
- Cleanup/retention policy.
- Admin dashboard.
- Any model routing change.
- Any dependency installation.
- Any frontend redesign.

## 9. Validation Plan

Light validation only:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\manifest_router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\manifest_router_fr.wav --dry-run
```

Frontend:

```powershell
cd D:\Vidiolingua\NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

Manifest tool:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir <new_or_test_job> --print-summary
.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir outputs\french_official_test --print-summary
.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir outputs\kannada_sarvam_practical_test_clipfix --print-summary
```

For protected historical outputs, missing manifests should be reported as
historical absence unless `--retrofit` is explicitly used. This phase will not
run retrofit on protected outputs.

## 10. Risks And Rollback Notes

Risk: manifest write failures could obscure the real stage error.

Mitigation: helper calls are wrapped so write failures print a warning and never
replace the original exception.

Risk: frontend assumes manifest exists.

Mitigation: frontend types keep manifest optional and fall back to current
status/result fields.

Risk: adding manifest fields to API responses leaks local paths.

Mitigation: API exposes concise summaries only. Full local artifact paths remain
inside backend/job-local manifest data; frontend display uses labels and
relative names where practical.

Rollback:

- Remove `backend/job_manifest.py`.
- Remove manifest calls from `backend/pipeline_runner.py`.
- Remove manifest summary calls/fields from `backend/job_store.py` and
  `backend/main.py`.
- Remove frontend manifest panels.
- Existing `pipeline_result.json` and generated MP4/WAV artifacts remain valid.
