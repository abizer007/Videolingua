"""Validate Sarvam speaker-aware managed-TTS voice planning."""

from __future__ import annotations

import argparse
from pathlib import Path

from speaker_analysis.sarvam_voice_selection import build_sarvam_voice_plan
from speaker_analysis.speaker_mapping import load_json
from speaker_analysis.speaker_profiles import build_speaker_profiles


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Sarvam speaker voice plan from a speaker map.")
    parser.add_argument("--speaker-map", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    profiles = build_speaker_profiles(load_json(args.speaker_map))
    plan = build_sarvam_voice_plan(profiles, target_language=args.target_language, output_path=args.output)
    print(
        "[validate_sarvam_speaker_plan] "
        f"status={plan.get('status')} target_language={plan.get('target_language')} "
        f"speakers={len(plan.get('speakers') or [])} output={Path(args.output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
