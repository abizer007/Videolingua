"""Compute and validate a VideoLingua automatic metrics report for a job folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.worker import run_evaluation


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute a metrics_report.json for a VideoLingua job.")
    parser.add_argument("--job-dir", required=True, help="Job/output directory to inspect.")
    parser.add_argument("--ground-truth-transcript", default=None, help="Deprecated; place expert transcript at job/evaluation/ground_truth_transcript.txt.")
    parser.add_argument("--reference-translation", default=None, help="Deprecated; place expert translation at job/evaluation/reference_translation.txt.")
    parser.add_argument("--output", default=None, help="Output metrics_report.json path.")
    return parser.parse_args()


def _status(report: dict, section: str, metric: str) -> str:
    value = report.get(section, {}).get(metric, {})
    return str(value.get("status") if isinstance(value, dict) else "computed")


def main() -> int:
    args = _parse_args()
    job_dir = Path(args.job_dir)
    output = Path(args.output) if args.output else job_dir / "evaluation" / "metrics_report.json"
    report = run_evaluation(job_dir, output)

    summary = {
        "output": str(output),
        "job_dir": str(job_dir),
        "evaluation_mode": report.get("evaluation_mode"),
        "overall_score": report.get("overall", {}).get("score_0_100"),
        "overall_grade": report.get("overall", {}).get("grade"),
        "operational_validation": report.get("operational", {}).get("validation_passed"),
        "translation_backend": report.get("operational", {}).get("translation_backend"),
        "voice_backend": report.get("operational", {}).get("voice_backend"),
        "asr_status": _status(report, "asr", "score"),
        "asr_method": report.get("asr", {}).get("score", {}).get("method"),
        "translation_status": _status(report, "translation", "score"),
        "translation_method": report.get("translation", {}).get("score", {}).get("method"),
        "voice_status": _status(report, "voice", "score"),
        "sync_status": _status(report, "sync", "score"),
        "speaker_status": _status(report, "speaker", "score"),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
