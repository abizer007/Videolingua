# HuBERT Frontend Metrics Exposure - 2026-05-05

## Purpose

This note records the frontend pass that exposes real HuBERT-guided Prosody Adapter evidence and fixes the screenshot-driven UI polish items.

## Artifact Values Shown

The Differentiators page now shows values read from existing validation artifacts:

- HuBERT model: `facebook/hubert-base-ls960`.
- Feature extraction status: `computed`.
- Device: `cpu`.
- Embedding dimension: `768`.
- Adapter model type: `ridge`.
- Training examples: `2`.
- Attempted jobs: `2`.
- Adapter confidence: `low`.
- Kannada validation status: `computed`.
- Kannada prosody similarity: `88.865 / 100`.
- Kannada embedding cosine similarity: `0.917243`.
- Kannada validation warnings: none in the report.
- Confusion matrix threshold: `85.0`.
- Confusion matrix dataset size: `4` pairs.
- Confusion matrix: TP `2`, FP `2`, TN `0`, FN `0`.
- Matrix metrics: accuracy `50.0%`, precision `50.0%`, recall `100.0%`, specificity `0.0%`.

## What Is Not Claimed

- HuBERT was not trained from scratch.
- The adapter is not presented as a large benchmark model.
- The Kannada score is not presented as perfect prosody or emotion transfer.
- No confusion matrix was fabricated; the displayed matrix is generated from existing HuBERT adapter artifacts and explicitly marked as tiny/low-confidence.
- No model weights, embeddings, secrets, or Sarvam credentials are exposed in frontend code.

## Confusion Matrix Status

No real confusion matrix existed at the start of this frontend pass. Searches for `confusion_matrix`, `true_positive`, `false_positive`, `true_negative`, `false_negative`, `classification_report`, labels, and matched/mismatched pair reports did not find a classifier-style matrix.

A tiny real matrix was then generated with `tools.evaluate_hubert_adapter_matrix` from existing saved HuBERT embeddings and the trained adapter. Positives are correct source/dub project pairs. Negatives are mismatched source/dub project pairs. The default threshold is `85.0` because positive and negative scores are not cleanly separated.

Result:

- TP: `2`
- FP: `2`
- TN: `0`
- FN: `0`

This is shown as a smoke-test matrix, not a benchmark. The false positives are intentionally visible because they show that the current adapter is not a reliable classifier yet.

## Results Page Reflection

`NEW_Frontend/app/results/page.tsx` exposes live HuBERT/prosody metadata when present in the API result or metrics report:

- HuBERT features computed.
- HuBERT status.
- HuBERT model.
- HuBERT prosody similarity.
- HuBERT embedding cosine.
- Adapter status.
- Adapter confidence.
- Confusion matrix status or static artifact summary.
- Low-confidence note when adapter confidence is `low`.

If live API metadata is absent, no live value is invented; the static artifact evidence remains on the Differentiators page.

## UI Polish Summary

- Navbar spacing was fixed with priority navigation: six primary desktop links plus a polished `More` dropdown for Languages, Architecture, and Results.
- All visible Differentiators grid cards now show `Implemented`.
- The Differentiators page "What this is" and "What this is not" boxes were removed.
- The Language Integrity page "What it is not" box was removed and the Roadmap section was balanced as a full-width card.
- The footer now states that Vidiolingua is a Techgium proof-of-concept and includes `L&T Technology Services`.

## Validation

Latest lint/build outcomes are recorded in `COMMAND_LOG.md`.
