"""Validate job lifecycle cleanup without running the video pipeline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from backend import job_manifest, job_store
from backend.main import NO_CACHE_HEADERS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assert(condition: bool, message: str) -> dict[str, Any]:
    return {"ok": bool(condition), "message": message}


def validate_job_terminal_state(work_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    job_id = "validation-job-lifecycle-cleanup"
    input_video = work_dir / "input_video.mp4"
    input_video.write_bytes(b"mock video placeholder")
    job_store.create_job(job_id, str(input_video), ["kn"], source_language="en")
    job_store.update_job(job_id, stage="translation", progress=35)
    job_store.mark_job_terminal(
        job_id,
        status="failed",
        stage="error",
        error_summary="Mock translation timeout",
        result={
            "jobId": job_id,
            "status": "failed",
            "terminal": True,
            "localizedVideos": [],
            "metrics": {"totalTime": 0, "languagesProcessed": 0},
            "error": "Mock translation timeout",
        },
    )
    status = job_store.get_job_status_response(job_id) or {}
    result = job_store.get_job_result_response(job_id) or {}
    checks.append(_assert(status.get("terminal") is True, "status payload terminal=true"))
    checks.append(_assert(status.get("status") == "failed", "status payload status=failed"))
    checks.append(_assert(bool(status.get("terminalAt")), "terminalAt is present"))
    checks.append(_assert(status.get("resultAvailable") is True, "resultAvailable=true after terminal result"))
    checks.append(_assert(result.get("error") == "Mock translation timeout", "failed result payload is available"))
    return checks


def validate_no_store_headers() -> list[dict[str, Any]]:
    expected = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return [_assert(NO_CACHE_HEADERS == expected, "job API no-store headers match expected values")]


def validate_manifest_recovery(work_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    manifest_dir = work_dir / "manifest_lock"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = job_manifest.create_manifest(manifest_dir, "manifest-lock-validation")
    manifest["warnings"].append({"message": "force recovery path"})
    original_replace = job_manifest.os.replace

    def locked_replace(src: str, dst: str) -> None:
        raise PermissionError(5, "Access is denied", dst)

    try:
        job_manifest.os.replace = locked_replace
        ok = job_manifest.save_manifest(manifest_dir, manifest)
    finally:
        job_manifest.os.replace = original_replace

    recovery_files = sorted(manifest_dir.glob("job_manifest.recovery.*.json"))
    checks.append(_assert(ok is False, "manifest save returns False after repeated PermissionError"))
    checks.append(_assert(bool(recovery_files), "manifest recovery copy is written after replace lock"))
    if recovery_files:
        recovered = json.loads(recovery_files[-1].read_text(encoding="utf-8"))
        checks.append(_assert(recovered.get("job", {}).get("job_id") == "manifest-lock-validation", "recovery manifest is valid JSON"))
    return checks


def validate_stale_metadata() -> list[dict[str, Any]]:
    active_job_key = "vidiolingua:v1:activeJob"
    legacy_keys = ["videolingua.currentJob", "videolingua.lastResult"]
    terminal_key = "vidiolingua:v1:terminalJob"
    return [
        _assert(active_job_key.startswith("vidiolingua:v1:"), "active job storage key is versioned"),
        _assert(terminal_key.startswith("vidiolingua:v1:"), "terminal job storage key is versioned"),
        _assert(all(not key.startswith("vidiolingua:v1:") for key in legacy_keys), "legacy keys are recognized as unversioned stale data"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate job lifecycle cleanup behavior.")
    parser.add_argument("--output", required=True, help="Path to write validation JSON.")
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=str(output.parent)) as tmpdir:
        work_dir = Path(tmpdir)
        checks = []
        checks.extend(validate_job_terminal_state(work_dir))
        checks.extend(validate_no_store_headers())
        checks.extend(validate_manifest_recovery(work_dir))
        checks.extend(validate_stale_metadata())

    report = {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "protected_paths_touched": [],
        "notes": [
            "No video pipeline stages were run.",
            "No virtual environments or dependencies were modified.",
            "Manifest lock handling was simulated with an in-process PermissionError.",
        ],
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
