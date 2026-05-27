# Frontend Revamp Plan - 2026-04-29

## Source Template

The visual foundation is the v0 Optimus template downloaded into:

```text
NEW_Frontend
```

The template is a Next.js app-router project with Tailwind CSS 4, shadcn-style UI components, `lucide-react`, dark/premium landing sections, animated SVG/React visuals, and a full landing page split across `components/landing`.

## Current NEW_Frontend Structure

```text
NEW_Frontend/
  app/
    globals.css
    layout.tsx
    page.tsx
  components/
    landing/
      navigation.tsx
      hero-section.tsx
      features-section.tsx
      how-it-works-section.tsx
      infrastructure-section.tsx
      metrics-section.tsx
      integrations-section.tsx
      security-section.tsx
      developers-section.tsx
      testimonials-section.tsx
      pricing-section.tsx
      cta-section.tsx
      animated-sphere.tsx
      animated-tetrahedron.tsx
      animated-wave.tsx
    ui/
      shadcn-style primitives including button, card, select, progress, input,
      textarea, tabs, badge, alert, tooltip, dialog, and more.
  hooks/
  lib/
    utils.ts
  public/
  styles/
  package.json
  pnpm-lock.yaml
  next.config.mjs
  tsconfig.json
```

Important implementation notes:

- Package manager appears to be pnpm because only `pnpm-lock.yaml` exists.
- `node_modules` is not present in `NEW_Frontend`; no dependency install should be run without approval.
- Template scripts are `dev`, `build`, `lint`, and `start`.
- The app currently contains only the landing page at `/` and generic Optimus content.

## Existing frontend-next Structure

```text
frontend-next/
  src/app/
    page.tsx
    upload/page.tsx
    pipeline/page.tsx
    results/page.tsx
    architecture/page.tsx
    layout.tsx
    providers.tsx
  src/services/api.ts
  src/hooks/useJobPolling.ts
  src/store/pipeline-store.ts
  src/components/pipeline/
  src/components/ui/
  package.json
  package-lock.json
  node_modules/
```

Useful existing behavior to port/adapt:

- Upload sends `FormData` to `POST /api/upload`.
- Job polling calls `GET /api/job-status/{jobId}`.
- Results call `GET /api/result/{jobId}` and display direct backend video URLs.
- The old language picker is incomplete and includes only a small set of global/Hindi languages.
- Existing copy incorrectly trends toward generic voice cloning for all languages and must be corrected.

## Backend API Contract

Current FastAPI endpoints:

```text
GET /
GET /api/health
GET /api/health/deps
GET /tts-health
GET /api/tts-health
POST /api/upload
GET /api/job-status/{job_id}
GET /api/result/{job_id}
GET /api/result/{job_id}/file/{filename}
```

Upload request format:

```text
video: file, required
languages: JSON string array
voiceOptions: JSON object string
sourceLanguage: optional string
voiceSample: optional audio file
```

Status response shape:

```text
jobId
stage
progress
currentLanguage
languages
sourceLanguage
sourceLanguageConfidence
error
metrics
```

Result response shape:

```text
jobId
originalVideo
localizedVideos[{ language, url, confidence }]
metrics
error?
```

Frontend env:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

No secrets belong in frontend env. Sarvam credentials must remain backend-only.

## Recommended Target Strategy

Use `NEW_Frontend` as the new app and keep `frontend-next` untouched as a known integration reference.

Reasons:

- User requested work inside `NEW_Frontend` first.
- The v0 template already provides the desired premium landing visual foundation.
- `frontend-next` currently contains useful implementation references but a different design system and should not be destroyed before the new app builds.

Approach:

- Keep the v0 visual rhythm, typography, dark hero bands, premium cards, animated visual motifs, and section cadence.
- Replace generic Optimus content with Vidiolingua-specific content.
- Add app-router pages for `/upload`, `/pipeline`, `/results`, `/architecture`, and `/backends`.
- Implement a dependency-light frontend API client using `fetch` instead of adding Axios/Zustand/Dropzone/Framer dependencies.
- Persist current job/result state in browser storage so upload, pipeline, and results can hand off without adding a global store dependency.

## Pages To Implement

1. `/`
   - Premium landing page.
   - Hero: "Translate and dub videos across global and Indian languages".
   - CTA buttons: "Start a dubbing job", "View architecture", "See demo outputs".
   - Demo cards for French XTTS and Kannada IndicTrans2 + Sarvam.
   - Technology badges for XTTS, IndicTrans2, Sarvam AI, Whisper/ASR, FFmpeg.
   - Honest voice backend note: XTTS is speaker-reference cloning for supported global languages; Sarvam is managed Indian-language TTS and not exact cloning.

2. `/upload`
   - Source video upload.
   - Optional reference audio upload.
   - Target language dropdown/list across XTTS and Sarvam groups.
   - Mode/voice behavior explanation based on selected language.
   - Submit to backend upload endpoint and navigate to pipeline with job id.

3. `/pipeline`
   - Job status page with polling.
   - Stages shown as: Audio extraction, ASR/transcription, Translation, Voice generation, Audio validation, Lipsync/mux, Final MP4.
   - Backend labels: IndicTrans2 for Indic translation, XTTS or Sarvam voice as applicable, IndicF5 disabled/local experimental.

4. `/results`
   - Result video player(s), download links, metadata cards, language/backend labels, voice backend note.
   - Demo output showcase cards for the protected known-good French and Kannada paths as informational references only. Do not overwrite these outputs.

5. `/architecture`
   - Premium visual architecture page.
   - Pipeline flow, local vs managed split, XTTS path, Sarvam path, IndicTrans2 path, disabled IndicF5 roadmap, no generic fallback policy.

6. `/backends`
   - Cards for XTTS, IndicTrans2, Sarvam, IndicF5 disabled/local experimental, FFmpeg/Lipsync.
   - Supported language grouping.

## Components To Create Or Update

Create under `NEW_Frontend/components/vidiolingua`:

```text
site-navigation.tsx
site-footer.tsx
hero-section.tsx
workflow-section.tsx
demo-showcase.tsx
backend-router-section.tsx
language-support-section.tsx
quality-section.tsx
cta-section.tsx
language-selector.tsx
pipeline-timeline.tsx
result-video-card.tsx
architecture-flow.tsx
backend-card.tsx
```

Create under `NEW_Frontend/lib`:

```text
api.ts
language-capabilities.ts
pipeline-storage.ts
types.ts
```

Update:

```text
app/layout.tsx
app/page.tsx
app/globals.css
```

Add:

```text
app/upload/page.tsx
app/pipeline/page.tsx
app/results/page.tsx
app/architecture/page.tsx
app/backends/page.tsx
.env.example
```

## Language And Backend UX Rules

XTTS supported languages:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh
```

UX:

- Label: `XTTS speaker-reference voice`.
- Reference audio is required/recommended for speaker-reference dubbing.
- Copy: "Uses your reference audio to preserve speaker style where supported."

Sarvam managed Indian-language TTS:

```text
hi, ta, bn, te, kn, ml, mr, gu, pa, or, od
```

UX:

- Label: `Sarvam managed Indian-language voice`.
- Copy: "Natural regional-language speech through Sarvam AI. Not exact speaker cloning."
- Reference audio is optional from the UI point of view and should not be presented as required for Sarvam.

IndicF5:

- Show only as disabled/local experimental roadmap.
- Do not make it the active default.
- Do not run local IndicF5.

Forbidden/blocked:

- No generic TTS fallback in UI.
- No Indic Parler user-facing feature claim.
- Do not claim Hindi/Kannada uses XTTS.
- Do not claim Sarvam is exact cloning.

## Backend Allowlist Risk And Fix

`backend/main.py` currently accepts only:

```text
hi, es, fr, de, ja, zh, ar, pt
```

This blocks Kannada and most Sarvam regional languages through `POST /api/upload`.

Tiny safe fix if still present:

- Expand the upload allowlist to:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh,
hi, ta, bn, te, kn, ml, mr, gu, pa, or, od
```

- Expand the display-name `code_map`.
- Do not change translation or TTS routing logic.

## API Integration Plan

Implement `lib/api.ts`:

- `API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`
- `uploadVideo({ video, targetLanguage, sourceLanguage, voiceMode, voiceSample })`
- `getJobStatus(jobId)`
- `getResult(jobId)`
- `healthCheck()`
- `healthDeps()`
- `ttsHealth()`
- `buildResultFileUrl(jobId, filename)`

Use browser `fetch`, `FormData`, and typed response helpers.

Document future backend recommendation:

```text
GET /api/capabilities
```

The frontend will use local constants until this endpoint exists.

## Design Adaptation Plan

- Keep v0's large typographic hero, grid-line background, fixed translucent navigation, dark process band, premium border/card rhythm, animated visuals, and marquee/stat accents.
- Replace Optimus product vocabulary with Vidiolingua pipeline vocabulary.
- Use a controlled backend palette:
  - XTTS: cyan/blue accents.
  - IndicTrans2: violet/indigo accents.
  - Sarvam: green/emerald accents.
  - Disabled/experimental: amber/slate accents.
  - Media/FFmpeg: rose/orange accents.
- Preserve responsive layouts and keep upload/status/results pages visually aligned with the landing site rather than becoming a plain internal dashboard.

## Risks

- `NEW_Frontend` has no `node_modules`, so build/lint cannot run there unless dependencies are installed or reused. Do not install without approval.
- Template uses Next 16 and Tailwind 4; local environment compatibility is unknown until dependencies are installed.
- Backend jobs are in-memory, so refresh/backend restart can lose active status.
- No backend capabilities endpoint exists; frontend language constants can drift from backend routing.
- Known-good demo MP4s are protected outputs and should be referenced only as proof artifacts, not overwritten.

## Validation Commands

Frontend:

```powershell
cd NEW_Frontend
pnpm run lint
pnpm run build
```

If dependencies are missing:

```powershell
cd NEW_Frontend
pnpm install
```

Do not run install without approval.

Backend light checks:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\frontend_revamp_router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\frontend_revamp_router_fr.wav --dry-run
```

Expected:

```text
kn -> Sarvam
fr -> XTTS
```

## Files Expected To Modify

```text
NEW_Frontend/app/layout.tsx
NEW_Frontend/app/page.tsx
NEW_Frontend/app/globals.css
NEW_Frontend/app/upload/page.tsx
NEW_Frontend/app/pipeline/page.tsx
NEW_Frontend/app/results/page.tsx
NEW_Frontend/app/architecture/page.tsx
NEW_Frontend/app/backends/page.tsx
NEW_Frontend/components/vidiolingua/*
NEW_Frontend/lib/api.ts
NEW_Frontend/lib/language-capabilities.ts
NEW_Frontend/lib/pipeline-storage.ts
NEW_Frontend/lib/types.ts
NEW_Frontend/.env.example
backend/main.py
docs/FRONTEND_REVAMP_WITH_V0_DESIGN_2026-04-29.md
docs/FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md
docs/PROJECT_PIPELINE.md
docs/VOICE_BACKENDS.md
COMMAND_LOG.md
```

Backend changes should be limited to the upload language allowlist if still needed.
