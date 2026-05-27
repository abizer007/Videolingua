"""Shared schema helpers for automatic quality reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


Metric = dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def metric(
    *,
    status: str,
    value: Any = None,
    unit: str,
    method: str,
    confidence: str,
    source: str,
    explanation: str,
    reference_type: str,
    details: dict[str, Any] | None = None,
) -> Metric:
    item: Metric = {
        "status": status,
        "value": value,
        "unit": unit,
        "method": method,
        "confidence": confidence,
        "source": source,
        "explanation": explanation,
        "reference_type": reference_type,
    }
    if details:
        item["details"] = details
    return item


def unavailable(method: str, explanation: str, *, source: str = "not_available") -> Metric:
    return metric(
        status="unavailable",
        value=None,
        unit="none",
        method=method,
        confidence="none",
        source=source,
        explanation=explanation,
        reference_type="unavailable",
    )


def score_to_grade(score_0_100: float) -> str:
    if score_0_100 >= 85.0:
        return "Excellent"
    if score_0_100 >= 70.0:
        return "Good"
    if score_0_100 >= 45.0:
        return "Needs review"
    return "Failed"


def confidence_rank(confidence: str) -> int:
    return {"none": 0, "low": 1, "medium": 2, "high": 3}.get(str(confidence), 1)


def confidence_from_ranks(values: list[str]) -> str:
    ranks = [confidence_rank(value) for value in values if value and value != "none"]
    if not ranks:
        return "low"
    avg = sum(ranks) / len(ranks)
    if avg >= 2.65:
        return "high"
    if avg >= 1.75:
        return "medium"
    return "low"
