# Frontend Final UI And Webflow Test Plan - 2026-04-29

## 1. Components And Files To Update

Frontend:

- `NEW_Frontend\components\vidiolingua\hero-section.tsx`
- `NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx`
- `NEW_Frontend\components\vidiolingua\interactive-architecture-diagram.tsx`
- `NEW_Frontend\components\vidiolingua\architecture-flow.tsx`
- `NEW_Frontend\app\pipeline\page.tsx`
- `NEW_Frontend\app\results\page.tsx`
- `NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx`
- `NEW_Frontend\components\vidiolingua\result-video-card.tsx`
- `NEW_Frontend\lib\types.ts`

Backend/API evidence:

- `backend\pipeline_runner.py`
- `backend\job_store.py` only if the public result/status shape needs a small extension.

Docs:

- `docs\FRONTEND_FINAL_UI_AND_WEBFLOW_TEST_REPORT_2026-04-29.md`
- `docs\FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md`
- `COMMAND_LOG.md`

## 2. Hero Headline Options And Chosen Headline

Options considered:

- `Localize videos into new languages.`
- `Turn source videos into localized MP4s.`
- `Translate, voice, and deliver localized video.`
- `Video localization built for real dubbing workflows.`
- `From source video to localized speech.`

Chosen headline:

```text
Video localization built for real dubbing workflows.
```

It is concise, product-specific, and honest about the current pipeline without implying a generic magic dubbing layer.

## 3. Hero Visual Simplification Approach

Keep the current custom localization visual instead of returning to a generic sphere/orb. Simplify it further by:

- reducing contrast and density;
- moving the visual farther right on large screens;
- using thin route lines and a subdued waveform/subtitle-to-audio motif;
- avoiding floating cards and template-like dashboard fragments;
- ensuring it never sits under or competes with the headline.

## 4. Architecture Diagram Layout Fix Plan

- Increase graph canvas height and allow visible overflow where needed.
- Switch the desktop graph to a wider responsive canvas with an intentionally separated inspect panel.
- Use a mobile stacked card layout instead of absolute-positioned graph nodes on small screens.
- Keep the inspect panel beside the graph only when there is enough horizontal room.
- Ensure node positions do not exceed the graph boundary and the bottom result nodes are not clipped.

## 5. Architecture Correctness Checklist

The diagram must represent:

- Next.js UI
- FastAPI backend / job orchestration
- Audio extraction / media prep
- ASR / transcription
- Translation router
- IndicTrans2 for supported Indic translation pairs
- Voice router
- XTTS for supported global speaker-reference languages
- Sarvam for Indian regional managed voice
- IndicF5 disabled/local experimental only
- Audio validation / cleanup
- Lipsync / mux / FFmpeg
- Final MP4 result

The diagram must not:

- show IndicF5 as active;
- imply Sarvam is exact voice cloning;
- imply generic fallback;
- show XTTS as the Kannada/Hindi backend;
- mention or use forbidden voice backends.

## 6. Arrow And Animation Improvement Plan

- Replace ambiguous dashed routes with clearer directed SVG paths.
- Add arrowheads that follow the actual stage direction.
- Use one subtle moving highlight on the active or primary pipeline path.
- Avoid random decorative motion.
- Keep branch arrows from voice router to XTTS/Sarvam/disabled IndicF5 clear and non-overlapping.

## 7. Current Fake Or Hardcoded Metrics Found

Found and to remove:

- `backend\pipeline_runner.py` adds `confidence: 0.88` to every localized video result.
- `NEW_Frontend\app\results\page.tsx` renders that as `Confidence: 88.0%`.

Already absent from the active `NEW_Frontend` surfaces inspected in this pass:

- ASR Accuracy `95.2%`
- BLEU `0.87`
- MOS `4.3/5`
- LSE-C `0.89`
- CSIM
- FID
- fake ROI

Protected historical `pipeline_result.json` files still contain old `confidence: 0.88`; those protected outputs will not be overwritten.

## 8. Real Metrics Available From Backend And Job Outputs

Currently available from status/result data:

- active stage
- progress
- elapsed seconds
- stage history and stage durations
- ASR segment count
- speaker count when ASR reports speakers
- ASR output file count
- source language and confidence if ASR reports it
- translation output file count
- target language count
- generated TTS WAV count
- generated TTS total duration
- source video duration
- TTS/video duration delta
- mux output file count
- final MP4 count
- final MP4 size
- final MP4 duration
- final/video duration delta
- total backend runtime
- languages processed
- BGM preserved boolean

Available from real output artifacts with small backend probing:

- final video/audio stream presence
- final video codec, resolution, FPS
- final audio codec, sample rate, and channel count
- final MP4 byte size

Available from translation JSON:

- translation engine such as `indictrans2`
- source language
- target language
- fallback allowed/used policy when written by the translation stage

Not currently exposed reliably:

- BLEU, MOS, LSE-C, CSIM, FID, ASR accuracy
- exact perceptual voice similarity
- Sarvam request status beyond stage success/failure
- audio peak after cleanup for every full pipeline job

These must be labeled as not measured or future hooks, not shown as current scores.

## 9. Quality And Results Analysis Framework Plan

Pipeline page:

- show active stage, elapsed time, stage history, completed/pending states;
- show backend routing decisions from stored job metadata plus real backend metrics when present;
- show live evidence metrics exactly as returned by backend;
- label missing data as pending/not reported.

Results page:

- keep video preview/download;
- add structured panels:
  - Backend decisions
  - Validation checks
  - Output inspection
  - Media metadata
  - Guardrails
  - Future evaluation hooks
- remove confidence percentage;
- show not measured/not available for uncomputed metrics.

## 10. Real Web-Interface E2E Test Plan

After lint/build/backend checks:

1. Start FastAPI backend on `127.0.0.1:8000`.
2. Start `NEW_Frontend` on `127.0.0.1:3000`.
3. Use the real browser UI for:
   - home page load;
   - upload page load;
   - upload `Vidiolingua_Test_Official.mp4`;
   - select Kannada;
   - submit one job;
   - observe pipeline progress;
   - confirm no fake scores appear;
   - open results;
   - confirm final MP4 preview/download if the job completes.
4. If Kannada fails because of a real integration bug, fix that bug and retry once.
5. Stop after one retry. Do not run heavy loops.

## 11. Risks And Stop Conditions

Risks:

- Browser automation may be blocked by local browser tooling limitations.
- Kannada Sarvam can take several minutes and uses managed API quota.
- Existing job store is in-memory; backend restart loses live job status.
- Protected historical result JSON files contain old confidence fields but must not be overwritten.

Stop conditions:

- any sign of local IndicF5 model loading;
- missing Sarvam backend key or managed service error that is unrelated to frontend integration;
- a second real pipeline failure after one meaningful retry;
- any risk of overwriting protected output folders or `models\xtts_v2`;
- any accidental secret exposure in frontend or docs.
