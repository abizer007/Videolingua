"""Validate speaker-to-ASR segment mapping."""

from __future__ import annotations

import argparse
from pathlib import Path

from speaker_analysis.speaker_mapping import load_json, map_speakers_to_asr_segments, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Map diarization JSON to ASR segment JSON.")
    parser.add_argument("--asr-json", required=True)
    parser.add_argument("--diarization-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    mapping = map_speakers_to_asr_segments(load_json(args.asr_json), load_json(args.diarization_json))
    write_json(args.output, mapping)
    print(
        "[validate_speaker_mapping] "
        f"status={mapping.get('status')} speaker_count={mapping.get('speaker_count')} "
        f"segments={mapping.get('segment_count')} unknown={mapping.get('unknown_segment_count')} "
        f"ambiguous={mapping.get('ambiguous_segment_count')} output={Path(args.output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
