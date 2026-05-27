"""Shared metric result helpers and evaluator stubs."""

from __future__ import annotations

from typing import Any


def computed(value: Any, **extra: Any) -> dict[str, Any]:
    result = {"status": "computed", "value": value}
    result.update(extra)
    return result


def unavailable(status: str, reason: str | None = None, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status}
    if reason:
        result["reason"] = reason
    result.update(extra)
    return result


def error_result(message: str) -> dict[str, Any]:
    return {"status": "error", "reason": message}


def advanced_evaluator_status(*, human_mos_rating: float | None = None, human_quality_notes: str | None = None) -> dict[str, Any]:
    mos = (
        computed(
            round(float(human_mos_rating), 3),
            source="human_rating",
            notes=human_quality_notes or None,
        )
        if human_mos_rating is not None
        else unavailable("evaluator_not_installed", "No MOS evaluator or human rating was provided.")
    )
    return {
        "mos": mos,
        "lse_c": unavailable("evaluator_not_installed", "No lip-sync evaluator is installed."),
        "lse_d": unavailable("evaluator_not_installed", "No lip-sync evaluator is installed."),
        "voice_similarity": unavailable(
            "evaluator_not_installed",
            "No speaker embedding evaluator is installed.",
        ),
    }

