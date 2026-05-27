# Frontend Final Hero Refinement And Webflow Test Report - 2026-04-29

## Summary

This pass kept the current premium `NEW_Frontend` structure intact and focused on the remaining weak points: the hero headline, the right-side hero visual, restrained copy polish, and a real browser-driven upload-to-result test.

The real web-interface Kannada run initially exposed a backend integration bug. After a narrow pipeline fix, the retry completed through the UI and produced a downloadable Kannada MP4.

## Hero Visual Change

The right-side hero artwork was simplified in:

```text
NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx
NEW_Frontend\components\vidiolingua\hero-section.tsx
```

The previous busier composition was replaced with a quieter localization signal motif: faint routing lines, small stage nodes, subtitle-to-audio waveform cues, and restrained labels for source, translate, voice, validate, and MP4. The visual is now limited to the right side with reduced opacity and a left-to-right fade so it does not fight the hero headline.

## Final Hero Headline

Chosen headline:

```text
Video localization built for real dubbing workflows.
```

This was chosen because it is direct, product-specific, and less awkward than the previous wording. It describes the product as a workflow system rather than a generic AI demo.

Updated hero support copy:

```text
Vidiolingua takes a source video through ASR, translation routing, voice generation, validation, and muxing. XTTS handles supported speaker-reference dubbing; Sarvam handles managed Indian-language speech without pretending to clone.
```

CTA changes:

- Primary: `Start a dubbing run`
- Secondary: `View architecture`
- Results link: `Review proof outputs`

## Sitewide Humanization Changes

Copy was lightly refined across:

```text
NEW_Frontend\app\upload\page.tsx
NEW_Frontend\app\pipeline\page.tsx
NEW_Frontend\app\results\page.tsx
NEW_Frontend\app\architecture\page.tsx
NEW_Frontend\app\backends\page.tsx
NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx
```

Changes stayed restrained: clearer labels, less template-like helper text, more accurate language around XTTS and Sarvam, and stage names that read like a real localization pipeline:

```text
Prepare audio
Transcribe speech
Route translation
Generate voice
Validate audio
Mux media
Serve final MP4
```

Sarvam is described as managed Indian-language speech/TTS, not exact voice cloning.

## Frontend Backend Integration Findings

Reviewed integration points:

- `NEXT_PUBLIC_API_URL` behavior in `NEW_Frontend\lib\api.ts`
- multipart upload field names: `video`, `languages`, `voiceOptions`, `sourceLanguage`, `voiceSample`
- target language selection and Kannada/Sarvam messaging
- pipeline polling through `/api/job-status/{jobId}`
- result fetch through `/api/result/{jobId}`
- result video URLs through `/api/result/{jobId}/file/{filename}`
- terminal error handling and user-facing UI text

The frontend payload shape was correct. The real failure was in backend pipeline orchestration for Sarvam-routed Indic jobs.

## Real E2E UI Test

Local services:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:3000`

Health and page checks:

- Backend `/api/health`: passed
- Backend `/api/tts-health`: passed, Sarvam configured
- Frontend `/upload`: loaded
- Frontend root page served the updated hero copy

Browser automation note:

The in-app browser plugin could not initialize because the local Node runtime is below the plugin requirement. I used a headless Chrome session controlled through the Chrome DevTools Protocol instead, which still exercised the real Next.js UI, real file inputs, real form submission, and real route transitions.

### Initial Real Run

Input:

```text
Video: Vidiolingua_Test_Official.mp4
Target language: Kannada
Reference audio: test_speaker_ref.wav
```

Job:

```text
9437b97a-2ed8-45da-bb5c-9dd04d36173a
```

Observed stages:

```text
uploading -> asr -> translation -> error
```

Failure:

```text
IndicF5 requires the exact transcript of the reference audio. Provide --reference-text, --reference-text-path, VIDIOLINGUA_REFERENCE_TEXT, or VIDIOLINGUA_REFERENCE_TEXT_PATH. The pipeline will not guess this transcript.
```

Root cause:

`backend\pipeline_runner.py` still enforced the disabled experimental Indic reference-transcript guard for Kannada even when the configured Indic voice backend was Sarvam. It also attempted voice-sample extraction for managed Sarvam jobs where XTTS-style cloning was not required.

## Fix Applied

File:

```text
backend\pipeline_runner.py
```

Fixes:

- Added `_indic_voice_backend()` to read `VIDIOLINGUA_INDIC_VOICE_BACKEND`, defaulting safely to `sarvam`.
- Changed `_requires_indicf5_reference_text()` so the transcript requirement only applies when the configured Indic voice backend is explicitly `indicf5`.
- Changed voice sample extraction to run only when `cloning_required` is true.

This preserves Sarvam as the managed Indian-language TTS route and does not enable local experimental IndicF5.

Backend compile and routing checks after the fix:

```text
.\.venv_api\Scripts\python.exe -m compileall backend: passed
Kannada router dry-run: selected_engine=sarvam, cloning_required=false, exact_voice_clone=false
```

## Retry Real Run

Input:

```text
Video: Vidiolingua_Test_Official.mp4
Source language: en
Target language: Kannada
Reference audio: none, because Sarvam managed TTS does not require exact voice cloning
```

Job:

```text
63cf909f-7f34-48b7-afe8-44f9f1fc09fe
```

Observed UI/backend stages:

```text
uploading -> asr -> translation -> tts -> lipsync -> complete
```

Final UI route:

```text
http://127.0.0.1:3000/results?jobId=63cf909f-7f34-48b7-afe8-44f9f1fc09fe
```

Result payload included:

```text
originalVideo:
http://localhost:8000/api/result/63cf909f-7f34-48b7-afe8-44f9f1fc09fe/file/input_video.mp4

localizedVideos[0]:
language=kn
url=http://localhost:8000/api/result/63cf909f-7f34-48b7-afe8-44f9f1fc09fe/file/input_video_dubbed_kn.mp4
confidence=0.88
```

UI result handling:

- Results page loaded automatically.
- Original video element was present.
- Localized Kannada video element was present.
- Download links for both original and localized MP4 were present.
- UI text represented Kannada as Sarvam managed Indian-language voice and did not claim exact cloning.

Artifact check:

```text
jobs\63cf909f-7f34-48b7-afe8-44f9f1fc09fe\results\input_video_dubbed_kn.mp4
size: 78,532,708 bytes
ffprobe: H.264 video, AAC audio, duration 30.575011s
```

## Validation

Frontend:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
```

Build warning only:

```text
stale baseline-browser-mapping data
```

Backend:

```text
GET /api/health: passed
GET /api/tts-health: passed
compileall backend: passed
Kannada real UI retry: complete
```

Protection checks:

- No Sarvam key was added to frontend files.
- No public frontend key environment pattern was found in the frontend.
- No Python virtual environment was mutated.
- No backend dependencies were reinstalled.
- No full heavy pipeline loop was run; there was one real submitted failure and one retry after the fix.
- `models\xtts_v2` was not modified.
- Protected output directories were not overwritten.

## Files Changed

```text
NEW_Frontend\components\vidiolingua\hero-section.tsx
NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx
NEW_Frontend\app\upload\page.tsx
NEW_Frontend\app\pipeline\page.tsx
NEW_Frontend\app\results\page.tsx
NEW_Frontend\app\architecture\page.tsx
NEW_Frontend\app\backends\page.tsx
NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx
backend\pipeline_runner.py
docs\FRONTEND_FINAL_HERO_REFINEMENT_AND_WEBFLOW_TEST_PLAN_2026-04-29.md
docs\FRONTEND_FINAL_HERO_REFINEMENT_AND_WEBFLOW_TEST_REPORT_2026-04-29.md
docs\FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md
COMMAND_LOG.md
```

Rollback snapshot:

```text
_snapshots\frontend_final_hero_webflow_20260430
```

## Remaining Issues

- The in-app browser plugin is blocked by the local Node version, so visual/browser QA used headless Chrome CDP instead.
- Backend file URLs support normal `GET` video rendering/download; `HEAD` returned 405 during a direct probe, which does not block the UI.
- The successful web-flow test created a normal job workspace under `jobs\63cf909f-7f34-48b7-afe8-44f9f1fc09fe`.

## Recommendation Before Final Demo

Use the successful job above as the current proof run, and keep the frontend pointed at `NEXT_PUBLIC_API_URL=http://localhost:8000` for demo testing.
