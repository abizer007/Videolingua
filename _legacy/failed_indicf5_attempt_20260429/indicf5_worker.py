"""IndicF5 worker entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one IndicF5 voice synthesis request.")
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_path = Path(args.request)
    response_path = Path(args.response)
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    try:
        from voice.base import VoiceSynthesisRequest
        from voice.router import synthesize_voice

        result = synthesize_voice(
            VoiceSynthesisRequest(
                text=payload["text"],
                target_language=payload["target_language"],
                output_path=Path(payload["output_path"]),
                reference_audio_path=Path(payload["reference_audio_path"]),
                reference_text=payload["reference_text"],
                preferred_engine="indicf5",
                cloning_required=True,
            )
        )
        response_path.write_text(json.dumps(result.metadata | {"ok": True, "output_path": str(result.output_path)}, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:
        response_path.write_text(json.dumps({"ok": False, "error": str(exc)}, indent=2), encoding="utf-8")
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

