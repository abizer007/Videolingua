"""Validate or optionally retrofit a VideoLingua job_manifest.json sidecar."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from backend import job_manifest


REQUIRED_TOP_LEVEL = {"schema_version", "job", "inputs", "routing", "stages", "artifacts", "recovery", "result"}
REQUIRED_STAGE_FIELDS = {
    "status",
    "started_at",
    "ended_at",
    "elapsed_sec",
    "attempt_count",
    "can_retry",
    "can_resume_from_here",
    "error_message",
    "warning_messages",
    "input_artifacts",
    "output_artifacts",
    "logs",
}
VALID_STAGE_STATUSES = {"pending", "running", "completed", "failed", "skipped"}


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a JSON object")
    return data


def _discover_first(job_dir: Path, pattern: str) -> Path | None:
    matches = sorted(job_dir.glob(pattern))
    return matches[0] if matches else None


def _retrofit(job_dir: Path) -> Path:
    pipeline_result_path = job_dir / "pipeline_result.json"
    pipeline_result = _read_json(pipeline_result_path) if pipeline_result_path.is_file() else {}
    job_id = str(pipeline_result.get("jobId") or job_dir.name)
    metrics = pipeline_result.get("metrics") if isinstance(pipeline_result.get("metrics"), dict) else {}
    analysis = pipeline_result.get("analysis") if isinstance(pipeline_result.get("analysis"), dict) else {}
    run_evidence = analysis.get("run_evidence") if isinstance(analysis.get("run_evidence"), dict) else {}
    input_video = _discover_first(job_dir, "results/input_video.mp4") or _discover_first(job_dir, "asr/input/*.mp4")
    target_language = metrics.get("target_language") or run_evidence.get("target_language")
    source_language = metrics.get("translation_source_language") or run_evidence.get("source_language")
    manifest = job_manifest.create_manifest(
        job_dir,
        job_id,
        input_video_path=input_video,
        target_language=str(target_language) if target_language else None,
        source_language=str(source_language) if source_language else None,
        run_source="historical_retrofit",
        output_dir=job_dir,
    )
    manifest_path = job_manifest.manifest_path_for_job(job_dir)
    job_manifest.set_routing_decision(
        manifest_path,
        selected_translation_backend=metrics.get("translation_backend") or run_evidence.get("translation_backend"),
        selected_voice_backend=metrics.get("voice_backend") or run_evidence.get("voice_backend"),
        xtts_supported=bool(metrics.get("xtts_selected")),
        sarvam_supported=bool(metrics.get("sarvam_selected")),
        indicf5_enabled=False,
        generic_fallback_allowed=False,
        fallback_used=bool(metrics.get("fallback_used") or run_evidence.get("fallback_used")),
    )
    artifacts = {
        "source_video": input_video,
        "asr_json": _discover_first(job_dir, "asr/output/*.json"),
        "translation_json": _discover_first(job_dir, "translation/output/*.json"),
        "tts_wav": _discover_first(job_dir, "tts/output/*.wav"),
        "normalized_tts_wav": _discover_first(job_dir, "outputs/intermediate/*clean*.wav"),
        "reference_audio": _discover_first(job_dir, "reference/*.wav") or _discover_first(job_dir, "outputs/intermediate/reference*.wav"),
        "reference_metadata": _discover_first(job_dir, "reference/*metadata*.json"),
        "final_mp4": _discover_first(job_dir, "results/*_dubbed_*.mp4"),
        "metrics_report": _discover_first(job_dir, "evaluation/metrics_report.json"),
        "pipeline_result": pipeline_result_path if pipeline_result_path.is_file() else None,
    }
    stage_by_key = {
        "source_video": "receive_upload",
        "asr_json": "asr",
        "translation_json": "translation",
        "tts_wav": "voice_generation",
        "normalized_tts_wav": "audio_validation",
        "reference_audio": "prepare_audio",
        "reference_metadata": "prepare_audio",
        "final_mp4": "lipsync_mux",
        "metrics_report": "metrics_evaluation",
        "pipeline_result": "complete",
    }
    for key, value in artifacts.items():
        if value:
            job_manifest.register_artifact(manifest_path, key, value, stage=stage_by_key.get(key), kind=value.suffix.lstrip("."), role="output")
    for stage in job_manifest.STAGES:
        if stage == "complete" and pipeline_result:
            job_manifest.complete_stage(manifest_path, stage, output_artifacts=[pipeline_result_path])
        elif stage == "metrics_evaluation" and artifacts["metrics_report"]:
            job_manifest.complete_stage(manifest_path, stage, output_artifacts=[artifacts["metrics_report"]])
        elif any(stage_by_key.get(key) == stage and value for key, value in artifacts.items()):
            job_manifest.complete_stage(manifest_path, stage)
        else:
            job_manifest.skip_stage(manifest_path, stage, "Historical retrofit did not find artifacts for this stage.")
    final_mp4 = artifacts["final_mp4"]
    job_manifest.set_final_result(
        manifest_path,
        final_status="completed" if final_mp4 else "failed" if pipeline_result.get("error") else "pending",
        final_mp4_path=final_mp4,
        duration_sec=metrics.get("final_mp4_duration_s") if isinstance(metrics.get("final_mp4_duration_s"), (int, float)) else None,
        file_size_bytes=final_mp4.stat().st_size if final_mp4 and final_mp4.is_file() else None,
        validation_passed=bool(final_mp4) and not bool(pipeline_result.get("error")),
        user_facing_error=pipeline_result.get("error"),
    )
    return manifest_path


def _validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(manifest.keys()))
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")
    stages = manifest.get("stages")
    if not isinstance(stages, dict):
        errors.append("stages must be an object")
    else:
        for stage in job_manifest.STAGES:
            data = stages.get(stage)
            if not isinstance(data, dict):
                errors.append(f"missing stage object: {stage}")
                continue
            stage_missing = sorted(REQUIRED_STAGE_FIELDS - set(data.keys()))
            if stage_missing:
                errors.append(f"{stage}: missing fields {', '.join(stage_missing)}")
            if data.get("status") not in VALID_STAGE_STATUSES:
                errors.append(f"{stage}: invalid status {data.get('status')!r}")
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for key, value in artifacts.items():
            entries = value if isinstance(value, list) else [value]
            for entry in entries:
                if not isinstance(entry, dict):
                    errors.append(f"artifact {key}: entry must be an object")
                    continue
                path_value = entry.get("path")
                if path_value and entry.get("exists") is True and not Path(path_value).is_file():
                    errors.append(f"artifact {key}: marked exists but file is missing: {path_value}")
    elif artifacts is not None:
        errors.append("artifacts must be an object")
    if not manifest_path.name == job_manifest.MANIFEST_FILENAME:
        errors.append("manifest filename must be job_manifest.json")
    return errors


def _print_summary(manifest: dict[str, Any], manifest_path: Path) -> None:
    summary = job_manifest.build_manifest_summary(manifest_path) or {}
    stages = summary.get("stage_statuses") or {}
    artifacts = summary.get("important_artifacts") or {}
    print(json.dumps({
        "manifest": str(manifest_path),
        "job_id": summary.get("job_id"),
        "final_status": summary.get("final_status"),
        "current_stage": summary.get("current_stage"),
        "last_completed_stage": summary.get("last_completed_stage"),
        "failed_stage": summary.get("failed_stage"),
        "selected_backends": summary.get("selected_backends"),
        "stage_count": len(stages),
        "artifact_count": len(artifacts),
        "resume_supported": summary.get("resume_supported"),
    }, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a VideoLingua job_manifest.json file.")
    parser.add_argument("--job-dir", required=True, help="Job/output directory containing job_manifest.json.")
    parser.add_argument("--print-summary", action="store_true", help="Print a concise manifest summary.")
    parser.add_argument("--retrofit", action="store_true", help="Create a retrospective manifest from existing artifacts.")
    args = parser.parse_args(argv)

    job_dir = Path(args.job_dir)
    manifest_path = job_manifest.manifest_path_for_job(job_dir)
    if not manifest_path.is_file():
        if not args.retrofit:
            print(f"manifest not present for historical job: {manifest_path}")
            return 0
        manifest_path = _retrofit(job_dir)
        print(f"retrofitted manifest: {manifest_path}")

    try:
        manifest = _read_json(manifest_path)
    except Exception as exc:
        print(f"malformed manifest: {exc}", file=sys.stderr)
        return 2

    errors = _validate_manifest(manifest, manifest_path)
    if args.print_summary:
        _print_summary(manifest, manifest_path)
    if errors:
        for error in errors:
            print(f"manifest validation error: {error}", file=sys.stderr)
        return 2
    print("job_manifest.json is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
