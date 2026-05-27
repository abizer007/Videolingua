# Cost Analysis Frontend Integration Plan

Date prepared: 2026-05-05
Requested filename date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Standalone Files Found

| File | Status | Decision |
| --- | --- | --- |
| `assets/cost_financial_analysis.html` | Present | Superseded by the integrated Next.js page. Useful only as audit context. |
| `assets/cost_financial_analysis.png` | Present | Superseded. Must not be used as page content. |
| `docs/cost_financial_analysis_notes.md` | Present | Partially useful for identifying earlier assumptions, but several vendor values needed fresh source checks. |
| `cost_financial_analysis.html` | Not found at repo root | Add to `.gitignore` to prevent future standalone report commits. |
| `cost_financial_analysis.png` | Not found at repo root | Add to `.gitignore` to prevent future standalone report commits. |

## Reuse

- Reuse the high-level framing that Vidiolingua cost is driven by media processing, ASR, translation, TTS, validation, and review.
- Reuse repo-backed facts only after validating against local artifacts and metrics reports.
- Reuse the caution that cloud GPU throughput is an assumption until benchmarked on the actual stack.

## Discard Or Ignore

- Do not reuse the standalone slide layout, dark table treatment, or fixed 1600x900 report design.
- Do not use `assets/cost_financial_analysis.png` as content.
- Do not copy any values from external screenshots.
- Do not present old vendor estimates as measured facts.

## Frontend Route

Route created:

`NEW_Frontend\app\economics\page.tsx`

Navigation label:

`Economics`

This route was chosen because the page covers cost, backend routing economics, validation evidence, and evaluation framing rather than only a static cost table.

## Components And Data

- `NEW_Frontend\app\economics\page.tsx` implements the native page.
- `NEW_Frontend\lib\cost-analysis-data.ts` stores source-backed measured and external values with source labels, URLs, access dates, evidence kind, and confidence.
- Existing `SiteNavigation`, `SiteFooter`, `Button`, typography, card borders, spacing, and editorial grid patterns are reused.

## Content Revisions

- Cost formula is shown as a native card grid.
- Backend economics matrix covers XTTS, IndicTrans2, Sarvam, IndicF5, and FFmpeg/mux.
- Validated run evidence uses French and Kannada artifacts from protected output folders.
- Pricing sources are labeled as external planning data, not measured Vidiolingua cost.
- Evaluation metrics are split into automatically computed metrics and optional reference/evaluator metrics.
- Risk and guardrail analysis includes no silent fallback, backend-only secrets, audio validation, no generic TTS fallback, and disabled local IndicF5.

## Allowed Assumptions

- Provider prices may be shown only as source-backed external references with access date and update warnings.
- Future cloud GPU economics may be discussed only as planning context until Vidiolingua has measured hosted throughput.
- Manual localization prices may be shown as market comparison, not a Vidiolingua savings claim.

## Validation Plan

- Run `corepack pnpm run lint` in `NEW_Frontend`.
- Run `corepack pnpm run build` in `NEW_Frontend`.
- Run backend compile validation for `backend app asr translation tts voice workers tools evaluation`.
- Run metrics report validation on the two known output jobs without changing protected MP4 files.
- Run voice-router dry runs only; do not run full pipeline and do not load local IndicF5.
