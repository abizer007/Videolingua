# Job Manifest Orchestration Report - 2026-05-05

## 1. What Was Added

Added a durable per-job manifest sidecar:

```text
<job_dir>\job_manifest.json
```

New API/CLI jobs write this manifest as the pipeline runs. The manifest records
job identity, inputs, routing decisions, stage checkpoints, artifacts, errors,
and retry/resume metadata.

## 2. Manifest Schema Summary

Top-level sections:

- `job`
- `inputs`
- `routing`
- `stages`
- `artifacts`
- `recovery`
- `result`
- `warnings`
- `errors`

Tracked stages:

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

Each stage stores status, timing, attempts, retry/resume flags, errors,
warnings, input artifacts, output artifacts, and logs.

## 3. Where The Manifest Is Written

`backend/job_manifest.py` writes:

```text
jobs\<job_id>\job_manifest.json
```

for API jobs, or:

```text
outputs\<output_dir>\job_manifest.json
```

for CLI jobs using `--output-dir`.

Writes use a temp file and `os.replace()` for atomic-ish updates.

## 4. How Each Stage Updates The Manifest

`backend/pipeline_runner.py` now updates the manifest at existing safe
boundaries:

- job start creates the manifest and completes `receive_upload`
- pre-ASR reference/audio prep updates `prepare_audio`
- ASR subprocess updates `asr`
- translation subprocess updates `translation`
- TTS subprocess updates `voice_generation`
- TTS WAV checks update `audio_validation`
- lipsync/mux updates `lipsync_mux`
- final MP4 inspection updates `output_validation`
- automatic report generation updates `metrics_evaluation`
- final result payload updates `complete`

The stage logic itself was not changed.

## 5. Artifact Map

The manifest registers important artifacts when they exist:

- source video
- extracted/BGM audio
- ASR JSON
- translation JSON
- TTS WAV
- cleaned/normalized TTS WAV
- reference audio
- reference metadata
- final MP4
- metrics report
- pipeline result
- stage logs

API summaries expose artifact names and existence/size metadata instead of
requiring the frontend to parse full manifest internals.

## 6. Error Capture

When a stage fails, the manifest records:

- failed stage name
- stage-level error message
- `result.final_status=failed`
- `result.user_facing_error`
- recovery hints

Manifest write failures are logged with `[JobManifest] WARNING` and do not mask
the real pipeline error.

## 7. Retry/Resume Metadata

This phase records metadata only:

- `last_completed_stage`
- `failed_stage`
- `retry_count_total`
- `max_retries`
- `resume_supported=false`
- `resume_command_hint`
- `retry_failed_stage_hint`
- per-stage `can_retry`
- per-stage `can_resume_from_here`

No resume engine or retry executor was implemented.

## 8. What Is Not Implemented Yet

Not implemented in this phase:

- SQLite/Postgres persistent job database
- Redis/Celery queue
- true resume execution
- retry-only-failed-stage execution
- cleanup/retention policy
- admin job dashboard
- routing/model changes
- dependency changes
- local IndicF5 execution

## 9. Frontend Display Changes

`NEW_Frontend` now consumes optional `manifestSummary` data:

- pipeline page shows `Run manifest`
- pipeline page shows `Stage evidence`
- timeline uses manifest stage statuses when available
- results page shows `Run manifest`
- results page shows `Artifacts written`
- old jobs without manifests fall back to existing status/result data

## 10. Validation Results

Backend:

```text
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation
passed

.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
passed; Sarvam enabled with masked key, IndicF5 false/local_disabled, XTTS model ready

.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\manifest_router_kn.wav --dry-run
passed; selected_engine=sarvam, no IndicF5, no generic fallback

.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\manifest_router_fr.wav --dry-run
passed; selected_engine=xtts, no Sarvam, no IndicF5, no generic fallback
```

Manifest validation:

```text
.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir outputs\validation\manifest_smoke --print-summary
passed; generated manifest is valid

.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir outputs\kannada_sarvam_practical_test_clipfix --print-summary
reported manifest not present for historical job; no retrofit used

.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir outputs\french_official_test --print-summary
reported manifest not present for historical job; no retrofit used
```

Frontend:

```text
corepack pnpm run lint
passed after scoped Corepack cache escalation

corepack pnpm run build
passed; existing baseline-browser-mapping age warning remains
```

## 11. Compatibility With `pipeline_result.json`

`pipeline_result.json` remains the legacy result contract. New runs also include:

- `manifestPath`
- `manifestSummary`

Existing historical `pipeline_result.json` files were not modified.

## 12. Safety Confirmation

- Working French XTTS path preserved.
- Working Kannada IndicTrans2 + Sarvam path preserved.
- No Python virtual environment was mutated.
- No dependency was installed.
- No full heavy video pipeline was run.
- No local IndicF5 load or generation was run.
- `models\xtts_v2` was untouched.
- Protected output folders were not modified.
- No Sarvam key was exposed.
- No secrets were placed in frontend.
- No generic fallback was added.
- Indic Parler was not used.

## 13. Multilingual Export Relationship

The multilingual audio export phase builds on the same evidence-first design but
does not change `job_manifest.json` execution semantics.

New export manifests are separate files:

```text
outputs\multilingual_exports\<export_id>\metadata\multilingual_manifest.json
```

They package existing outputs into HLS and optional multi-audio MP4 artifacts.
They do not replace per-job manifests, do not enable resume execution, and do
not alter single-language pipeline behavior.

Proof export:

```text
outputs\multilingual_exports\official_fr_kn_test
```

Included language evidence:

- French: translation `google`, voice `xtts`, mode `speaker-reference voice`.
- Kannada: translation `indictrans2`, voice `sarvam`, mode
  `managed-indian-tts`.

## Future Roadmap

1. Persistent job database:
   - SQLite first
   - Postgres later

2. Redis/Celery queue:
   - async long-running jobs
   - GPU worker queues
   - retry policies

3. Resume execution:
   - resume from last completed stage
   - retry failed stage only
   - artifact dependency validation

4. Cleanup policy:
   - keep final MP4
   - keep logs/manifest/metrics
   - expire intermediates after N days

5. Admin job dashboard:
   - jobs
   - failures
   - retries
   - storage usage
   - backend usage
## 2026-05-06 Responsible AI Artifact Registration

The pipeline now registers responsible AI artifacts in `job_manifest.json` when the compliance package writes them:

- consent record
- SGI risk report
- abuse risk report
- synthetic disclosure report
- provenance manifest
- fingerprint report
- audit ledger
- retention policy
- compliance passport JSON/Markdown

Registration is additive and does not alter resumability semantics or existing route decisions.
