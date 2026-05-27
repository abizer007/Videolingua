# Frontend Backend Integration Readiness - 2026-04-29

## Current Backend Endpoints

Health:

```text
GET /
GET /api/health
GET /api/health/deps
GET /tts-health
GET /api/tts-health
```

Pipeline:

```text
POST /api/upload
GET /api/job-status/{job_id}
GET /api/result/{job_id}
GET /api/result/{job_id}/file/{filename}
```

## Upload Request Format

`POST /api/upload` expects multipart form data:

```text
video: file, required
languages: JSON string array, required by frontend
voiceOptions: JSON object string
sourceLanguage: string, optional
voiceSample: audio file, optional
```

Current frontend service:

```text
frontend-next\src\services\api.ts
```

uses `NEXT_PUBLIC_API_URL` or `http://localhost:8000`.

## Job Lifecycle

1. Frontend uploads form data to `/api/upload`.
2. Backend returns `{ "jobId": "..." }`.
3. Frontend polls `/api/job-status/{jobId}`.
4. On `stage=complete`, frontend fetches `/api/result/{jobId}`.
5. Result video URLs point to `/api/result/{jobId}/file/{filename}`.
6. Frontend can preview/download MP4 URLs directly.

Lifecycle hardening added on 2026-05-06:

- Job storage uses versioned keys under `vidiolingua:v1:*`.
- Each upload creates a fresh `runSessionId`.
- Terminal states are explicit: `complete`, `failed`, `cancelled`, `timeout`, and `error`.
- Polling stops on terminal state, aborts in-flight fetches on unmount, and fetches result metadata once.
- Job status/result/file responses are returned with no-store headers.
- Failed or timed-out pages provide `Start fresh run` and `Clear old job state` actions.

Status response fields:

```text
jobId
status
terminal
stage
progress
currentLanguage
languages
sourceLanguage
sourceLanguageConfidence
error
errorSummary
metrics
createdAt
updatedAt
terminalAt
completedAt
failedAt
resultAvailable
```

Result response fields:

```text
jobId
originalVideo
localizedVideos[{ language, url, confidence }]
metrics
error?
```

## Current Frontend State

- `frontend-next` already has upload, pipeline polling, and results pages.
- `Providers` auto-switches to real API when `/api/health` is reachable.
- The API client starts in mock mode until the provider changes it.
- Results page previews and downloads real backend URLs.
- `NEW_Frontend` now contains the v0-based VideoLingua revamp with `/`,
  `/upload`, `/pipeline`, `/results`, `/architecture`, and `/backends`.
- `NEW_Frontend` uses a fetch-based API client in `NEW_Frontend\lib\api.ts`.
- `NEW_Frontend` has no `node_modules`; frontend lint/build still require
  `pnpm install` before validation.

## Readiness Gaps Before Frontend Work

1. Backend `/api/upload` previously allowed only:

```text
hi, es, fr, de, ja, zh, ar, pt
```

It has now been expanded to include the XTTS language set and Sarvam regional
languages including `kn`, `or`, and `od`.

2. `frontend-next` still has the old language list. `NEW_Frontend` has the
updated XTTS/Sarvam language selector.

3. `NEW_Frontend` sends `cloned=true` for XTTS speaker-reference routes and
does not present Sarvam as exact speaker cloning.

4. `POST /api/upload` does not accept `referenceText`. Sarvam does not need it,
but explicit IndicF5 experiments would. Since IndicF5 is disabled, this is not
blocking frontend work.

5. There is no dedicated backend endpoint for supported language/backend
metadata. Frontend can hardcode initially, but a future endpoint would reduce
drift.

## 2026-05-05 Automatic Evaluation Update

- Backend jobs now write automatic `evaluation\metrics_report.json` through
  `evaluation.worker.run_evaluation`.
- `GET /api/job-status/{job_id}` and `GET /api/result/{job_id}` can include
  `metricsReport`.
- Normal upload flow does not require ground-truth transcript, reference
  translation, human MOS, or quality notes.
- Those expert reference fields remain in a collapsed `Expert reference metrics`
  section.
- Results and pipeline pages show Testing / Analysis cards for overall, ASR,
  translation, voice naturalness, sync, speaker similarity, and output
  validation.
- Each card shows method, confidence, explanation, and whether the metric is
  reference-backed, auto-reference, proxy, artifact, or not applicable.

## 2026-05-06 Visual Lip-sync Evidence Update

Backend status/result payloads may now include lipsync evidence in:

```text
metrics
analysis.lipsync
metricsReport.lipsync
```

The frontend uses these fields to distinguish Wav2Lip visual sync from ffmpeg
audio mux. When ffmpeg mux is used, the UI says audio replacement only and does
not imply mouth animation was applied.

`NEW_Frontend` additions:

- pipeline page: `Lip-sync evidence`
- results page: `Lip-sync evidence`
- mode/method/preflight/checkpoint/Python runtime fields
- alignment level and duration integrity fields
- no fake LSE metric display

The existing ffmpeg mux workflow remains supported. Wav2Lip required mode is
allowed to fail clearly instead of silently returning an ffmpeg-only result.

## 2026-05-05 Job Manifest Update

New backend jobs now write `job_manifest.json` in the job/output folder. Status
and result responses may include:

```text
manifestSummary
manifestPath
```

The summary exposes current stage, last completed checkpoint, failed stage,
stage statuses, selected backends, artifact names/existence metadata, and
recovery hints. The frontend treats the fields as optional so historical jobs
without manifests still render from existing status/result data.

`NEW_Frontend` additions:

- pipeline page: `Run manifest`
- pipeline page: `Stage evidence`
- timeline: manifest stage states when available
- results page: `Run manifest`
- results page: `Artifacts written`

Retry/resume is metadata-only in this phase. `resume_supported` remains false
until a real resume executor is implemented.

## 2026-05-05 Multilingual Audio Export Update

Backend:

```text
POST /api/multilingual-export
GET /api/multilingual-export/{export_id}
GET /api/multilingual-export/{export_id}/file/{path}
```

The endpoint wraps `tools.create_multilingual_export` and only packages existing
artifacts. It restricts source media and audio track paths to project/output/job
folders, blocks path traversal, and exposes no delete/mutation endpoint.

Frontend:

- Navigation now includes `OTT Export`.
- New page: `NEW_Frontend\app\multilingual-export\page.tsx`.
- Homepage and architecture page show OTT-style multilingual delivery as a
  visible differentiator.
- Results page detects `official_fr_kn_test` when present and shows HLS, MP4,
  manifest links, and backend evidence per track.

Proof export:

```text
outputs\multilingual_exports\official_fr_kn_test
```

The proof export packages existing French XTTS and Kannada IndicTrans2 + Sarvam
WAVs only. No pipeline generation stage is rerun.

## 2026-05-05 Translation QA Context Layer Update

Backend status/result payloads may now include:

```text
translationQA
```

The compact summary reports status, check counts, warning/error counts, empty
segments, script match, number/entity issues, expansion warnings, glossary use,
translation-memory hits, post-edit use, and QA report artifact name.

`NEW_Frontend` additions:

- pipeline page: `Translation integrity`
- pipeline timeline: QA details during the translation stage
- results page: `Translation integrity`
- architecture/backends/home sections: translation QA guardrails

This frontend wording is intentionally conservative: VideoLingua performs
translation integrity checks around the current translation system. It does not
claim trained context-aware translation or silent LLM replacement.

## Recommended Target Language Dropdown

XTTS cloned/global:

```text
en, fr, es, de, ja, zh, ar, pt, it, ko, nl, pl, ru, tr, cs, hu
```

Sarvam managed Indian TTS:

```text
hi, ta, bn, te, kn, ml, mr, gu, pa, or
```

Suggested display labels:

- XTTS: `XTTS voice cloning`
- Sarvam: `Sarvam managed Indian-language TTS`
- IndicF5: `disabled / local experimental`

## User-Facing Voice Warnings

- Sarvam is managed TTS, not exact voice cloning.
- IndicF5 local execution is disabled.
- Generic fallback is not allowed for strict/practical cloned runs.

## Frontend Env

Required:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Readiness Verdict

Backend is ready for frontend connection testing with the new `NEW_Frontend`
language picker after dependency installation and frontend build validation.
Kannada is no longer blocked by the upload allowlist.

## Polish And Integration Follow-Up - 2026-04-30

The `NEW_Frontend` upload/status/results handoff was tightened after the polish
pass.

Confirmed:

- `POST /api/upload` form fields still match the backend route:
  - `video`
  - `languages`
  - `voiceOptions`
  - `sourceLanguage`
  - `voiceSample`
- A mocked upload/status/result contract test passed without running the heavy
  video pipeline.
- Kannada frontend-style voice options with `cloned=false` still route to
  Sarvam in router dry-run.
- French with `cloned=true` still routes to XTTS in router dry-run.

Frontend fixes:

- `/results?jobId=...` now uses the query job id instead of relying only on
  browser localStorage.
- `/pipeline` now stops polling at terminal states and fetches backend error
  result payloads as well as completed result payloads.
- API errors now parse FastAPI `detail` bodies into readable UI messages.
- Upload validation now catches missing or empty source video before submitting.

Current validation:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
backend compileall: passed
tools.inspect_pipeline_config: passed
kn dry-run with cloned=false: selected_engine=sarvam
kn dry-run with cloned=true: selected_engine=sarvam
fr dry-run with cloned=true: selected_engine=xtts
```

Browser screenshot QA note:

The in-app browser plugin could not initialize because the local Node runtime is
`22.15.0` and the plugin requires `>=22.22.0`. The Next dev server did start at
`http://127.0.0.1:3000`, and HTTP checks returned `200` for `/`, `/architecture`,
`/upload`, and `/results`.

## Final Hero/Webflow Follow-Up - 2026-04-30

A real browser-driven `NEW_Frontend` upload-to-result check was completed after
the final hero refinement.

Confirmed UI flow:

```text
upload -> pipeline page -> status polling -> results page -> downloadable MP4
```

Successful retry job:

```text
63cf909f-7f34-48b7-afe8-44f9f1fc09fe
```

Route tested:

```text
source=en
target=kn
voice backend=Sarvam managed Indian-language TTS
```

The first submitted Kannada UI run exposed a backend integration bug:
`backend\pipeline_runner.py` enforced the disabled experimental Indic
reference-transcript guard even when `VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam`.
The frontend upload payload was correct.

Fix:

- `_requires_indicf5_reference_text()` now only requires an exact reference
  transcript when the configured Indic voice backend is explicitly `indicf5`.
- automatic voice-sample extraction now runs only when XTTS-style cloning is
  required.

Validation after the fix:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
backend compileall: passed
GET /api/health: passed
real Kannada UI retry: complete
final localized MP4: rendered/downloadable in the results UI
```

The UI represents Kannada as Sarvam managed voice and does not describe Sarvam
as exact voice cloning.

## Final UI Evidence Pass Follow-Up - 2026-04-30

Focused final UI refinements were applied after the prior webflow pass.

Confirmed:

- Hero headline now reads `Video localization built for real dubbing workflows.`
- The hero visual is lighter, farther right, and less visually competitive.
- Architecture diagram now has a taller graph canvas, directed arrows, clearer branch routes, and an intentionally separated inspect panel.
- Architecture content now includes media prep, ASR, translation router, IndicTrans2, voice router, XTTS, Sarvam managed speech, disabled local IndicF5, audio validation, mux, and final MP4.
- Backend result generation no longer adds hardcoded localized-video confidence.
- Results UI no longer renders a fake confidence percentage.
- Results UI now separates backend decisions, validation checks, output inspection, run evidence, guardrails, and future evaluation hooks.
- New backend result metrics carry forward measured stage evidence and ffprobe stream metadata when a final MP4 is produced.

Validation:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
backend compileall backend app tools voice translation tts: passed
tools.inspect_pipeline_config: passed
kn dry-run with cloning_required=true: selected_engine=sarvam
fr dry-run with cloning_required=true: selected_engine=xtts
```

Post-change real web UI E2E status:

```text
blocked before frontend server start
```

The backend server started and `/api/health` returned `ok`. The first frontend
launch failed because extra arguments were parsed by Next.js as an invalid
project directory. The corrected launch required another sandbox escalation, but
the approval reviewer rejected it because the session hit its usage limit. No
indirect workaround was attempted, and no new heavy pipeline run was started.

## Real Run Analysis And Auto Reference Follow-Up - 2026-04-30

Backend and `NEW_Frontend` now use real `analysis` metadata for pipeline and
results evidence.

Confirmed:

- Active ASR accuracy, BLEU, MOS, LSE-C, and voice similarity placeholder rows
  were removed from the main results UI.
- `IndicF5 loaded: No` is no longer shown in primary job metric panels.
- Speaker count no longer defaults to `0`; jobs without diarization labels show
  speaker analysis as `not_run` or `not_determined`.
- Upload now supports `autoReference=true` for backend-supported XTTS reference
  extraction from the source video.
- Sarvam uploads do not require reference audio and remain labeled as managed
  Indian-language speech, not exact voice cloning.

New response field:

```text
analysis
```

with `run_evidence`, `speaker_analysis`, `reference_audio`,
`output_inspection`, `audio_validation`, and evaluator requirement metadata.

Validation:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
backend compileall backend app tools voice translation tts asr: passed
tools.inspect_pipeline_config: passed
kn dry-run with cloning_required=true: selected_engine=sarvam
fr dry-run with cloning_required=true: selected_engine=xtts
manual upload validation: XTTS requires uploaded or auto reference; Sarvam does not
auto-reference extractor: passed on Vidiolingua_Test_Official.mp4
```

## Real Evaluation Metrics Framework Follow-Up - 2026-04-30

`NEW_Frontend` now consumes backend `metricsReport` when present.

Upload page:

- adds an `Advanced evaluation` section;
- accepts optional ground-truth transcript file/text;
- accepts optional reference translation file/text;
- accepts optional human MOS rating and notes.

Results page:

- shows operational route and validation data from computed reports;
- shows audio/media inspection from WAV analysis and ffprobe;
- shows WER/CER/ASR accuracy and BLEU-lite/chrF-lite only when references are
  provided;
- shows MOS/LSE/voice similarity in a collapsed evaluator extension panel with
  `evaluator_not_installed` unless real evaluator data exists.

Validation:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
metrics report for Kannada proof job: audio/media computed, references required
metrics report for French proof job: audio/media computed, references required
```

## Economics And Automatic Metrics Correction - 2026-05-05

The prior standalone cost analysis artifacts are superseded by the native
frontend route:

```text
NEW_Frontend\app\economics\page.tsx
```

Navigation now includes `Economics`. The page uses the same frontend typography,
card rhythm, editorial grid, navigation, and footer as the rest of
`NEW_Frontend`; it does not embed the old standalone PNG/HTML report.

The upload page now labels reference-based scoring as `Expert evaluation
inputs`. It remains collapsed by default and is optional. Normal users are no
longer asked to provide ground-truth transcript, reference translation, MOS, or
notes as part of the standard run flow.

`metricsReport` now includes explicit automatic sections:

```text
operational
transcript
translation
voice_audio
media_output
validation
optional_reference_metrics
```

Reference-only metrics remain secondary:

- WER/CER/accuracy require a reference transcript.
- BLEU/chrF require a reference translation.
- MOS, LSE-C/LSE-D, and voice similarity require human input or evaluator
  models.
# 2026-05-05 Language Integrity UI Addendum

The frontend now has a dedicated `/language-integrity` page. Pipeline and results pages surface `linguisticIntegrity` and `phoneticResolution` summaries when the backend provides them.

Expected API/result fields:

- `linguisticIntegrity.status`
- `linguisticIntegrity.score`
- `linguisticIntegrity.scriptStatus`
- `linguisticIntegrity.numberWarnings`
- `linguisticIntegrity.nameWarnings`
- `linguisticIntegrity.expansionWarnings`
- `phoneticResolution.status`
- `phoneticResolution.phoneticRiskScore`
- `phoneticResolution.dictionaryUsed`
- `phoneticResolution.acronymsDetected`
- `phoneticResolution.ambiguityWarnings`
# 2026-05-05 Prosody/Differentiators Update

The frontend now includes a visible `/differentiators` route and prosody evidence cards in pipeline/results views. Backend status/result payloads can expose `analysis.prosodyElocution`, prosody metrics, manifest artifacts, and metrics report `prosody` values. Missing HuBERT data must display as unavailable rather than guessed.
## 2026-05-06 Responsible AI & Provenance Update

The backend now exposes `responsibleAI` in job status and result payloads for new runs. The upload page sends `responsibleAIConsent` form data, while pipeline/results pages show compliance mode, SGI risk, consent status, disclosure status, provenance manifest status, hash generation, audit ledger status, safe-for-demo/export, and warning/error counts.

The differentiators page integrates the Responsible AI & Provenance Engine as a same-page section under `NEW_Frontend\app\differentiators\page.tsx`; no separate frontend route was created.
## 2026-05-06 Speaker Analysis Panel Readiness

The frontend now treats speaker analysis as backend evidence, not a cosmetic
metric. Pipeline and results views show:

- status: computed, failed, unavailable, or not run
- speaker count only when computed
- unknown and ambiguous segment counts
- reference candidates
- voice assignment status
- visual analysis status
- exact errors, warnings, and fix instructions

Sarvam copy says managed TTS voice selection is not exact cloning. Voice-fit
hints are labeled as `Voice profile hint`; they are voice-fit routing hints, not
identity or demographic certainty.

## 2026-05-06 Reference Audio UI Update

The upload page now sends `referenceMode` as `uploaded`, `auto_extract`, or
`none`. Sarvam Indian-language managed TTS does not require reference audio and
allows either no reference or auto-analysis from the uploaded video. XTTS
speaker-reference routes require an uploaded reference or `auto_extract`; if
neither is selected, the frontend and backend show the same clear validation
message.
