"""Run the Phonetic and Ambiguity Resolution Layer on translation JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voice.phonetic_resolution import analyze_phonetic_resolution, build_phonetic_resolution_summary, write_phonetic_resolution_report
from voice.pronunciation_dictionary import load_pronunciation_dictionary


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"JSON file not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {p}")
    return data


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate TTS phonetic preparation.")
    parser.add_argument("--translation-json", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--dictionary", default=None)
    parser.add_argument("--source-json", default=None)
    parser.add_argument("--source-language", default=None)
    parser.add_argument("--output", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    translation_data = _read_json(args.translation_json)
    source_segments = None
    if args.source_json:
        source_data = _read_json(args.source_json)
        source_segments = source_data.get("segments") if isinstance(source_data.get("segments"), list) else None
    dictionary = load_pronunciation_dictionary(args.dictionary, strict=bool(args.dictionary))
    _, report = analyze_phonetic_resolution(
        translation_data,
        target_language=args.target_language,
        dictionary=dictionary,
        source_segments=source_segments,
        source_language=args.source_language,
    )
    payload = report.to_dict()
    payload["summary"] = build_phonetic_resolution_summary(payload, Path(args.output).name if args.output else None)
    if args.output:
        write_phonetic_resolution_report(payload, args.output)
        print(f"Phonetic resolution report written: {args.output}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(
        "Phonetic resolution: "
        f"status={report.status} risk={report.phonetic_risk_score_0_100} "
        f"terms={len(report.terms_detected)} acronyms={len(report.acronyms_detected)} "
        f"warnings={len(report.warnings)} errors={len(report.errors)}"
    )
    return 1 if report.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
