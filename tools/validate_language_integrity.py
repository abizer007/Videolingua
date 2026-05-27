"""Combined linguistic and phonetic integrity validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_linguistic_integrity import main as linguistic_main
from tools.validate_phonetic_resolution import main as phonetic_main


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run linguistic and phonetic validation.")
    parser.add_argument("--source-json", required=True)
    parser.add_argument("--translation-json", required=True)
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--dictionary", default=None)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ling_code = linguistic_main([
        "--source-json", args.source_json,
        "--translation-json", args.translation_json,
        "--source-language", args.source_language,
        "--target-language", args.target_language,
        "--output", str(output_dir / "linguistic_integrity_report.json"),
    ])
    phonetic_args = [
        "--translation-json", args.translation_json,
        "--target-language", args.target_language,
        "--source-json", args.source_json,
        "--source-language", args.source_language,
        "--output", str(output_dir / "phonetic_resolution_report.json"),
    ]
    if args.dictionary:
        phonetic_args.extend(["--dictionary", args.dictionary])
    phonetic_code = phonetic_main(phonetic_args)
    return max(ling_code, phonetic_code)


if __name__ == "__main__":
    raise SystemExit(main())
