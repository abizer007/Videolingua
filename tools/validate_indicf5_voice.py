"""Validate IndicF5 voice synthesis."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from voice.base import VoiceSynthesisRequest
from voice.router import synthesize_voice


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate IndicF5 voice synthesis.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = synthesize_voice(
            VoiceSynthesisRequest(
                text=args.text,
                target_language=args.language,
                output_path=Path(args.output),
                reference_audio_path=Path(args.reference),
                reference_text=args.reference_text,
                preferred_engine="indicf5",
                cloning_required=True,
            )
        )
        payload = {"ok": True, **asdict(result), "output_path": str(result.output_path)}
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "engine": "indicf5", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

