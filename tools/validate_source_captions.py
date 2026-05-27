"""Lightweight validation for source-language caption sidecars."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from backend.captions import generate_source_captions_from_asr


def _assert(condition: bool, message: str) -> dict:
    return {"ok": bool(condition), "message": message}


def run_validation(output_dir: Path) -> dict:
    run_dir = output_dir / f"source_captions_{time.strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    asr_json = run_dir / "fake_asr.json"
    asr_json.write_text(
        json.dumps(
            {
                "language": "en",
                "segments": [
                    {"start": 0.0, "end": 1.25, "text": "Hello from the original speaker."},
                    {"start": 1.25, "end": 2.0, "text": ""},
                    {"start": 2.0, "end": 4.5, "text": "Second caption with <tags> and an arrow --> marker."},
                    {"start": 5.0, "text": "Invalid segment without an end time."},
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    false_dir = run_dir / "include_false"
    checks = [
        _assert(not false_dir.exists(), "includeCaptions=false does not create caption artifacts when generation is not called"),
    ]

    result = generate_source_captions_from_asr(asr_json, run_dir / "captions")
    vtt_path = run_dir / "captions" / "source_original.vtt"
    srt_path = run_dir / "captions" / "source_original.srt"
    vtt = vtt_path.read_text(encoding="utf-8") if vtt_path.is_file() else ""
    srt = srt_path.read_text(encoding="utf-8") if srt_path.is_file() else ""

    checks.extend(
        [
            _assert(result.generated, "includeCaptions=true creates caption artifacts"),
            _assert(vtt_path.is_file(), "WebVTT file exists"),
            _assert(srt_path.is_file(), "SRT file exists"),
            _assert(vtt.startswith("WEBVTT\n"), "Generated .vtt starts with WEBVTT"),
            _assert("00:00:00.000 --> 00:00:01.250" in vtt, "Generated .vtt has valid timestamps"),
            _assert("1\n00:00:00,000 --> 00:00:01,250" in srt, "Generated .srt has numbered cues"),
            _assert("2\n00:00:02,000 --> 00:00:04,500" in srt, "Empty segment text is skipped without breaking numbering"),
            _assert(
                "&lt;tags&gt;" in vtt and "arrow" in vtt and "-&gt; marker" in vtt and "arrow --> marker" not in vtt,
                "WebVTT cue text is escaped/sanitized",
            ),
            _assert(result.cue_count == 2, "Only non-empty valid timestamped segments become cues"),
        ]
    )

    missing = generate_source_captions_from_asr(run_dir / "missing.json", run_dir / "missing_captions")
    checks.append(_assert(not missing.generated and bool(missing.warnings), "Missing ASR JSON is handled gracefully"))

    ok = all(item["ok"] for item in checks)
    return {
        "ok": ok,
        "output_dir": str(run_dir),
        "vtt_path": str(vtt_path),
        "srt_path": str(srt_path),
        "cue_count": result.cue_count,
        "warnings": result.warnings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source-language caption generation.")
    parser.add_argument("--output-dir", default="outputs/validation", help="Directory for temporary validation artifacts.")
    parser.add_argument("--report", default="", help="Optional JSON report path.")
    args = parser.parse_args()

    report = run_validation(Path(args.output_dir))
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
