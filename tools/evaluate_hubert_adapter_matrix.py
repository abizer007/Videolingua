"""Create a tiny HuBERT adapter confusion matrix from existing artifacts."""

from __future__ import annotations

import argparse
import json

from prosody.adapter_evaluation import build_hubert_adapter_confusion_matrix
from voice.hubert_prosody import DEFAULT_MODEL


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the HuBERT prosody adapter as a tiny positive/negative pair matrix.")
    parser.add_argument("--adapter-dir", default="models/prosody_hubert_adapter")
    parser.add_argument("--output", default="outputs/validation/hubert_adapter_confusion_matrix.json")
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()
    report = build_hubert_adapter_confusion_matrix(
        args.adapter_dir,
        args.output,
        model_name=args.model_name,
        threshold=args.threshold,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("status") == "computed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
