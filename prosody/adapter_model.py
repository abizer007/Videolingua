"""Lightweight HuBERT prosody adapter model.

This is a calibration layer on top of frozen HuBERT embeddings and handcrafted
prosody features. It is not a trained HuBERT model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FEATURE_NAMES = [
    "embedding_cosine",
    "duration_similarity",
    "speech_rate_similarity",
    "energy_similarity",
    "pause_similarity",
]


def cosine_similarity(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype="float32")
    b = np.asarray(b, dtype="float32")
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def baseline_score(features: dict[str, float | None]) -> float:
    weights = {
        "embedding_cosine": 0.38,
        "duration_similarity": 0.22,
        "speech_rate_similarity": 0.18,
        "energy_similarity": 0.12,
        "pause_similarity": 0.10,
    }
    total = 0.0
    used = 0.0
    for key, weight in weights.items():
        value = features.get(key)
        if value is None:
            continue
        total += clamp01((float(value) + 1.0) / 2.0 if key == "embedding_cosine" else float(value)) * weight
        used += weight
    if used <= 0:
        return 0.0
    return clamp01(total / used)


def feature_vector(features: dict[str, float | None]):
    import numpy as np

    values = []
    for name in FEATURE_NAMES:
        value = features.get(name)
        if value is None:
            value = 0.5 if name != "embedding_cosine" else 0.0
        if name == "embedding_cosine":
            value = (float(value) + 1.0) / 2.0
        values.append(clamp01(float(value)))
    return np.asarray(values, dtype="float32")


class ProsodyAdapter:
    def __init__(self, weights=None, bias: float = 0.0, *, status: str = "missing", confidence: str = "low") -> None:
        self.weights = weights
        self.bias = float(bias)
        self.status = status
        self.confidence = confidence

    def predict01(self, features: dict[str, float | None]) -> float:
        if self.weights is None:
            return baseline_score(features)
        import numpy as np

        x = feature_vector(features)
        value = float(np.dot(self.weights, x) + self.bias)
        return clamp01(value)

    def predict_score(self, features: dict[str, float | None]) -> float:
        return round(self.predict01(features) * 100.0, 3)


def save_adapter(output_dir: str | Path, weights, bias: float, config: dict[str, Any]) -> None:
    import numpy as np

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    np.savez(output / "adapter_weights.npz", weights=weights, bias=float(bias))
    (output / "adapter_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def load_adapter(adapter_dir: str | Path) -> ProsodyAdapter:
    import numpy as np

    root = Path(adapter_dir)
    config_path = root / "adapter_config.json"
    weights_path = root / "adapter_weights.npz"
    if not config_path.is_file() or not weights_path.is_file():
        return ProsodyAdapter(status="missing", confidence="low")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    data = np.load(weights_path)
    return ProsodyAdapter(data["weights"], float(data["bias"]), status=config.get("adapter_status", "trained"), confidence=config.get("confidence", "low"))
