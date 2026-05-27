# HuBERT Prosody Adapter Training - 2026-05-05

## What Is Trained

The trained component is a lightweight calibration adapter on top of frozen pretrained HuBERT embeddings. It uses:

- HuBERT global embedding cosine similarity.
- Duration similarity.
- Speech-rate similarity.
- Energy similarity.
- Pause-count similarity.

The adapter is ridge regression when at least two ready examples are available; otherwise it writes a baseline calibration model and reports insufficient data.

## What Is Not Trained

- HuBERT is not trained from scratch.
- No full cross-lingual prosody transfer model is trained.
- No exact emotion or speaker cloning model is trained.

## Artifact Location

`models/prosody_hubert_adapter/`

This path is ignored by `.gitignore` through the existing `models/` rule. Do not commit trained weights.

## Training Command

```powershell
.\.venv_api\Scripts\python.exe -m tools.train_hubert_prosody_adapter --training-jobs outputs\french_official_test outputs\kannada_sarvam_practical_test_clipfix --output-dir models\prosody_hubert_adapter
```

The command delegates to `.venv_prosody` when that isolated environment exists.

## Confidence

Expected confidence is low until a larger set of paired source/dub examples exists. The report is useful for calibration and inspection, not universal prosody transfer.

## Current Training Result

The adapter training command completed with:

- status: `trained`
- model type: `ridge`
- training examples: `2`
- attempted jobs: `2`
- HuBERT model: `facebook/hubert-base-ls960`
- HuBERT feature extraction device in validation artifact: `cpu`
- HuBERT embedding dimension in validation artifact: `768`
- confidence: `low`

Kannada validation produced:

- status: `computed`
- HuBERT-guided prosody similarity score: `88.865 / 100`
- embedding cosine similarity: `0.917243`
- confidence: `low`
- warning count: `0`

## Confusion Matrix Status

No real confusion matrix existed in the adapter artifacts before this follow-up. Searches for classifier outputs such as `confusion_matrix`, `true_positive`, `false_positive`, `true_negative`, `false_negative`, `classification_report`, labels, and matched/mismatched pair reports did not find an evaluation matrix.

Added `tools.evaluate_hubert_adapter_matrix` and `prosody.adapter_evaluation` to build a tiny real matrix from existing project artifacts only:

- Positive pairs: source/reference audio paired with its correct dubbed output.
- Negative pairs: source/reference audio paired with a mismatched project dubbed output.
- Threshold: `85.0`.
- Dataset size: `4` pairs.
- TP: `2`
- FP: `2`
- TN: `0`
- FN: `0`
- Accuracy: `0.5`
- Precision: `0.5`
- Recall: `1.0`
- Specificity: `0.0`

The result is written to `outputs/validation/hubert_adapter_confusion_matrix.json`. It is marked low confidence and tiny project-only smoke-test evidence, not a large benchmark. The false positives are intentionally exposed because the current adapter is not yet a reliable classifier.

## Frontend Exposure

`NEW_Frontend/app/differentiators/page.tsx` now shows the real HuBERT model, embedding dimension, device, extraction status, adapter type, training count, confidence, Kannada validation score, cosine similarity, limitations, and the tiny matrix. It also states that pretrained HuBERT was used as a frozen feature extractor and was not trained from scratch.
