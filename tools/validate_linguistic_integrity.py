"""Run the Linguistic Integrity Engine on existing JSON artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from translation.validation.glossary import load_glossary
from translation.validation.linguistic_integrity import analyze_linguistic_integrity, build_linguistic_integrity_summary, write_linguistic_integrity_report


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"JSON file not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {p}")
    return data


def _segments(data: dict[str, Any]) -> list[Any]:
    segments = data.get("segments")
    if isinstance(segments, list):
        return segments
    return [{"id": "0", "text": str(data.get("text") or "")}]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate translation linguistic integrity.")
    parser.add_argument("--source-json", required=True)
    parser.add_argument("--translation-json", required=True)
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--glossary", default=None)
    parser.add_argument("--output", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    source_data = _read_json(args.source_json)
    translation_data = _read_json(args.translation_json)
    glossary = load_glossary(args.glossary) if args.glossary else None
    report = analyze_linguistic_integrity(
        _segments(source_data),
        _segments(translation_data),
        args.source_language,
        args.target_language,
        glossary=glossary,
    )
    payload = report.to_dict()
    payload["summary"] = build_linguistic_integrity_summary(payload, Path(args.output).name if args.output else None)
    if args.output:
        write_linguistic_integrity_report(payload, args.output)
        print(f"Linguistic integrity report written: {args.output}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(
        "Linguistic integrity: "
        f"status={report.status} score={report.score_0_100} severity={report.severity} "
        f"warnings={len(report.warnings)} errors={len(report.errors)}"
    )
    return 1 if report.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
