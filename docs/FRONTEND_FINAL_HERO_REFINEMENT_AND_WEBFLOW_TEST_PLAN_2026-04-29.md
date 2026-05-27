# Frontend Final Hero Refinement And Webflow Test Plan - 2026-04-29

## Scope

Do one focused frontend refinement pass and one real web-interface pipeline check. Preserve the existing `NEW_Frontend` premium design; do not rebuild the site.

## 1. Files And Components To Update

Hero and visual:

```text
NEW_Frontend\components\vidiolingua\hero-section.tsx
NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx
NEW_Frontend\app\globals.css
```

Light copy pass:

```text
NEW_Frontend\app\upload\page.tsx
NEW_Frontend\app\pipeline\page.tsx
NEW_Frontend\app\results\page.tsx
NEW_Frontend\app\architecture\page.tsx
NEW_Frontend\app\backends\page.tsx
NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx
```

Integration inspection / likely no code change unless real UI flow fails:

```text
NEW_Frontend\lib\api.ts
NEW_Frontend\lib\language-capabilities.ts
backend\main.py
backend\job_store.py
backend\pipeline_runner.py
```

Docs:

```text
docs\FRONTEND_FINAL_HERO_REFINEMENT_AND_WEBFLOW_TEST_REPORT_2026-04-29.md
docs\FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md
COMMAND_LOG.md
```

## 2. Headline Options And Chosen Direction

Options considered:

1. `Translate and dub videos across languages.`
2. `From source video to localized speech and final MP4.`
3. `Video localization built for real dubbing workflows.`
4. `Localize video with translation, voice, and final MP4 delivery.`

Chosen headline:

```text
Video localization built for real dubbing workflows.
```

Reason:

- It reads as a complete professional sentence.
- It avoids the awkward rotating-word grammar.
- It positions Vidiolingua as a workflow/pipeline product, not a generic AI demo.
- It leaves room for the subtext to explain ASR, routing, XTTS, Sarvam, validation, and muxing.

## 3. Hero Visual Simplification

The current replacement visual is too busy because it uses multiple floating panels, language chips, and a large waveform block near the headline area.

Plan:

- Remove floating cards/panels from the hero visual.
- Replace with a quieter, mostly-line-based technical composition:
  - faint route lines
  - small endpoint dots
  - restrained waveform rails
  - tiny labels such as `source`, `translate`, `voice`, `validate`, `mp4`
- Keep it on the right side and reduce opacity.
- Add a left-to-right fade so the hero text area remains clean.
- Use CSS/SVG only; no new dependencies.

## 4. Real UI Integration Test Plan

Preferred workflow: Kannada through the actual UI.

Assets:

```text
Vidiolingua_Test_Official.mp4
test_speaker_ref.wav
```

Steps:

1. Start backend with `.venv_api`.
2. Start `NEW_Frontend`.
3. Confirm `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
4. Load frontend root and upload page.
5. Use browser automation or a browser-equivalent UI test to:
   - choose `Vidiolingua_Test_Official.mp4`
   - select target language `kn`
   - optionally attach `test_speaker_ref.wav` only if the current UI requires or accepts it
   - submit the form
   - follow `/pipeline?jobId=...`
   - wait for terminal state
   - open `/results?jobId=...`
   - verify result metadata and MP4 URL/render/download control
6. Stop after one run unless there is a meaningful fixable failure; then apply one fix and retry once.

Browser note:

The in-app browser plugin previously failed because local Node was `22.15.0` and the plugin required `>=22.22.0`. If that remains true, use the project’s available browser automation path from installed frontend dependencies or a local browser/CDP route. The test must still exercise the web UI code path, not just call backend functions.

## 5. Likely Failure Points

- Browser automation availability on this machine.
- Large upload timeout or browser file-input automation issue.
- Frontend default target language is French, so the UI test must explicitly select Kannada.
- Sarvam route must stay labeled as managed Indian-language voice, not exact cloning.
- Backend job store is in-memory, so backend restart would lose job status.
- Result videos are served from `/api/result/{job_id}/file/{filename}` and must be reachable by the frontend.
- Pipeline may fail if environment variables for Sarvam/IndicTrans2 are not loaded by the backend process.
- Heavy run should not write to protected output folders; backend upload jobs write under `jobs\{job_id}`.

## 6. Validation Steps

Frontend:

```powershell
cd NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

Backend health:

```powershell
.\.venv_api\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
GET http://127.0.0.1:8000/api/health
GET http://127.0.0.1:8000/api/tts-health
```

Frontend health:

```powershell
corepack pnpm run dev -- --hostname 127.0.0.1 --port 3000
GET http://127.0.0.1:3000
GET http://127.0.0.1:3000/upload
GET http://127.0.0.1:3000/pipeline
GET http://127.0.0.1:3000/results
```

Real webflow:

- Submit one Kannada job through the UI.
- Monitor backend status and UI pages.
- Verify final output file URL exists and is downloadable/renderable.

## 7. Rollback And Risk Notes

- Before edits, snapshot the key frontend files into `_snapshots`.
- Do not touch:
  - `outputs\french_official_test`
  - `outputs\kannada_sarvam_practical_test_clipfix`
  - `models\xtts_v2`
- Do not mutate Python virtual environments.
- Do not reinstall backend dependencies.
- Do not enable local IndicF5.
- Do not expose or copy secrets into frontend or docs.
- Limit real pipeline execution to one initial run and one retry only if there is a clear fix.
