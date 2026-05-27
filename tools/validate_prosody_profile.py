"""Validate source prosody profile generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice.prosody_analysis import analyze_source_prosody


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a source prosody profile JSON.")
    parser.add_argument("--source-video", required=True)
    parser.add_argument("--asr-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    profile = analyze_source_prosody(args.source_video, asr_json_path=args.asr_json, output_path=args.output)
    print(json.dumps(profile.get("summary", {}), indent=2, ensure_ascii=False))
    return 0 if not profile.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
