"""Validate HuBERT feature extraction through the isolated worker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice.hubert_prosody import DEFAULT_MODEL, extract_hubert_features, prosody_python


def _segments(asr_json: str | None) -> list[dict]:
    if not asr_json:
        return []
    data = json.loads(Path(asr_json).read_text(encoding="utf-8"))
    raw = data.get("segments") if isinstance(data, dict) else []
    return [item for item in raw if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract HuBERT embeddings for an audio/video file.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--asr-json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    py = prosody_python()
    if py:
        print(f"HuBERT worker call: {py} workers\\hubert_prosody_worker.py --request <request.json> --response <hubert_features.json>")
    response = extract_hubert_features(
        audio_path=args.audio,
        segments=_segments(args.asr_json),
        output_dir=args.output_dir,
        model_name=args.model_name,
        device=args.device,
    )
    print(json.dumps(response, indent=2, ensure_ascii=False))
    return 0 if response.get("status") == "computed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
