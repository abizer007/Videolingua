"""Retention metadata for job artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance.schemas import delete_after_iso, env_int, new_id, utc_now, write_json


def generate_retention_policy(
    *,
    output_path: str | Path,
    retention_days: int | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    days = int(retention_days if retention_days is not None else env_int("VIDIOLINGUA_RETENTION_DAYS", 30))
    policy = {
        "retention_policy_id": new_id("retention"),
        "retention_days": days,
        "created_at": utc_now(),
        "delete_after": delete_after_iso(days),
        "applies_to": [
            "input_video",
            "reference_audio",
            "generated_audio",
            "final_video",
            "logs",
            "reports",
        ],
        "withdrawal_supported": True,
        "deletion_not_implemented_yet": True,
        "notes": notes or [],
    }
    write_json(output_path, policy)
    return policy
