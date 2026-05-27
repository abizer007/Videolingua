"""Append-only JSONL audit ledger for responsible AI events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from compliance.fingerprinting import sha256_file
from compliance.schemas import new_id, utc_now


def ledger_path(compliance_dir: str | Path) -> Path:
    return Path(compliance_dir) / "audit_ledger.jsonl"


def append_event(
    *,
    compliance_dir: str | Path,
    job_id: str,
    event_type: str,
    summary: str,
    artifact_path: str | Path | None = None,
    include_hash: bool = True,
) -> dict[str, Any]:
    event = {
        "event_id": new_id("audit_event"),
        "timestamp": utc_now(),
        "job_id": job_id,
        "event_type": event_type,
        "summary": summary,
        "artifact_path": str(artifact_path) if artifact_path else None,
    }
    if include_hash and artifact_path:
        digest = sha256_file(artifact_path)
        if digest:
            event["sha256"] = digest
    target = ledger_path(compliance_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event
