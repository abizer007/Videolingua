# Differentiators Page Report - 2026-05-05

## Route

`NEW_Frontend/app/differentiators/page.tsx`

## Sections Added

- Hero section.
- Differentiator index.
- HuBERT-guided Prosody & Elocution Engine deep dive.
- Research-backed "Why HuBERT?" citation cards.
- Architecture flow.
- Backend artifacts.
- Artifact-backed HuBERT Adapter Evidence panel.
- Evidence/validation honesty panel.
- Expandable roadmap slots.

## Differentiators Listed

All visible differentiator grid cards now show `Implemented` for this UI pass:

- HuBERT-guided Prosody & Elocution Engine.
- Job manifest orchestration.
- Multilingual / OTT export.
- Translation QA and context integrity.
- Linguistic and phonetic integrity.
- Automatic evaluation metrics.
- Resume/retry execution.
- C2PA / provenance.

The expandable roadmap slots remain present below the evidence sections.

## Research Citations

See `docs/DIFFERENTIATORS_RESEARCH_SOURCES_2026-05-05.md`.

## Backend Artifacts Shown

The page lists `source_prosody_profile.json`, `tts_prosody_plan.json`, HuBERT feature metadata, `hubert_prosody_report.json`, `prosody_validation_report.json`, adapter training report, manifest integration, and metrics integration.

The HuBERT evidence panel now exposes only values read from local validation artifacts:

- HuBERT model: `facebook/hubert-base-ls960`.
- Embedding dimension: `768`.
- Device: `CPU`.
- Feature extraction status: `computed`.
- Adapter model type: `ridge`.
- Training examples: `2`.
- Adapter confidence: `low`.
- Kannada HuBERT-guided prosody similarity: `88.865 / 100`.
- Kannada embedding cosine: `0.917243`.
- Tiny confusion matrix: TP `2`, FP `2`, TN `0`, FN `0`, threshold `85.0`, dataset size `4`.

## Honesty Notes

The page explicitly states that HuBERT is pretrained/frozen, HuBERT is not trained from scratch, the adapter is lightweight, confidence is low with small data, and the Kannada score is HuBERT-guided prosody similarity, not perfect emotion transfer.

A tiny real confusion matrix is now shown from `outputs/validation/hubert_adapter_confusion_matrix.json`. It uses existing adapter scores only and is marked as low-confidence smoke-test evidence. It does not claim benchmark reliability.

The previous side-by-side "What this is" and "What this is not" boxes were removed from the Differentiators page. The roadmap section was preserved.

## Frontend Polish Updates

- Navbar layout now uses priority navigation: Workflow, Differentiators, Backends, Economics, OTT Export, and Language Integrity stay visible; Languages, Architecture, and Results are in a polished More dropdown. This preserves sticky/glass/animation behavior while preventing link/CTA overlap.
- Footer now identifies Vidiolingua as a Techgium proof-of-concept and includes `L&T Technology Services` in the copyright-style line.

## Validation

Latest frontend lint/build results are recorded in `COMMAND_LOG.md`.
## 2026-05-06 Responsible AI Section

Added the `Responsible AI & Provenance Engine` differentiator card and a major same-page section anchored at `#responsible-ai-provenance`.

The section covers the synthetic media problem, why Vidiolingua implemented a compliance-readiness layer, verified source cards, defense-in-depth architecture, generated backend artifacts, a compliance passport preview from validation output, "what this is / is not", and roadmap items.

No separate page was created. Copy avoids legal certification, C2PA certification, tamper-proof watermarking, complete misuse prevention, and legal-advice claims.
