# Frontend Final UI And Webflow Test Report - 2026-04-29

## 1. Final Hero Headline

```text
Video localization built for real dubbing workflows.
```

CTA updated to:

```text
Start a localization run
```

## 2. Hero Visual Change Summary

The existing product-specific localization visual was preserved but made lighter:

- reduced right-side width and opacity;
- moved farther right on large screens;
- reduced waveform density and contrast;
- kept subtle route lines and subtitle-to-voice motif;
- avoided cards, spheres, or generic AI-orb visuals.

## 3. Architecture Diagram Fixes

The architecture diagram was rebuilt with a taller, intentional graph canvas and a separated inspect panel:

- graph canvas now has enough vertical space for the final delivery nodes;
- mobile/narrow layouts use an intentional horizontal scroll region;
- inspect panel no longer squeezes the graph at laptop widths;
- node placement uses centered coordinates so cards do not overflow the bottom edge.

## 4. Architecture Correctness Notes

The diagram now shows:

- Next.js UI;
- FastAPI job orchestration;
- media prep / audio extraction;
- ASR transcription;
- translation router;
- IndicTrans2;
- voice router;
- XTTS for supported global speaker-reference languages;
- Sarvam managed Indian-language voice;
- IndicF5 disabled/local experimental;
- audio validation;
- FFmpeg / mux;
- final MP4.

Sarvam is described as managed TTS, not exact voice cloning. IndicF5 is marked disabled and not part of the active runtime path. Generic fallback is not presented as an available success route.

## 5. Arrow And Animation Changes

- Replaced ambiguous route lines with directed SVG paths and arrowheads.
- Kept animation subtle and limited to active/related paths.
- Made the main flow direction explicit from UI to backend to media prep, ASR, translation, voice, validation, mux, and final MP4.
- Branches from voice router to XTTS, Sarvam, and disabled IndicF5 are visually distinct.

## 6. Fake Metrics Removed

Removed from active new result payloads and UI:

- hardcoded `confidence: 0.88`;
- result-page display of `Confidence: 88.0%`.

The active `NEW_Frontend` did not contain current ASR Accuracy, BLEU, MOS, LSE-C, CSIM, FID, or fake ROI cards. Historical protected `pipeline_result.json` files still contain the old confidence value and were not modified.

## 7. Real Metrics And Analysis Framework Added

Results page now includes evidence panels:

- Backend decisions
- Validation checks
- Output inspection
- Run evidence
- Future hooks

Pipeline page labels were expanded for real backend metrics and guardrails.

Backend result metrics now carry forward measured stage evidence and add ffprobe output metadata for new jobs:

- stage-derived ASR/translation/TTS/mux counts and durations;
- translation backend from translation JSON when present;
- fallback policy booleans when present;
- voice route booleans;
- final MP4 size and duration;
- final audio/video stream presence;
- video codec, resolution, fps;
- audio codec, sample rate, channels.

## 8. Backend Data Used

Used real data from:

- `GET /api/job-status/{job_id}` status metrics;
- `GET /api/result/{job_id}` result metrics;
- translation JSON route metadata;
- ffprobe inspection of newly produced final MP4s.

Not measured today and explicitly labeled as future hooks:

- ASR accuracy;
- BLEU;
- MOS;
- LSE-C;
- voice similarity.

## 9. Frontend-Backend Integration Findings

Confirmed by inspection:

- `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`.
- Upload fields remain `video`, `languages`, `voiceOptions`, `sourceLanguage`, and `voiceSample`.
- Kannada UI route sends `cloned=false` and does not require reference audio.
- XTTS routes still require reference audio in the UI.
- Status polling terminal states remain `complete` and `error`.
- Results use `?jobId=...` as the source of truth when present.

Backend result payload was corrected so new localized videos no longer carry invented confidence scores.

## 10. Real E2E UI Test Steps

Planned steps:

1. Start backend on `127.0.0.1:8000`.
2. Start frontend on `127.0.0.1:3000`.
3. Open the real UI.
4. Upload `Vidiolingua_Test_Official.mp4`.
5. Select Kannada.
6. Start one job.
7. Watch pipeline progress.
8. Open results and confirm final MP4 preview/download.

## 11. Real E2E UI Test Result

Blocked in this pass.

Backend started and health returned `ok`. The first frontend launch failed because extra dev-server arguments were parsed as an invalid Next.js project directory. The corrected launch required another sandbox escalation, but the approval reviewer rejected it because the session had hit its usage limit. Per policy, no indirect frontend launch workaround was attempted.

No new heavy pipeline run was started after these UI changes.

## 12. Failure Root Cause And Fix

Root cause of E2E block:

- local frontend server could not be restarted after the corrected launch command required approval;
- approval was rejected by session usage limit, not by a code failure.

Code fixes completed before the block:

- backend result confidence removed;
- backend result metrics made evidence-based;
- architecture layout and arrows rebuilt;
- results panels now separate measured data from future hooks.

## 13. Files Changed

```text
docs\FRONTEND_FINAL_UI_AND_WEBFLOW_TEST_PLAN_2026-04-29.md
docs\FRONTEND_FINAL_UI_AND_WEBFLOW_TEST_REPORT_2026-04-29.md
NEW_Frontend\components\vidiolingua\hero-section.tsx
NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx
NEW_Frontend\components\vidiolingua\interactive-architecture-diagram.tsx
NEW_Frontend\components\vidiolingua\architecture-flow.tsx
NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx
NEW_Frontend\app\pipeline\page.tsx
NEW_Frontend\app\results\page.tsx
NEW_Frontend\lib\types.ts
backend\pipeline_runner.py
```

Rollback snapshot:

```text
_snapshots\frontend_final_ui_webflow_20260430_1125
```

## 14. Remaining Issues

- Real post-change web UI E2E is still pending.
- Existing protected historical `pipeline_result.json` files contain old `confidence` fields and should stay untouched unless the user explicitly asks for regenerated proof artifacts.
- Next build still skips TypeScript validation because the project config has `typescript.ignoreBuildErrors=true`.
- The backend job store is still in-memory.

## 15. Recommendations Before Demo

1. Start frontend with `corepack pnpm run dev` from `NEW_Frontend` after approval is available.
2. Run exactly one Kannada UI job.
3. Confirm result panels show measured fields and `Not measured` future hooks instead of invented benchmark scores.
4. Capture the completed job id and final MP4 metadata in a short addendum.

## Validation Summary

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
backend compileall: passed
tools.inspect_pipeline_config: passed
Kannada voice router dry-run: selected Sarvam
French voice router dry-run: selected XTTS
Real post-change web UI E2E: blocked before frontend server start
```

## Safety Confirmation

- Core design preserved.
- No secrets exposed.
- No Sarvam key in frontend.
- No Python virtual environment mutation.
- No backend dependency reinstall.
- No heavy pipeline loop.
- No local IndicF5 load.
- `models\xtts_v2` untouched.
- Protected French and Kannada output folders untouched.
