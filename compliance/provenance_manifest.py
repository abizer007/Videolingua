"""C2PA-style sidecar provenance manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance.fingerprinting import sha256_file
from compliance.schemas import DISCLOSURE_TEXT, new_id, probe_duration, write_json, utc_now


def generate_provenance_manifest(
    *,
    output_path: str | Path,
    asset_id: str | None,
    job_id: str,
    input_video_path: str | Path | None,
    output_video_path: str | Path | None,
    pipeline: dict[str, Any],
    reports: dict[str, str | None],
    disclosure: str = DISCLOSURE_TEXT,
) -> dict[str, Any]:
    manifest = {
        "provenance_manifest_id": new_id("provenance"),
        "created_at": utc_now(),
        "asset_id": asset_id or new_id("asset"),
        "job_id": job_id,
        "synthetic_media": True,
        "disclosure": disclosure,
        "input": {
            "path": str(input_video_path) if input_video_path else None,
            "sha256": sha256_file(input_video_path),
            "duration_sec": probe_duration(input_video_path),
        },
        "output": {
            "path": str(output_video_path) if output_video_path else None,
            "sha256": sha256_file(output_video_path),
            "duration_sec": probe_duration(output_video_path),
        },
        "pipeline": pipeline,
        "reports": reports,
        "c2pa_status": "sidecar_only_not_signed",
        "warnings": [],
        "limitations": [
            "This is a C2PA-style sidecar and is not a signed C2PA manifest.",
            "Metadata can be stripped by downstream processing.",
        ],
    }
    if not manifest["output"]["sha256"]:
        manifest["warnings"].append("Output hash is unavailable because final output was not found.")
    write_json(output_path, manifest)
    return manifest
