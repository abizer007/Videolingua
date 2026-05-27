# Frontend Revamp With v0 Design - 2026-04-29

## Summary

The v0 Optimus template in `NEW_Frontend` was adapted into a Vidiolingua-specific Next.js app. The revamp keeps the template's premium AI platform feel, large typography, animated hero visual, dark process sections, premium cards, and strong CTA rhythm, while replacing the public-facing experience with Vidiolingua pipeline, model routing, language support, and backend integration content.

Primary frontend path:

```text
NEW_Frontend
```

`frontend-next` was inspected as the integration reference and was not destroyed or migrated over.

## Pages Implemented

```text
/
/upload
/pipeline
/results
/architecture
/backends
```

## Components Created Or Updated

Created:

```text
NEW_Frontend/components/vidiolingua/site-navigation.tsx
NEW_Frontend/components/vidiolingua/site-footer.tsx
NEW_Frontend/components/vidiolingua/hero-section.tsx
NEW_Frontend/components/vidiolingua/workflow-section.tsx
NEW_Frontend/components/vidiolingua/demo-showcase.tsx
NEW_Frontend/components/vidiolingua/backend-router-section.tsx
NEW_Frontend/components/vidiolingua/language-support-section.tsx
NEW_Frontend/components/vidiolingua/quality-section.tsx
NEW_Frontend/components/vidiolingua/cta-section.tsx
NEW_Frontend/components/vidiolingua/language-selector.tsx
NEW_Frontend/components/vidiolingua/pipeline-timeline.tsx
NEW_Frontend/components/vidiolingua/result-video-card.tsx
NEW_Frontend/components/vidiolingua/architecture-flow.tsx
NEW_Frontend/components/vidiolingua/backend-card.tsx
```

Updated:

```text
NEW_Frontend/app/layout.tsx
NEW_Frontend/app/page.tsx
NEW_Frontend/app/globals.css
```

## API Integration

Created:

```text
NEW_Frontend/lib/api.ts
NEW_Frontend/lib/types.ts
NEW_Frontend/lib/language-capabilities.ts
NEW_Frontend/lib/pipeline-storage.ts
NEW_Frontend/.env.example
```

The frontend API client uses browser `fetch` and `FormData`.

Endpoints used:

```text
POST /api/upload
GET /api/job-status/{job_id}
GET /api/result/{job_id}
GET /api/health
GET /api/health/deps
GET /api/tts-health
```

Frontend env:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

No Sarvam key or other backend secret was added to frontend code or frontend env.

## Language And Voice UX

XTTS cloned/speaker-reference languages:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh
```

UI label:

```text
XTTS speaker-reference voice
```

Sarvam managed Indian-language TTS languages:

```text
hi, ta, bn, te, kn, ml, mr, gu, pa, or, od
```

UI label:

```text
Sarvam managed Indian-language voice
```

Sarvam copy explicitly says it is natural managed regional speech and not exact speaker cloning. Reference audio is required in the UI for XTTS routes and optional for Sarvam routes.

IndicF5 appears only as disabled/local experimental roadmap copy. It is not presented as an active default.

## Content Customization

The landing page now includes:

- Hero positioning: "Translate and dub videos across global and Indian languages".
- ASR, translation, voice generation, validation, and mux pipeline copy.
- French XTTS proof card.
- Kannada IndicTrans2 + Sarvam proof card.
- Backend router cards for XTTS, IndicTrans2, Sarvam AI, IndicF5, and FFmpeg/Lipsync.
- Supported language groups for XTTS and Sarvam.
- Quality/security section covering backend-only secrets, strict routing, auditable stages, and local/managed split.
- CTA into `/upload`.

## Backend Allowlist Change

`backend/main.py` upload validation was updated to accept:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh,
hi, ta, bn, te, kn, ml, mr, gu, pa, or, od
```

This was limited to upload language allowlist and display-name mapping. Translation and TTS routing logic was not changed.

## Validation Results

Frontend dependency check:

```powershell
Test-Path node_modules
```

Result in `NEW_Frontend`:

```text
False
```

Frontend lint/build were not run because `NEW_Frontend/node_modules` is missing and dependencies were not installed. Install command needed before frontend validation:

```powershell
cd NEW_Frontend
pnpm install
pnpm run lint
pnpm run build
```

Backend compile:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts
```

Result:

```text
passed
```

Pipeline config inspect:

```powershell
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
```

Result:

```text
passed
```

Kannada router dry-run:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --target-language kn --cloning-required true --dry-run
```

Result:

```text
selected_engine=sarvam
managed_tts=true
exact_voice_clone=false
xtts_used=false
indicf5_used=false
```

French router dry-run:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --target-language fr --cloning-required true --dry-run
```

Result:

```text
selected_engine=xtts
xtts_used=true
sarvam_used=false
indicf5_used=false
```

## Remaining Issues Before Frontend Demo

- Run `pnpm install` in `NEW_Frontend` with approval, then run `pnpm run lint` and `pnpm run build`.
- Start the backend and frontend together for browser QA.
- Add a future backend `GET /api/capabilities` endpoint so supported-language metadata does not live only in frontend constants.
- Consider persisting job state server-side; current backend job store is in-memory.

## Safety Confirmation

- No secrets exposed.
- No Sarvam key added to frontend.
- No dependency installs run.
- No venv mutations.
- No full video pipeline run.
- No local IndicF5 load or generation.
- `models\xtts_v2` untouched.
- `outputs\french_official_test` untouched.
- `outputs\kannada_sarvam_practical_test_clipfix` untouched.
