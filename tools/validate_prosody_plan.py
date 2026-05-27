"""Validate cross-lingual TTS prosody plan generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice.prosody_transfer import build_tts_prosody_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a TTS prosody guidance plan.")
    parser.add_argument("--prosody-profile", required=True)
    parser.add_argument("--translation-json", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--voice-backend", required=True)
    parser.add_argument("--preset", default="balanced")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    profile = json.loads(Path(args.prosody_profile).read_text(encoding="utf-8"))
    translation = json.loads(Path(args.translation_json).read_text(encoding="utf-8"))
    plan = build_tts_prosody_plan(
        profile,
        translation,
        target_language=args.target_language,
        voice_backend=args.voice_backend,
        preset_name=args.preset,
        output_path=args.output,
    )
    print(json.dumps(plan.get("global", {}), indent=2, ensure_ascii=False))
    return 0 if plan.get("status") == "computed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
