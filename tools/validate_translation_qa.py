"""Validate translation QA on existing source and translation JSON artifacts."""

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
from translation.validation.translation_quality import analyze_translation_segments, build_translation_qa_summary


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
    text = data.get("text")
    return [{"id": "0", "text": str(text or "")}]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VideoLingua translation QA on existing JSON files.")
    parser.add_argument("--source-json", required=True, help="ASR/source transcript JSON.")
    parser.add_argument("--translation-json", required=True, help="Translated segment JSON.")
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--glossary", default=None, help="Optional glossary JSON.")
    parser.add_argument("--output", default=None, help="Optional output report path.")
    parser.add_argument("--context-window-size", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    source_data = _read_json(args.source_json)
    translation_data = _read_json(args.translation_json)
    glossary = load_glossary(args.glossary) if args.glossary else None
    report = analyze_translation_segments(
        _segments(source_data),
        _segments(translation_data),
        args.source_language,
        args.target_language,
        glossary=glossary,
        context_window_size=args.context_window_size,
        enable_post_edit=False,
        translation_engine=translation_data.get("translation_engine"),
        domain=(glossary or {}).get("domain") if isinstance(glossary, dict) else None,
        update_memory=False,
    )
    payload = report.to_dict()
    summary = build_translation_qa_summary(payload, Path(args.output).name if args.output else None)
    payload["summary"] = summary
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Translation QA report written: {out}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(
        "Translation QA: "
        f"status={report.status} "
        f"segments={report.segment_count_source}/{report.segment_count_translated} "
        f"warnings={len(report.warnings)} errors={len(report.errors)}"
    )
    return 1 if report.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
