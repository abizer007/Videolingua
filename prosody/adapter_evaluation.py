"""Tiny HuBERT adapter evaluation matrix from existing project artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prosody.adapter_model import cosine_similarity, load_adapter
from prosody.adapter_train import _duration_similarity, _load_embedding, _scalar_similarity
from voice.hubert_prosody import DEFAULT_MODEL
from voice.speech_rate import rate_similarity


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _global(profile: dict[str, Any]) -> dict[str, Any]:
    value = profile.get("global")
    return value if isinstance(value, dict) else {}


def _embedding_path(features: dict[str, Any]) -> str | None:
    value = features.get("global_embedding_path")
    return str(value) if value else None


def _score_pair(adapter, source: dict[str, Any], dub: dict[str, Any]) -> tuple[dict[str, float | None], float]:
    source_emb = _load_embedding(_embedding_path(source["source_hubert"]))
    dub_emb = _load_embedding(_embedding_path(dub["dub_hubert"]))
    source_global = _global(source["source_profile"])
    dub_global = _global(dub["dub_profile"])
    features = {
        "embedding_cosine": cosine_similarity(source_emb, dub_emb) if source_emb is not None and dub_emb is not None else None,
        "duration_similarity": _duration_similarity(source_global.get("speech_duration_sec"), dub_global.get("speech_duration_sec")),
        "speech_rate_similarity": rate_similarity(source_global.get("speech_rate_wpm"), dub_global.get("speech_rate_wpm")),
        "energy_similarity": _scalar_similarity(source_global.get("average_energy_rms"), dub_global.get("average_energy_rms")),
        "pause_similarity": _scalar_similarity(source_global.get("pause_count"), dub_global.get("pause_count")),
    }
    return features, adapter.predict_score(features)


def _load_ready_pairs(adapter_dir: Path, training_report: dict[str, Any]) -> list[dict[str, Any]]:
    ready: list[dict[str, Any]] = []
    for example in training_report.get("examples") or []:
        if not isinstance(example, dict) or example.get("status") != "ready":
            continue
        job_name = Path(str(example.get("job_dir") or "")).name
        if not job_name:
            continue
        feature_dir = adapter_dir / "training_features" / job_name
        source_hubert = _read_json(feature_dir / "source_hubert" / "hubert_features.json") or example.get("source_hubert") or {}
        dub_hubert = _read_json(feature_dir / "dub_hubert" / "hubert_features.json") or example.get("dub_hubert") or {}
        source_profile = _read_json(feature_dir / "source_prosody_profile.json")
        dub_profile = _read_json(feature_dir / "dub_prosody_profile.json")
        if source_hubert.get("status") != "computed" or dub_hubert.get("status") != "computed":
            continue
        ready.append(
            {
                "job_id": job_name,
                "source_hubert": source_hubert,
                "dub_hubert": dub_hubert,
                "source_profile": source_profile,
                "dub_profile": dub_profile,
            }
        )
    return ready


def build_hubert_adapter_confusion_matrix(
    adapter_dir: str | Path,
    output_path: str | Path,
    *,
    model_name: str = DEFAULT_MODEL,
    threshold: float | None = None,
) -> dict[str, Any]:
    adapter_root = Path(adapter_dir)
    output = Path(output_path)
    training_report = _read_json(adapter_root / "training_report.json")
    adapter = load_adapter(adapter_root)
    pairs = _load_ready_pairs(adapter_root, training_report)
    warnings: list[str] = []
    samples: list[dict[str, Any]] = []

    for item in pairs:
        features, score = _score_pair(adapter, item, item)
        samples.append(
            {
                "pair_type": "positive",
                "source_job": item["job_id"],
                "dub_job": item["job_id"],
                "true_label": 1,
                "score_0_100": score,
                "features": {key: round(value, 6) if isinstance(value, float) else value for key, value in features.items()},
            }
        )

    for source in pairs:
        for dub in pairs:
            if source["job_id"] == dub["job_id"]:
                continue
            features, score = _score_pair(adapter, source, dub)
            samples.append(
                {
                    "pair_type": "negative_mismatch",
                    "source_job": source["job_id"],
                    "dub_job": dub["job_id"],
                    "true_label": 0,
                    "score_0_100": score,
                    "features": {key: round(value, 6) if isinstance(value, float) else value for key, value in features.items()},
                }
            )

    positives = [sample["score_0_100"] for sample in samples if sample["true_label"] == 1]
    negatives = [sample["score_0_100"] for sample in samples if sample["true_label"] == 0]
    threshold_method = "manual"
    if threshold is None:
        if positives and negatives and min(positives) > max(negatives):
            threshold = round((min(positives) + max(negatives)) / 2.0, 3)
            threshold_method = "midpoint_between_lowest_positive_and_highest_negative"
        else:
            threshold = 85.0
            threshold_method = "default_similarity_threshold"
            warnings.append("Positive and negative scores are not cleanly separated; default 85.0 threshold used.")

    tp = fp = tn = fn = 0
    for sample in samples:
        predicted = 1 if float(sample["score_0_100"]) >= float(threshold) else 0
        sample["predicted_label"] = predicted
        sample["prediction"] = "match" if predicted else "mismatch"
        if sample["true_label"] == 1 and predicted == 1:
            tp += 1
        elif sample["true_label"] == 0 and predicted == 1:
            fp += 1
        elif sample["true_label"] == 0 and predicted == 0:
            tn += 1
        else:
            fn += 1

    total = len(samples)
    accuracy = round((tp + tn) / total, 6) if total else None
    precision = round(tp / (tp + fp), 6) if (tp + fp) else None
    recall = round(tp / (tp + fn), 6) if (tp + fn) else None
    specificity = round(tn / (tn + fp), 6) if (tn + fp) else None
    if total < 20:
        warnings.append("Tiny project-only evaluation set; treat this as a smoke-test matrix, not a benchmark.")
    if len(pairs) < 2:
        warnings.append("At least two paired jobs are required to create mismatch negatives.")

    report = {
        "schema_version": 1,
        "status": "computed" if samples and positives and negatives else "insufficient_data",
        "hubert_model": model_name,
        "adapter_path": str(adapter_root),
        "adapter_status": adapter.status,
        "confidence": "low",
        "evaluation_type": "tiny_project_pair_matrix",
        "threshold": threshold,
        "threshold_method": threshold_method,
        "dataset": {
            "paired_jobs": len(pairs),
            "positive_pairs": len(positives),
            "negative_pairs": len(negatives),
            "total_pairs": total,
            "positive_definition": "source/reference audio paired with its correct dubbed output",
            "negative_definition": "source/reference audio paired with a mismatched job dubbed output",
        },
        "matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
        },
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
        },
        "samples": samples,
        "warnings": warnings,
        "limitations": [
            "Uses existing project HuBERT embeddings and adapter scores only.",
            "Negative pairs are mismatched project jobs, not a large labeled corpus.",
            "This matrix does not prove general prosody or emotion transfer.",
        ],
        "note": "Classifier-style matrix over a tiny set of labeled positive and mismatch pairs; HuBERT remains frozen and was not trained from scratch.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
