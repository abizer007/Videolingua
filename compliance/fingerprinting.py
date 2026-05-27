"""SHA-256 and basic media fingerprint sidecars."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from compliance.schemas import new_id, probe_duration, utc_now, write_json


def sha256_file(path: str | Path | None) -> str | None:
    if not path:
        return None
    target = Path(path)
    if not target.is_file():
        return None
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def file_size(path: str | Path | None) -> int | None:
    if not path:
        return None
    try:
        target = Path(path)
        return target.stat().st_size if target.is_file() else None
    except OSError:
        return None


def generate_fingerprint_report(
    *,
    job_id: str,
    output_path: Path,
    input_video_path: str | Path | None,
    output_video_path: str | Path | None,
    audio_path: str | Path | None = None,
    provenance_manifest_path: str | Path | None = None,
    job_manifest_id: str | None = None,
) -> dict[str, Any]:
    report = {
        "fingerprint_id": new_id("fingerprint"),
        "created_at": utc_now(),
        "job_id": job_id,
        "input_video_sha256": sha256_file(input_video_path),
        "output_video_sha256": sha256_file(output_video_path),
        "audio_sha256": sha256_file(audio_path),
        "provenance_manifest_sha256": sha256_file(provenance_manifest_path),
        "job_manifest_id": job_manifest_id,
        "file_size_bytes": file_size(output_video_path),
        "input_file_size_bytes": file_size(input_video_path),
        "audio_file_size_bytes": file_size(audio_path),
        "duration_sec": probe_duration(output_video_path),
        "input_duration_sec": probe_duration(input_video_path),
        "audio_duration_sec": probe_duration(audio_path),
        "perceptual_video_hash": {
            "status": "not_available_without_dependency",
        },
        "audio_fingerprint": {
            "status": "not_available_without_dependency",
        },
        "warnings": [],
        "errors": [],
    }
    if not report["output_video_sha256"]:
        report["warnings"].append("Output video hash is unavailable because no final output path was found.")
    write_json(output_path, report)
    return report
