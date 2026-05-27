# Prosody & Elocution Engine Report - 2026-05-05

## Summary

Added the Prosody & Elocution Engine as an additive backend/frontend layer. It analyzes source rhythm and pauses, creates TTS guidance, exposes backend-specific controls, extracts HuBERT speech representations through an isolated worker, trains a lightweight adapter, and reports prosody validation.

## Research Consulted

See `docs/PROSODY_ELOCUTION_RESEARCH_2026-05-05.md`.

## Why HuBERT Was Selected

HuBERT has a stable pretrained feature-extraction model (`facebook/hubert-base-ls960`) and is appropriate as a frozen speech representation layer. Vidiolingua uses it to compare source and dubbed speech representations.

## Why HuBERT Was Not Trained From Scratch

Training HuBERT would require large-scale unlabeled speech data and heavy compute. This project phase needs a practical, defensible component, so HuBERT remains pretrained/frozen and only a lightweight adapter is trained.

## Adapter

The adapter calibrates HuBERT cosine similarity with duration, speech-rate, energy, and pause features. With limited project data, confidence remains low.

## Schemas

- `source_prosody_profile.json`: global speech rate, pause count, average pause, energy profile, segment timing/rate/energy classes, emphasis hints, warnings/errors.
- `hubert_features.json`: model, device, embedding dimension, global embedding path, segment embedding paths, warnings/errors.
- `adapter_config.json`: adapter name/status, model type, HuBERT model, feature list, confidence.
- `training_report.json`: status, examples, limitations, validation method.
- `tts_prosody_plan.json`: preset, duration pressure, recommended pace, pause plan, backend controls, prepared text hints.
- `prosody_validation_report.json`: rate similarity, pause preservation proxy, duration drift.
- `hubert_prosody_report.json`: HuBERT similarity, adapter-calibrated score, segment similarity, limitations note.

## XTTS Controls

When the prosody engine is enabled, presets can set XTTS temperature, repetition penalty, max chunk characters, crossfade milliseconds, and punctuation-aware prepared text. Existing defaults remain when the engine is disabled.

## Sarvam Controls

Presets can set Sarvam pace, temperature, and speaker. Pace is bounded to avoid overdriving managed TTS.

## Validation Status

Validation commands were added under `tools/`.

- Backend compile: passed.
- Config inspect: passed; `.venv_prosody` detected.
- Kannada source prosody profile: computed, balanced speech rate, 0 detected ASR-gap pauses.
- HuBERT feature extraction: computed with `facebook/hubert-base-ls960`, CPU, 768-dimensional embeddings.
- Adapter training: trained ridge adapter with 2 project examples, confidence low.
- Kannada adapter validation: computed, HuBERT similarity 88.865/100, confidence low.
- Kannada prosody plan: computed, high duration pressure, Sarvam pace bounded to 1.12.
- Router dry-runs: Kannada routes to Sarvam, French routes to XTTS, no generic fallback.

A tiny real confusion matrix was added after this phase using existing HuBERT adapter artifacts only. It is a smoke-test matrix over 2 positive pairs and 2 mismatched negative pairs, threshold `85.0`: TP `2`, FP `2`, TN `0`, FN `0`. It is explicitly low confidence and not a benchmark.

Latest frontend lint/build results are recorded in `COMMAND_LOG.md`.

## Frontend Reflections

The frontend now includes Differentiators, architecture/backends references, pipeline prosody status, and results prosody summary cards.

Latest UI update:

- Differentiators page includes a real `HuBERT Adapter Evidence` section and a visual tiny confusion matrix sourced from validation artifacts.
- Results page exposes HuBERT features/status/model, adapter status/confidence, prosody similarity, embedding cosine, and confusion-matrix status when result metadata includes those fields.
- Differentiators page no longer includes the large "What this is" / "What this is not" boxes.
- Language Integrity page no longer includes the large "What it is not" box; the roadmap is presented as a balanced full-width section.
- Navbar spacing was fixed with priority navigation and a More dropdown without removing sticky/glass transitions.
- Footer now mentions Techgium and L&T Technology Services.

## Remaining Roadmap

- Larger paired training dataset.
- WavLM comparison.
- Dedicated F0/pitch model.
- Emotion classifier.
- SyncNet/LSE integration.
- Learned prosody encoder.
- Human review workflow.
- User-selectable expressive styles.
