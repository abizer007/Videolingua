"""Map diarized speaker turns onto ASR transcript segments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def map_speakers_to_asr_segments(
    asr_payload: dict[str, Any],
    diarization_payload: dict[str, Any],
    *,
    min_overlap_ratio: float = 0.2,
    ambiguity_ratio: float = 0.2,
) -> dict[str, Any]:
    segments = asr_payload.get("segments") if isinstance(asr_payload, dict) else None
    if not isinstance(segments, list):
        segments = []
    turns = diarization_payload.get("turns") if isinstance(diarization_payload, dict) else None
    if not isinstance(turns, list):
        turns = []

    diarization_status = str(diarization_payload.get("status") or "unavailable")
    if diarization_status != "computed":
        return {
            "status": diarization_status if diarization_status in {"failed", "unavailable"} else "unavailable",
            "segment_count": len(segments),
            "speaker_count": None,
            "segments": [],
            "warnings": ["Speaker-to-ASR mapping unavailable because diarization did not compute speaker turns."],
            "errors": list(diarization_payload.get("errors") or []),
            "recommended_fix": diarization_payload.get("recommended_fix"),
        }

    mapped: list[dict[str, Any]] = []
    warnings: list[str] = []
    unknown_count = 0
    ambiguous_count = 0
    speaker_ids: set[str] = set()

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", start) or start)
        duration = max(0.0, end - start)
        overlaps: dict[str, float] = {}
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            speaker_id = str(turn.get("speaker_id") or "").strip()
            if not speaker_id:
                continue
            amount = _overlap(start, end, float(turn.get("start", 0.0)), float(turn.get("end", 0.0)))
            if amount > 0:
                overlaps[speaker_id] = overlaps.get(speaker_id, 0.0) + amount

        ordered = sorted(overlaps.items(), key=lambda item: item[1], reverse=True)
        best_speaker = ordered[0][0] if ordered else "unknown"
        best_overlap = ordered[0][1] if ordered else 0.0
        ratio = (best_overlap / duration) if duration > 0 else 0.0
        if ratio < min_overlap_ratio:
            best_speaker = "unknown"
            unknown_count += 1
        else:
            speaker_ids.add(best_speaker)

        candidates = [
            {"speaker_id": speaker, "overlap_sec": round(amount, 3), "overlap_ratio": round((amount / duration) if duration > 0 else 0.0, 3)}
            for speaker, amount in ordered
            if duration > 0 and amount / duration >= ambiguity_ratio
        ]
        ambiguous = len(candidates) > 1
        if ambiguous:
            ambiguous_count += 1

        mapped.append(
            {
                "segment_id": str(segment.get("id", index)),
                "start": round(start, 3),
                "end": round(end, 3),
                "text": segment.get("text", ""),
                "speaker_id": best_speaker,
                "speaker_overlap_sec": round(best_overlap, 3),
                "speaker_overlap_ratio": round(ratio, 3),
                "ambiguous": ambiguous,
                "candidate_speakers": candidates,
            }
        )

    if unknown_count:
        warnings.append(f"{unknown_count} ASR segment(s) could not be assigned to a diarized speaker.")
    if ambiguous_count:
        warnings.append(f"{ambiguous_count} ASR segment(s) overlap multiple speakers.")

    return {
        "status": "computed",
        "segment_count": len(mapped),
        "speaker_count": len(speaker_ids),
        "unknown_segment_count": unknown_count,
        "ambiguous_segment_count": ambiguous_count,
        "segments": mapped,
        "warnings": warnings,
        "errors": [],
    }


def apply_mapping_to_asr(asr_payload: dict[str, Any], mapping_payload: dict[str, Any]) -> dict[str, Any]:
    if mapping_payload.get("status") != "computed":
        return asr_payload
    by_id = {str(item.get("segment_id")): item for item in mapping_payload.get("segments", []) if isinstance(item, dict)}
    enriched = dict(asr_payload)
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(asr_payload.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        next_segment = dict(segment)
        mapped = by_id.get(str(segment.get("id", index)))
        if mapped:
            speaker_id = mapped.get("speaker_id") or "unknown"
            next_segment["speaker_id"] = speaker_id
            next_segment["speaker"] = None if speaker_id == "unknown" else speaker_id
            next_segment["speaker_overlap_sec"] = mapped.get("speaker_overlap_sec")
            next_segment["speaker_overlap_ratio"] = mapped.get("speaker_overlap_ratio")
            next_segment["speaker_ambiguous"] = mapped.get("ambiguous")
            next_segment["candidate_speakers"] = mapped.get("candidate_speakers")
        segments.append(next_segment)
    enriched["segments"] = segments
    enriched["speaker_segment_mapping"] = {
        "status": mapping_payload.get("status"),
        "speaker_count": mapping_payload.get("speaker_count"),
        "unknown_segment_count": mapping_payload.get("unknown_segment_count"),
        "ambiguous_segment_count": mapping_payload.get("ambiguous_segment_count"),
    }
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Map diarization turns to ASR segments.")
    parser.add_argument("--asr-json", required=True)
    parser.add_argument("--diarization-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--enriched-asr-output")
    args = parser.parse_args()

    asr_payload = load_json(args.asr_json)
    diarization_payload = load_json(args.diarization_json)
    mapping = map_speakers_to_asr_segments(asr_payload, diarization_payload)
    write_json(args.output, mapping)
    if args.enriched_asr_output:
        write_json(args.enriched_asr_output, apply_mapping_to_asr(asr_payload, mapping))
    return 0 if mapping.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
