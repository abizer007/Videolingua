# Frontend Polish And Integration Fix Plan - 2026-04-29

## Scope

Refine the existing `NEW_Frontend` Next.js app without rebuilding it, preserve the current premium/v0-inspired structure, and make the upload -> backend job -> status -> result flow robust against the actual FastAPI contract.

## Screenshot Issue Mapping

1. Hero heading and generic animated visual
   - File: `NEW_Frontend\components\vidiolingua\hero-section.tsx`
   - Current issue: `text-[clamp(3rem,10vw,9rem)]` makes the "Translate and dub videos..." headline dominate the first viewport.
   - Current issue: `AnimatedSphere` from `NEW_Frontend\components\landing\animated-sphere.tsx` reads as a generic AI template object.

2. Top-left brand presence
   - File: `NEW_Frontend\components\vidiolingua\site-navigation.tsx`
   - Current issue: brand spelling is correct in code, but the visual weight is too shy compared with the page scale.

3. Marquee / content strip
   - File: `NEW_Frontend\components\vidiolingua\hero-section.tsx`
   - Current issue: items such as `Kannada`, `Strict routes`, and `Final MP4` feel like placeholders instead of a product narrative.

4. Third screenshot architecture content
   - File: `NEW_Frontend\app\architecture\page.tsx`
   - Current issue: "A local pipeline with managed voice where it belongs." is accurate but generic and under-explains the system.

5. Human/original copy across the site
   - Files:
     - `NEW_Frontend\components\vidiolingua\workflow-section.tsx`
     - `NEW_Frontend\components\vidiolingua\backend-router-section.tsx`
     - `NEW_Frontend\components\vidiolingua\demo-showcase.tsx`
     - `NEW_Frontend\components\vidiolingua\language-support-section.tsx`
     - `NEW_Frontend\components\vidiolingua\quality-section.tsx`
     - `NEW_Frontend\components\vidiolingua\cta-section.tsx`
     - `NEW_Frontend\app\upload\page.tsx`
     - `NEW_Frontend\app\pipeline\page.tsx`
     - `NEW_Frontend\app\results\page.tsx`

## Exact UI And Content Changes

- Reduce the hero heading from the current 10vw/9rem clamp to a smaller, more balanced clamp while keeping the display type and two-line structure.
- Keep the large, clean first viewport, grid texture, and CTA rhythm.
- Increase the `Vidiolingua` brand text in the navigation and make the supporting product label less dominant.
- Rewrite hero eyebrow/subtext/CTA copy to sound product-real: source video, routing, voice generation, validation, and localized MP4 output.
- Replace marquee items with longer product-aware units:
  - `Speaker-reference dubbing`
  - `IndicTrans2 routing`
  - `Sarvam managed Indian voice`
  - `Validated audio before muxing`
  - `Source video -> localized MP4`
  - `No silent generic fallback`
  - `Upload -> route -> synthesize -> validate -> mux`
  - `Global + Indian language localization`
- Rewrite the architecture page hero to explain local orchestration, translation routing, XTTS, Sarvam, validation, and final MP4 generation in clear, memorable language.
- Tighten page microcopy so it reads as written by someone who understands the pipeline, not a generic AI landing template.

## Sphere Replacement

- Remove `AnimatedSphere` import/use from `VidiolinguaHeroSection`.
- Add a custom `LocalizationSignalVisual` component under `NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx`.
- The replacement will be a subtle product-specific motion composition:
  - language chips and stage labels arranged on a translation-flow grid
  - waveform bars suggesting speech synthesis
  - thin animated routes connecting upload, translation, voice, validation, and MP4
  - no orb, globe, sphere, or generic "AI brain" visual
- The visual will use CSS/SVG/HTML only, with no new dependencies.

## Copy Strategy

- Keep premium restraint: short headlines, specific nouns, no heavy sales tone.
- Emphasize proof and routing:
  - XTTS for supported global speaker-reference voice
  - IndicTrans2 for supported Indic translation pairs
  - Sarvam for managed Indian-language voice
  - validation before muxing
  - no silent generic fallback
  - final localized MP4
- Do not imply Sarvam is exact voice cloning.
- Keep IndicF5 visible only as disabled/local experimental status where already appropriate.
- Do not mention forbidden backends.

## Likely Frontend-Backend Failure Points

1. Result page query handling
   - `NEW_Frontend\app\results\page.tsx` currently reads `localStorage` first and ignores `?jobId=...`.
   - Direct navigation from `/pipeline?jobId=...` or a browser refresh can fetch the wrong/stale job or no job.

2. Pipeline error-stage handling
   - `NEW_Frontend\app\pipeline\page.tsx` only fetches results when `stage === "complete"`.
   - Backend returns a result payload for `stage === "error"`; the UI should surface that clearly instead of leaving users stranded.

3. API error messages
   - `NEW_Frontend\lib\api.ts` throws raw response text, which can be JSON strings or unhelpful FastAPI detail payloads.
   - Improve parsing of `{detail: ...}` and HTTP 202 "job not complete" responses.

4. Upload validation and schema alignment
   - FastAPI expects:
     - `video`
     - `languages`
     - `voiceOptions`
     - `sourceLanguage`
     - `voiceSample`
   - The frontend matches these names, but it should validate `video.type`, XTTS reference audio, and unsupported language state before submitting.

5. Backend voice routing alignment
   - Frontend sends `cloned=true` for XTTS and `cloned=false` for Sarvam.
   - The pipeline extracts reference audio even when cloning is false, so lightweight tests should confirm Sarvam still routes to Sarvam instead of legacy or IndicF5.
   - If a small backend fix is needed, it should be limited to API/routing integration and not core model behavior.

6. API base URL behavior
   - `NEXT_PUBLIC_API_URL` is set to `http://localhost:8000` in `.env.local`.
   - Validate health checks and CORS against the running FastAPI app.

## Files Expected To Change

- `docs\FRONTEND_POLISH_AND_INTEGRATION_FIX_PLAN_2026-04-29.md`
- `docs\FRONTEND_POLISH_AND_INTEGRATION_FIX_REPORT_2026-04-29.md`
- `docs\FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md` if integration behavior changes
- `COMMAND_LOG.md`
- `NEW_Frontend\components\vidiolingua\hero-section.tsx`
- `NEW_Frontend\components\vidiolingua\site-navigation.tsx`
- `NEW_Frontend\components\vidiolingua\localization-signal-visual.tsx`
- `NEW_Frontend\components\vidiolingua\workflow-section.tsx`
- `NEW_Frontend\components\vidiolingua\backend-router-section.tsx`
- `NEW_Frontend\components\vidiolingua\demo-showcase.tsx`
- `NEW_Frontend\components\vidiolingua\language-support-section.tsx`
- `NEW_Frontend\components\vidiolingua\quality-section.tsx`
- `NEW_Frontend\components\vidiolingua\cta-section.tsx`
- `NEW_Frontend\app\architecture\page.tsx`
- `NEW_Frontend\app\upload\page.tsx`
- `NEW_Frontend\app\pipeline\page.tsx`
- `NEW_Frontend\app\results\page.tsx`
- `NEW_Frontend\lib\api.ts`
- `NEW_Frontend\lib\types.ts` only if the actual backend response shape needs a small type adjustment
- `backend\main.py` only if lightweight API testing proves a small endpoint compatibility fix is required
- `backend\pipeline_runner.py` only if lightweight routing validation proves the API path sets the wrong TTS mode

## Backup / Rollback Plan

- Before code edits, copy key frontend files into a timestamped `_snapshots` folder.
- Avoid touching protected outputs:
  - `outputs\french_official_test`
  - `outputs\kannada_sarvam_practical_test_clipfix`
- Avoid touching `models\xtts_v2`.
- Do not mutate Python virtual environments.

## Validation Steps

Frontend:

```powershell
cd NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

Backend/light integration:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts lipsync
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --output outputs\validation\frontend_polish_router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --target-language fr --reference test_speaker_ref.wav --output outputs\validation\frontend_polish_router_fr.wav --dry-run
```

API contract checks:

- Start FastAPI if needed.
- Call `/api/health`.
- Exercise upload contract with a minimal temporary video only if necessary.
- Poll one job until the first meaningful status/error; do not loop full heavy runs.

UI QA:

- Start the frontend dev server if needed.
- Check `/`, `/upload`, `/pipeline`, `/results`, `/architecture`, and `/backends`.
- Verify:
  - hero heading is smaller
  - `Vidiolingua` brand is more prominent
  - sphere is gone
  - new signal visual renders
  - marquee content is product-specific
  - architecture section reads stronger
  - upload/status/results errors are visible and actionable

## Risks And Mitigations

- Risk: over-polishing into a new site.
  - Mitigation: keep existing layout, grid texture, spacing, cards, dark sections, and CTA rhythm.
- Risk: copy implies unsupported voice cloning.
  - Mitigation: keep Sarvam described as managed Indian-language voice, not exact cloning.
- Risk: integration testing triggers a heavy pipeline repeatedly.
  - Mitigation: use health checks, dry-run routers, and at most one carefully stopped upload flow if needed.
- Risk: stale localStorage makes the results page appear broken.
  - Mitigation: use query `jobId` as the source of truth when present, then fall back to stored job/result.
- Risk: backend route drift from frontend constants.
  - Mitigation: keep frontend language constants aligned with documented XTTS/Sarvam allowlists and recommend a future `/api/capabilities` endpoint.
