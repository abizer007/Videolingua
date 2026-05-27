"""
In-memory job store for VideoLingua pipeline jobs.
Maps jobId -> status, progress, result paths, error.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import json
import os
import threading
import time

from backend import job_manifest

# Pipeline stages matching frontend-next types
STAGES = [
    "uploading",
    "bgm_separation",
    "asr",
    "translation",
    "tts",
    "lipsync",
    "complete",
    "error",
]
TERMINAL_STATUSES = {"complete", "failed", "cancelled", "timeout", "error"}
RUNNING_STATUSES = {"queued", "running"}
SCHEMA_VERSION = "job-store-v1"

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_JOBS_DIR = Path(os.environ.get("JOBS_DIR", str(_PROJECT_ROOT / "jobs")))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_stage_event(stage: str, now_iso: str, now_monotonic: float) -> dict[str, Any]:
    return {
        "stage": stage,
        "startedAt": now_iso,
        "completedAt": None,
        "durationSeconds": None,
        "_startedMonotonic": now_monotonic,
    }


def is_terminal_status(status: str | None) -> bool:
    return (status or "").lower() in TERMINAL_STATUSES


def _status_for_stage(stage: str | None, existing_status: str | None = None) -> str:
    normalized = (stage or "").lower()
    if normalized == "complete":
        return "complete"
    if normalized in {"error", "failed"}:
        return "failed"
    if normalized == "timeout":
        return "timeout"
    if normalized == "cancelled":
        return "cancelled"
    if existing_status in TERMINAL_STATUSES:
        return existing_status
    return "running"


def _finish_open_stage(job: dict[str, Any], now_iso: str, now_monotonic: float) -> None:
    history = job.setdefault("stageHistory", [])
    if history:
        previous = history[-1]
        if previous.get("completedAt") is None:
            previous["completedAt"] = now_iso
            started = previous.get("_startedMonotonic")
            if isinstance(started, (int, float)):
                previous["durationSeconds"] = round(max(0.0, now_monotonic - started), 2)


def _set_stage(job: dict[str, Any], stage: str, now_iso: str, now_monotonic: float) -> None:
    previous_stage = job.get("stage")
    if stage != previous_stage:
        _finish_open_stage(job, now_iso, now_monotonic)
        job.setdefault("stageHistory", []).append(_new_stage_event(stage, now_iso, now_monotonic))
    job["stage"] = stage


def _mark_terminal(
    job: dict[str, Any],
    *,
    status: str,
    now_iso: str,
    now_monotonic: float,
    stage: str | None = None,
    error_summary: str | None = None,
    result_path: str | None = None,
) -> None:
    if job.get("terminal"):
        if result_path:
            job["resultPath"] = result_path
        if error_summary and not job.get("errorSummary"):
            job["errorSummary"] = error_summary
        return
    terminal_stage = stage or ("complete" if status == "complete" else status)
    _set_stage(job, terminal_stage, now_iso, now_monotonic)
    _finish_open_stage(job, now_iso, now_monotonic)
    job["status"] = status
    job["terminal"] = True
    job["terminalAt"] = now_iso
    if status == "complete":
        job["completedAt"] = now_iso
    elif status in {"failed", "error"}:
        job["failedAt"] = now_iso
    elif status == "timeout":
        job["failedAt"] = now_iso
        job["timeoutAt"] = now_iso
    elif status == "cancelled":
        job["cancelledAt"] = now_iso
    if error_summary is not None:
        job["errorSummary"] = error_summary
        job["error"] = error_summary
    if result_path:
        job["resultPath"] = result_path


def create_job(
    job_id: str,
    video_path: str,
    languages: list[str],
    source_language: Optional[str] = None,
    voice_options: Optional[dict] = None,
    voice_sample_path: Optional[str] = None,
    captions_requested: bool = False,
    responsible_ai: Optional[dict] = None,
) -> None:
    now_iso = _utc_now()
    now_monotonic = time.monotonic()
    with _lock:
        _jobs[job_id] = {
            "jobId": job_id,
            "status": "queued",
            "terminal": False,
            "stage": "uploading",
            "progress": 0,
            "currentLanguage": None,
            "languages": languages,
            "sourceLanguage": source_language,
            "sourceLanguageConfidence": None,
            "voiceOptions": voice_options or {},
            "voiceSamplePath": voice_sample_path,
            "captionsRequested": bool(captions_requested),
            "error": None,
            "metrics": {},
            "analysis": {},
            "metricsReport": None,
            "responsibleAI": responsible_ai,
            "video_path": video_path,
            "jobDir": str(Path(video_path).parent),
            "manifestPath": str(job_manifest.manifest_path_for_job(Path(video_path).parent)),
            "result": None,
            "startedAt": now_iso,
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "terminalAt": None,
            "completedAt": None,
            "failedAt": None,
            "cancelledAt": None,
            "timeoutAt": None,
            "errorSummary": None,
            "errorTracePath": None,
            "resultPath": None,
            "_startedMonotonic": now_monotonic,
            "stageHistory": [_new_stage_event("uploading", now_iso, now_monotonic)],
        }


def update_job(
    job_id: str,
    stage: Optional[str] = None,
    progress: Optional[int] = None,
    current_language: Optional[str] = None,
    source_language: Optional[str] = None,
    source_language_confidence: Optional[float] = None,
    error: Optional[str] = None,
    metrics: Optional[dict] = None,
    analysis: Optional[dict] = None,
    result: Optional[dict] = None,
    metrics_report: Optional[dict] = None,
    voice_options: Optional[dict] = None,
    voice_sample_path: Optional[str] = None,
    captions_requested: Optional[bool] = None,
    responsible_ai: Optional[dict] = None,
) -> None:
    now_iso = _utc_now()
    now_monotonic = time.monotonic()
    with _lock:
        if job_id not in _jobs:
            return
        j = _jobs[job_id]
        currently_terminal = bool(j.get("terminal"))
        if stage is not None:
            next_status = _status_for_stage(stage, j.get("status"))
            if next_status in TERMINAL_STATUSES:
                _mark_terminal(
                    j,
                    status="failed" if next_status == "error" else next_status,
                    now_iso=now_iso,
                    now_monotonic=now_monotonic,
                    stage="error" if stage in {"error", "failed"} else stage,
                    error_summary=error,
                )
            elif not currently_terminal:
                _set_stage(j, stage, now_iso, now_monotonic)
                j["status"] = next_status
        j["updatedAt"] = now_iso
        if not currently_terminal and progress is not None:
            j["progress"] = min(100, max(0, progress))
        if not currently_terminal and current_language is not None:
            j["currentLanguage"] = current_language
        if source_language is not None:
            j["sourceLanguage"] = source_language
        if source_language_confidence is not None:
            j["sourceLanguageConfidence"] = source_language_confidence
        if error is not None:
            j["error"] = error
            j["errorSummary"] = error
            if not j.get("terminal"):
                _mark_terminal(
                    j,
                    status="failed",
                    now_iso=now_iso,
                    now_monotonic=now_monotonic,
                    stage="error",
                    error_summary=error,
                )
        if metrics is not None:
            j["metrics"] = {**j.get("metrics", {}), **metrics}
        if analysis is not None:
            j["analysis"] = {**j.get("analysis", {}), **analysis}
        if voice_options is not None:
            j["voiceOptions"] = voice_options
        if voice_sample_path is not None:
            j["voiceSamplePath"] = voice_sample_path
        if captions_requested is not None:
            j["captionsRequested"] = bool(captions_requested)
        if result is not None:
            j["result"] = result
            j["resultPath"] = str(Path(j.get("jobDir") or Path(j.get("video_path", "")).parent) / "pipeline_result.json")
        if metrics_report is not None:
            j["metricsReport"] = metrics_report
        if responsible_ai is not None:
            j["responsibleAI"] = responsible_ai


def mark_job_terminal(
    job_id: str,
    *,
    status: str,
    stage: str | None = None,
    error_summary: str | None = None,
    result: Optional[dict] = None,
    metrics_report: Optional[dict] = None,
    result_path: str | None = None,
) -> None:
    now_iso = _utc_now()
    now_monotonic = time.monotonic()
    normalized = "failed" if status == "error" else status
    if normalized not in TERMINAL_STATUSES:
        raise ValueError(f"Not a terminal job status: {status}")
    with _lock:
        if job_id not in _jobs:
            return
        j = _jobs[job_id]
        _mark_terminal(
            j,
            status=normalized,
            now_iso=now_iso,
            now_monotonic=now_monotonic,
            stage=stage,
            error_summary=error_summary,
            result_path=result_path,
        )
        j["updatedAt"] = now_iso
        if normalized == "complete":
            j["progress"] = 100
        if result is not None:
            j["result"] = result
        if metrics_report is not None:
            j["metricsReport"] = metrics_report


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    with _lock:
        _hydrate_job_from_disk(job_id)
        return _jobs.get(job_id)


def _hydrate_job_from_disk(job_id: str) -> None:
    """Restore a terminal job after an API restart using disk artifacts."""
    job_dir = _JOBS_DIR / job_id
    result_path = job_dir / "pipeline_result.json"
    manifest_path = job_manifest.manifest_path_for_job(job_dir)
    if not result_path.is_file() or not manifest_path.is_file():
        return
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    status = str(result.get("status") or ("complete" if result.get("localizedVideos") else "failed")).lower()
    if status == "completed":
        status = "complete"
    if status not in TERMINAL_STATUSES:
        status = "complete" if result.get("localizedVideos") else "failed"
    manifest = job_manifest.load_manifest(manifest_path) or {}
    manifest_summary = job_manifest.build_manifest_summary(manifest_path)
    languages = []
    target = (manifest.get("inputs") or {}).get("target_language") if isinstance(manifest, dict) else None
    if isinstance(target, str) and target:
        languages = [value.strip() for value in target.split(",") if value.strip()]
    elif isinstance(target, list):
        languages = [str(value) for value in target if value]
    run_evidence = (result.get("analysis") or {}).get("run_evidence") if isinstance(result.get("analysis"), dict) else {}
    if not languages and isinstance(run_evidence, dict) and run_evidence.get("target_language"):
        languages = [str(run_evidence["target_language"])]
    now_iso = _utc_now()
    _jobs[job_id] = {
        "jobId": job_id,
        "status": status,
        "terminal": True,
        "stage": "complete" if status == "complete" else "error",
        "progress": 100 if status == "complete" else 0,
        "currentLanguage": None,
        "languages": languages,
        "sourceLanguage": run_evidence.get("source_language") if isinstance(run_evidence, dict) else None,
        "sourceLanguageConfidence": None,
        "voiceOptions": {},
        "voiceSamplePath": None,
        "captionsRequested": bool(result.get("captionsRequested")),
        "error": result.get("error"),
        "metrics": result.get("metrics") if isinstance(result.get("metrics"), dict) else {},
        "analysis": result.get("analysis") if isinstance(result.get("analysis"), dict) else {},
        "metricsReport": result.get("metricsReport"),
        "responsibleAI": result.get("responsibleAI"),
        "video_path": str(job_dir / "input_video.mp4"),
        "jobDir": str(job_dir),
        "manifestPath": str(manifest_path),
        "result": result,
        "startedAt": result.get("startedAt") or now_iso,
        "createdAt": result.get("createdAt") or now_iso,
        "updatedAt": now_iso,
        "terminalAt": now_iso,
        "completedAt": now_iso if status == "complete" else None,
        "failedAt": now_iso if status != "complete" else None,
        "cancelledAt": None,
        "timeoutAt": None,
        "errorSummary": result.get("error"),
        "errorTracePath": None,
        "resultPath": str(result_path),
        "_startedMonotonic": time.monotonic(),
        "stageHistory": [],
    }


def _translation_qa_from_job(job: dict[str, Any]) -> dict[str, Any] | None:
    result = job.get("result")
    if isinstance(result, dict) and isinstance(result.get("translationQA"), dict):
        return result.get("translationQA")
    analysis = job.get("analysis")
    if isinstance(analysis, dict) and isinstance(analysis.get("translationQA"), dict):
        return analysis.get("translationQA")
    metrics = job.get("metrics") if isinstance(job.get("metrics"), dict) else {}
    if not any(str(key).startswith("translation_qa_") for key in metrics):
        return None
    return {
        "status": metrics.get("translation_qa_status"),
        "checksPassed": metrics.get("translation_qa_checks_passed"),
        "warningsCount": metrics.get("translation_qa_warnings_count"),
        "errorsCount": metrics.get("translation_qa_errors_count"),
        "emptySegments": metrics.get("translation_qa_empty_segments"),
        "scriptMatch": metrics.get("translation_qa_script_match"),
        "numberIssues": metrics.get("translation_qa_number_issues"),
        "entityIssues": metrics.get("translation_qa_entity_issues"),
        "expansionRatioWarnings": metrics.get("translation_qa_expansion_ratio_warnings"),
        "reportPath": metrics.get("translation_qa_report_path"),
    }


def _analysis_summary_from_job(job: dict[str, Any], key: str) -> dict[str, Any] | None:
    result = job.get("result")
    if isinstance(result, dict) and isinstance(result.get(key), dict):
        return result.get(key)
    analysis = job.get("analysis")
    if isinstance(analysis, dict) and isinstance(analysis.get(key), dict):
        return analysis.get(key)
    return None


def _normalize_result_payload(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    localized = payload.get("localizedVideos") if isinstance(payload.get("localizedVideos"), list) else []
    total_time = metrics.get("totalTime")
    languages_processed = metrics.get("languagesProcessed")
    normalized = {
        **payload,
        "originalVideo": payload.get("originalVideo") or "",
        "localizedVideos": localized,
        "metrics": {
            **metrics,
            "totalTime": total_time if isinstance(total_time, (int, float)) else 0,
            "languagesProcessed": languages_processed if isinstance(languages_processed, int) else len(localized),
        },
    }
    return normalized


def get_job_status_response(job_id: str) -> Optional[dict]:
    """Return job data in the shape expected by frontend GET /api/job-status/:jobId"""
    with _lock:
        _hydrate_job_from_disk(job_id)
        if job_id not in _jobs:
            return None
        j = _jobs[job_id]
        elapsed = None
        started_monotonic = j.get("_startedMonotonic")
        if isinstance(started_monotonic, (int, float)):
            elapsed = round(max(0.0, time.monotonic() - started_monotonic), 2)
        stage_history = []
        for event in j.get("stageHistory", []):
            public_event = {
                "stage": event.get("stage"),
                "startedAt": event.get("startedAt"),
                "completedAt": event.get("completedAt"),
                "durationSeconds": event.get("durationSeconds"),
            }
            if public_event["completedAt"] is None:
                started = event.get("_startedMonotonic")
                if isinstance(started, (int, float)):
                    public_event["durationSeconds"] = round(max(0.0, time.monotonic() - started), 2)
            stage_history.append(public_event)
        manifest_summary = job_manifest.build_manifest_summary(j.get("manifestPath") or Path(j.get("video_path", "")).parent)
        return {
            "schemaVersion": SCHEMA_VERSION,
            "jobId": j["jobId"],
            "status": j.get("status") or _status_for_stage(j.get("stage")),
            "terminal": bool(j.get("terminal") or is_terminal_status(j.get("status")) or j.get("stage") in {"complete", "error", "failed", "timeout", "cancelled"}),
            "stage": j["stage"],
            "progress": j["progress"],
            "currentLanguage": j.get("currentLanguage"),
            "languages": j.get("languages", []),
            "sourceLanguage": j.get("sourceLanguage"),
            "sourceLanguageConfidence": j.get("sourceLanguageConfidence"),
            "error": j.get("error"),
            "metrics": j.get("metrics") or {},
            "analysis": j.get("analysis") or {},
            "metricsReport": j.get("metricsReport"),
            "startedAt": j.get("startedAt"),
            "createdAt": j.get("createdAt") or j.get("startedAt"),
            "updatedAt": j.get("updatedAt"),
            "terminalAt": j.get("terminalAt"),
            "completedAt": j.get("completedAt"),
            "failedAt": j.get("failedAt"),
            "cancelledAt": j.get("cancelledAt"),
            "timeoutAt": j.get("timeoutAt"),
            "elapsedSeconds": elapsed,
            "errorSummary": j.get("errorSummary") or j.get("error"),
            "errorTracePath": j.get("errorTracePath"),
            "resultPath": j.get("resultPath"),
            "resultAvailable": j.get("result") is not None,
            "stageHistory": stage_history,
            "translationQA": _translation_qa_from_job(j),
            "linguisticIntegrity": _analysis_summary_from_job(j, "linguisticIntegrity"),
            "phoneticResolution": _analysis_summary_from_job(j, "phoneticResolution"),
            "responsibleAI": j.get("responsibleAI"),
            "captionsRequested": bool(j.get("captionsRequested")),
            "manifestSummary": manifest_summary,
            "manifestPath": manifest_summary.get("manifest_path") if manifest_summary else j.get("manifestPath"),
        }


def get_job_result_response(job_id: str) -> Optional[dict]:
    """Return job result in the shape expected by frontend GET /api/result/:jobId"""
    with _lock:
        _hydrate_job_from_disk(job_id)
        if job_id not in _jobs:
            return None
        j = _jobs[job_id]
        manifest_summary = job_manifest.build_manifest_summary(j.get("manifestPath") or Path(j.get("video_path", "")).parent)
        if j.get("result") is not None:
            result = _normalize_result_payload(dict(j["result"]))
            result.setdefault("manifestSummary", manifest_summary)
            result.setdefault("manifestPath", manifest_summary.get("manifest_path") if manifest_summary else j.get("manifestPath"))
            result.setdefault("translationQA", _translation_qa_from_job(j))
            result.setdefault("linguisticIntegrity", _analysis_summary_from_job(j, "linguisticIntegrity"))
            result.setdefault("phoneticResolution", _analysis_summary_from_job(j, "phoneticResolution"))
            result.setdefault("responsibleAI", j.get("responsibleAI"))
            result.setdefault("captionsRequested", bool(j.get("captionsRequested")))
            return result
        if j.get("stage") == "error":
            return {
                "jobId": job_id,
                "originalVideo": "",
                "localizedVideos": [],
                "metrics": {"totalTime": 0, "languagesProcessed": 0},
                "analysis": j.get("analysis") or {},
                "metricsReport": j.get("metricsReport"),
                "translationQA": _translation_qa_from_job(j),
                "linguisticIntegrity": _analysis_summary_from_job(j, "linguisticIntegrity"),
                "phoneticResolution": _analysis_summary_from_job(j, "phoneticResolution"),
                "responsibleAI": j.get("responsibleAI"),
                "captionsRequested": bool(j.get("captionsRequested")),
                "manifestSummary": manifest_summary,
                "manifestPath": manifest_summary.get("manifest_path") if manifest_summary else j.get("manifestPath"),
                "error": j.get("error"),
            }
        return None
