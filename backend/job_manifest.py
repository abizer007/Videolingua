"""Durable per-job manifest helpers for VideoLingua orchestration.

The manifest is intentionally additive: write failures are logged and do not
change pipeline routing, subprocess execution, or result creation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any


MANIFEST_FILENAME = "job_manifest.json"
SCHEMA_VERSION = 1
PIPELINE_VERSION = "job-manifest-2026-05-05"
MANIFEST_REPLACE_BACKOFF_SECONDS = (0.05, 0.1, 0.25, 0.5, 1.0)
_manifest_locks: dict[str, threading.Lock] = {}
_manifest_locks_guard = threading.Lock()

STAGES = [
    "receive_upload",
    "prepare_audio",
    "asr",
    "translation",
    "voice_generation",
    "audio_validation",
    "lipsync_mux",
    "output_validation",
    "metrics_evaluation",
    "complete",
]

RESUMABLE_STAGES = {
    "receive_upload",
    "prepare_audio",
    "asr",
    "translation",
    "voice_generation",
    "audio_validation",
    "lipsync_mux",
    "output_validation",
    "metrics_evaluation",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_path(path: str | Path) -> Path:
    p = Path(path)
    if p.name == MANIFEST_FILENAME:
        return p
    return p / MANIFEST_FILENAME


def manifest_path_for_job(job_dir: str | Path) -> Path:
    return _manifest_path(job_dir)


def _safe_path(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(Path(value))
    except (TypeError, ValueError):
        return str(value)


def _safe_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, Path)):
        return [str(values)]
    if isinstance(values, dict):
        return [str(key) for key in values.keys()]
    try:
        return [str(value) for value in values if value is not None]
    except TypeError:
        return [str(values)]


def _log_manifest_warning(message: str) -> None:
    print(f"[JobManifest] WARNING: {message}")


def _lock_for_manifest(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _manifest_locks_guard:
        lock = _manifest_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _manifest_locks[key] = lock
        return lock


def _is_windows_lock_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    winerror = getattr(exc, "winerror", None)
    return winerror == 5


def _recovery_manifest_path(manifest_file: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return manifest_file.with_name(f"job_manifest.recovery.{stamp}.json")


def _write_recovery_from_temp(temp_name: str, manifest_file: Path) -> Path:
    recovery_path = _recovery_manifest_path(manifest_file)
    recovery_path.write_bytes(Path(temp_name).read_bytes())
    try:
        Path(temp_name).unlink()
    except OSError:
        pass
    return recovery_path


def _stage_template(can_retry: bool = False) -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "ended_at": None,
        "elapsed_sec": None,
        "attempt_count": 0,
        "can_retry": can_retry,
        "can_resume_from_here": False,
        "error_message": None,
        "warning_messages": [],
        "input_artifacts": [],
        "output_artifacts": [],
        "logs": [],
    }


def _ensure_shape(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.setdefault("schema_version", SCHEMA_VERSION)
    manifest.setdefault("job", {})
    manifest.setdefault("inputs", {})
    manifest.setdefault("routing", {})
    stages = manifest.setdefault("stages", {})
    for stage in STAGES:
        stages.setdefault(stage, _stage_template(stage in RESUMABLE_STAGES))
    manifest.setdefault("artifacts", {})
    manifest.setdefault(
        "recovery",
        {
            "last_completed_stage": None,
            "failed_stage": None,
            "retry_count_total": 0,
            "max_retries": 0,
            "resume_supported": False,
            "resume_command_hint": build_resume_hint(None),
            "retry_failed_stage_hint": None,
        },
    )
    manifest.setdefault(
        "result",
        {
            "final_status": "pending",
            "final_mp4_path": None,
            "duration_sec": None,
            "file_size_bytes": None,
            "validation_passed": None,
            "user_facing_error": None,
        },
    )
    manifest.setdefault("warnings", [])
    manifest.setdefault("errors", [])
    return manifest


def _touch(manifest: dict[str, Any]) -> None:
    manifest.setdefault("job", {})["updated_at"] = _utc_now()


def _cheap_file_hash(path: str | Path | None, max_bytes: int = 256 * 1024 * 1024) -> str | None:
    if not path:
        return None
    p = Path(path)
    try:
        if not p.is_file() or p.stat().st_size > max_bytes:
            return None
        digest = hashlib.sha256()
        with p.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
    except OSError as exc:
        _log_manifest_warning(f"Could not hash input video {p}: {exc}")
        return None


def load_manifest(path: str | Path) -> dict[str, Any] | None:
    manifest_file = _manifest_path(path)
    try:
        if not manifest_file.is_file():
            return None
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            _log_manifest_warning(f"Manifest is not a JSON object: {manifest_file}")
            return None
        return _ensure_shape(data)
    except Exception as exc:
        _log_manifest_warning(f"Could not load manifest {manifest_file}: {exc}")
        return None


def save_manifest(path: str | Path, manifest: dict[str, Any]) -> bool:
    manifest_file = _manifest_path(path)
    lock = _lock_for_manifest(manifest_file)
    with lock:
        temp_name: str | None = None
        try:
            _ensure_shape(manifest)
            _touch(manifest)
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{MANIFEST_FILENAME}.",
                suffix=".tmp",
                dir=str(manifest_file.parent),
                text=True,
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError as exc:
                    _log_manifest_warning(f"Could not fsync temp manifest {temp_name}: {exc}")

            last_error: BaseException | None = None
            for attempt, delay in enumerate((0.0, *MANIFEST_REPLACE_BACKOFF_SECONDS), start=1):
                if delay:
                    time.sleep(delay)
                try:
                    os.replace(temp_name, manifest_file)
                    temp_name = None
                    return True
                except OSError as exc:
                    last_error = exc
                    if not _is_windows_lock_error(exc):
                        raise
                    _log_manifest_warning(
                        f"Manifest replace locked for {manifest_file} on attempt {attempt}; retrying."
                    )

            recovery_path = _write_recovery_from_temp(temp_name, manifest_file)
            temp_name = None
            _log_manifest_warning(
                f"Could not replace {manifest_file} after retries: {last_error}. "
                f"Wrote recovery manifest {recovery_path}."
            )
            return False
        except Exception as exc:
            try:
                if temp_name and Path(temp_name).exists():
                    recovery_path = _write_recovery_from_temp(temp_name, manifest_file)
                    _log_manifest_warning(
                        f"Could not save manifest {manifest_file}: {exc}. "
                        f"Wrote recovery manifest {recovery_path}."
                    )
                    temp_name = None
                    return False
            except Exception as recovery_exc:
                _log_manifest_warning(
                    f"Could not save manifest {manifest_file}: {exc}; recovery write also failed: {recovery_exc}"
                )
            _log_manifest_warning(f"Could not save manifest {manifest_file}: {exc}")
            return False
        finally:
            if temp_name:
                temp_path = Path(temp_name)
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass


def save_manifest_recovery_copy(path: str | Path, manifest: dict[str, Any]) -> Path | None:
    manifest_file = _manifest_path(path)
    try:
        _ensure_shape(manifest)
        _touch(manifest)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        recovery_path = _recovery_manifest_path(manifest_file)
        recovery_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return recovery_path
    except Exception as exc:
        _log_manifest_warning(f"Could not write recovery manifest for {manifest_file}: {exc}")
        return None


def create_manifest(
    job_dir: str | Path,
    job_id: str,
    *,
    input_video_path: str | Path | None = None,
    reference_audio_path: str | Path | None = None,
    auto_reference_enabled: bool = False,
    target_language: str | list[str] | None = None,
    source_language: str | None = None,
    mode: str | None = None,
    run_source: str = "api",
    requested_by: str | None = None,
    pipeline_version: str | None = None,
    output_dir: str | Path | None = None,
    captions_requested: bool = False,
    max_retries: int = 0,
) -> dict[str, Any]:
    now = _utc_now()
    job_dir = Path(job_dir)
    targets = ",".join(_safe_list(target_language)) if isinstance(target_language, list) else target_language
    manifest = _ensure_shape(
        {
            "schema_version": SCHEMA_VERSION,
            "job": {
                "job_id": job_id,
                "created_at": now,
                "updated_at": now,
                "pipeline_version": pipeline_version or PIPELINE_VERSION,
                "run_source": run_source,
                "requested_by": requested_by,
            },
            "inputs": {
                "input_video_path": _safe_path(input_video_path),
                "input_video_hash": _cheap_file_hash(input_video_path),
                "reference_audio_path": _safe_path(reference_audio_path),
                "auto_reference_enabled": bool(auto_reference_enabled),
                "extracted_reference_path": None,
                "target_language": targets,
                "source_language": source_language,
                "captionsRequested": bool(captions_requested),
                "captions_requested": bool(captions_requested),
                "mode": mode or os.environ.get("VIDIOLINGUA_PIPELINE_MODE", "practical"),
                "output_dir": _safe_path(output_dir or job_dir),
            },
            "routing": {
                "selected_translation_backend": None,
                "selected_voice_backend": None,
                "xtts_supported": False,
                "sarvam_supported": False,
                "indicf5_enabled": False,
                "generic_fallback_allowed": False,
                "fallback_used": False,
                "fallback_reason": None,
            },
            "recovery": {
                "last_completed_stage": None,
                "failed_stage": None,
                "retry_count_total": 0,
                "max_retries": max(0, int(max_retries)),
                "resume_supported": False,
                "resume_command_hint": build_resume_hint(None),
                "retry_failed_stage_hint": None,
            },
        }
    )
    save_manifest(job_dir, manifest)
    return manifest


def _mutate_manifest(path: str | Path, mutator) -> dict[str, Any] | None:
    manifest = load_manifest(path)
    if manifest is None:
        return None
    try:
        mutator(manifest)
    except Exception as exc:
        _log_manifest_warning(f"Could not update manifest data: {exc}")
        return manifest
    save_manifest(path, manifest)
    return manifest


def update_job_metadata(path: str | Path, **metadata: Any) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        job = manifest.setdefault("job", {})
        inputs = manifest.setdefault("inputs", {})
        for key, value in metadata.items():
            if key in {"input_video_path", "reference_audio_path", "extracted_reference_path", "output_dir"}:
                inputs[key] = _safe_path(value)
            elif key in inputs:
                inputs[key] = value
            else:
                job[key] = value

    return _mutate_manifest(path, mutate)


def start_stage(
    path: str | Path,
    stage: str,
    *,
    input_artifacts: Any = None,
    logs: Any = None,
) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        item = manifest["stages"].setdefault(stage, _stage_template(stage in RESUMABLE_STAGES))
        item["status"] = "running"
        item["started_at"] = _utc_now()
        item["ended_at"] = None
        item["elapsed_sec"] = None
        item["attempt_count"] = int(item.get("attempt_count") or 0) + 1
        item["error_message"] = None
        if input_artifacts is not None:
            item["input_artifacts"] = _safe_list(input_artifacts)
        if logs is not None:
            item["logs"] = _safe_list(logs)
        manifest["result"]["final_status"] = "running"

    return _mutate_manifest(path, mutate)


def complete_stage(
    path: str | Path,
    stage: str,
    *,
    output_artifacts: Any = None,
    logs: Any = None,
) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        item = manifest["stages"].setdefault(stage, _stage_template(stage in RESUMABLE_STAGES))
        ended = _utc_now()
        item["status"] = "completed"
        item["ended_at"] = ended
        item["error_message"] = None
        started = item.get("started_at")
        if started:
            try:
                elapsed = datetime.fromisoformat(ended).timestamp() - datetime.fromisoformat(started).timestamp()
                item["elapsed_sec"] = round(max(0.0, elapsed), 3)
            except ValueError:
                item["elapsed_sec"] = None
        item["can_resume_from_here"] = stage in RESUMABLE_STAGES
        if output_artifacts is not None:
            item["output_artifacts"] = _safe_list(output_artifacts)
        if logs is not None:
            item["logs"] = sorted(set(_safe_list(item.get("logs")) + _safe_list(logs)))
        recovery = manifest.setdefault("recovery", {})
        recovery["last_completed_stage"] = stage
        if recovery.get("failed_stage") == stage:
            recovery["failed_stage"] = None
            recovery["retry_failed_stage_hint"] = None
            recovery["resume_command_hint"] = build_resume_hint(None)

    return _mutate_manifest(path, mutate)


def fail_stage(
    path: str | Path,
    stage: str,
    error_message: str,
    *,
    output_artifacts: Any = None,
    logs: Any = None,
) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        item = manifest["stages"].setdefault(stage, _stage_template(stage in RESUMABLE_STAGES))
        ended = _utc_now()
        item["status"] = "failed"
        item["ended_at"] = ended
        item["error_message"] = str(error_message)
        if output_artifacts is not None:
            item["output_artifacts"] = _safe_list(output_artifacts)
        if logs is not None:
            item["logs"] = sorted(set(_safe_list(item.get("logs")) + _safe_list(logs)))
        recovery = manifest.setdefault("recovery", {})
        recovery["failed_stage"] = stage
        recovery["retry_failed_stage_hint"] = (
            f"Retry support is planned for stage '{stage}'. Inspect manifest artifacts before rerunning."
        )
        recovery["resume_command_hint"] = build_resume_hint(stage)
        manifest["result"]["final_status"] = "failed"
        manifest["result"]["user_facing_error"] = str(error_message)
        manifest.setdefault("errors", []).append(
            {"stage": stage, "message": str(error_message), "created_at": ended}
        )

    return _mutate_manifest(path, mutate)


def skip_stage(
    path: str | Path,
    stage: str,
    reason: str | None = None,
    *,
    logs: Any = None,
) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        item = manifest["stages"].setdefault(stage, _stage_template(stage in RESUMABLE_STAGES))
        item["status"] = "skipped"
        item["ended_at"] = _utc_now()
        item["elapsed_sec"] = 0.0
        if reason:
            item.setdefault("warning_messages", []).append(reason)
        if logs is not None:
            item["logs"] = sorted(set(_safe_list(item.get("logs")) + _safe_list(logs)))

    return _mutate_manifest(path, mutate)


def register_artifact(
    path: str | Path,
    key: str,
    artifact_path: str | Path | None,
    *,
    stage: str | None = None,
    kind: str | None = None,
    role: str = "output",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        artifact_value = _safe_path(artifact_path)
        entry: dict[str, Any] = {
            "path": artifact_value,
            "stage": stage,
            "kind": kind,
            "exists": bool(artifact_path and Path(artifact_path).is_file()),
            "size_bytes": None,
            "updated_at": _utc_now(),
        }
        if artifact_path:
            try:
                p = Path(artifact_path)
                if p.is_file():
                    entry["size_bytes"] = p.stat().st_size
            except OSError:
                pass
        if metadata:
            entry["metadata"] = metadata
        artifacts = manifest.setdefault("artifacts", {})
        if key in artifacts:
            existing = artifacts[key]
            if isinstance(existing, list):
                existing.append(entry)
            else:
                artifacts[key] = [existing, entry]
        else:
            artifacts[key] = entry
        if stage:
            stage_item = manifest["stages"].setdefault(stage, _stage_template(stage in RESUMABLE_STAGES))
            target_key = "input_artifacts" if role == "input" else "output_artifacts"
            values = _safe_list(stage_item.get(target_key))
            if artifact_value and artifact_value not in values:
                values.append(artifact_value)
            stage_item[target_key] = values

    return _mutate_manifest(path, mutate)


def register_warning(path: str | Path, message: str, *, stage: str | None = None) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        warning = {"stage": stage, "message": str(message), "created_at": _utc_now()}
        manifest.setdefault("warnings", []).append(warning)
        if stage:
            manifest["stages"].setdefault(stage, _stage_template()).setdefault("warning_messages", []).append(str(message))

    return _mutate_manifest(path, mutate)


def register_error(path: str | Path, message: str, *, stage: str | None = None) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        manifest.setdefault("errors", []).append(
            {"stage": stage, "message": str(message), "created_at": _utc_now()}
        )

    return _mutate_manifest(path, mutate)


def set_routing_decision(path: str | Path, **routing: Any) -> dict[str, Any] | None:
    allowed = {
        "selected_translation_backend",
        "selected_voice_backend",
        "xtts_supported",
        "sarvam_supported",
        "indicf5_enabled",
        "generic_fallback_allowed",
        "fallback_used",
        "fallback_reason",
    }

    def mutate(manifest: dict[str, Any]) -> None:
        target = manifest.setdefault("routing", {})
        for key, value in routing.items():
            if key in allowed:
                target[key] = value

    return _mutate_manifest(path, mutate)


def set_final_result(
    path: str | Path,
    *,
    final_status: str,
    final_mp4_path: str | Path | None = None,
    duration_sec: float | None = None,
    file_size_bytes: int | None = None,
    validation_passed: bool | None = None,
    user_facing_error: str | None = None,
) -> dict[str, Any] | None:
    def mutate(manifest: dict[str, Any]) -> None:
        manifest["result"] = {
            "final_status": final_status,
            "final_mp4_path": _safe_path(final_mp4_path),
            "duration_sec": duration_sec,
            "file_size_bytes": file_size_bytes,
            "validation_passed": validation_passed,
            "user_facing_error": user_facing_error,
        }

    return _mutate_manifest(path, mutate)


def build_resume_hint(failed_stage: str | None) -> str:
    if not failed_stage:
        return "Resume execution is planned; artifacts will be available through job_manifest.json."
    return (
        f"Resume support is planned. The failed stage is '{failed_stage}', and prior artifacts "
        "are recorded in job_manifest.json."
    )


def build_manifest_summary(path: str | Path) -> dict[str, Any] | None:
    manifest = load_manifest(path)
    if manifest is None:
        return None
    stages = manifest.get("stages") or {}
    current_stage = None
    for stage in STAGES:
        if stages.get(stage, {}).get("status") == "running":
            current_stage = stage
            break
    if current_stage is None:
        current_stage = manifest.get("recovery", {}).get("failed_stage") or manifest.get("recovery", {}).get("last_completed_stage")
    artifacts = {}
    for key, value in (manifest.get("artifacts") or {}).items():
        entries = value if isinstance(value, list) else [value]
        safe_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path_value = entry.get("path")
            safe_entries.append(
                {
                    "name": Path(path_value).name if path_value else None,
                    "stage": entry.get("stage"),
                    "kind": entry.get("kind"),
                    "exists": entry.get("exists"),
                    "sizeBytes": entry.get("size_bytes"),
                }
            )
        artifacts[key] = safe_entries if isinstance(value, list) else (safe_entries[0] if safe_entries else None)
    return {
        "job_id": manifest.get("job", {}).get("job_id"),
        "final_status": manifest.get("result", {}).get("final_status"),
        "current_stage": current_stage,
        "last_completed_stage": manifest.get("recovery", {}).get("last_completed_stage"),
        "failed_stage": manifest.get("recovery", {}).get("failed_stage"),
        "stage_statuses": {
            stage: {
                "status": data.get("status"),
                "attempt_count": data.get("attempt_count"),
                "elapsed_sec": data.get("elapsed_sec"),
                "can_retry": data.get("can_retry"),
                "can_resume_from_here": data.get("can_resume_from_here"),
                "error_message": data.get("error_message"),
            }
            for stage, data in stages.items()
            if isinstance(data, dict)
        },
        "selected_backends": {
            "translation": manifest.get("routing", {}).get("selected_translation_backend"),
            "voice": manifest.get("routing", {}).get("selected_voice_backend"),
        },
        "routing": manifest.get("routing", {}),
        "important_artifacts": artifacts,
        "user_facing_error": manifest.get("result", {}).get("user_facing_error"),
        "manifest_path": str(_manifest_path(path)),
        "resume_supported": manifest.get("recovery", {}).get("resume_supported"),
        "resume_command_hint": manifest.get("recovery", {}).get("resume_command_hint"),
        "retry_failed_stage_hint": manifest.get("recovery", {}).get("retry_failed_stage_hint"),
    }
