"""Validate IndicTrans2 translation execution."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from translation.base import TranslationRequest
from translation.router import translate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate IndicTrans2 translation.")
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = translate(
            TranslationRequest(
                source_text=args.text,
                source_language=args.source_language,
                target_language=args.target_language,
                preferred_engine="indictrans2",
            )
        )
        payload = {"ok": True, **asdict(result)}
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    except Exception as exc:
        payload = {"ok": False, "engine": "indictrans2", "error": str(exc)}
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
