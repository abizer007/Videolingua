"""Lightweight speaker-analysis helpers for ASR output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def analyze_speakers_from_asr(asr_json_paths: list[str | Path]) -> dict[str, Any]:
    """Return honest speaker status from ASR/diarization JSON files.

    This does not infer speaker count from faces, channel count, or defaults. A
    numeric count is returned only when the ASR output contains speaker labels.
    """
    labels: set[str] = set()
    segment_count = 0
    readable_files = 0
    malformed_files = 0
    diarization_reasons: list[str] = []
    diarization_statuses: list[str] = []

    for raw_path in asr_json_paths:
        path = Path(raw_path)
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            malformed_files += 1
            continue

        readable_files += 1
        diarization = data.get("diarization")
        if isinstance(diarization, dict):
            reason = str(diarization.get("reason") or "").strip()
            status = str(diarization.get("status") or "").strip()
            if status:
                diarization_statuses.append(status)
            if reason:
                diarization_reasons.append(reason)
            elif status:
                diarization_reasons.append(f"Diarization status: {status}.")
        segments = data.get("segments")
        if not isinstance(segments, list):
            continue
        segment_count += len(segments)
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            speaker = str(segment.get("speaker") or "").strip()
            if speaker:
                labels.add(speaker)

    if labels:
        return {
            "status": "computed",
            "speakers_detected": len(labels),
            "source": "asr_segments",
            "reason": "ASR output contains speaker labels.",
            "segment_count": segment_count,
            "speaker_labels": sorted(labels),
        }

    if readable_files and segment_count > 0:
        failed = any(status == "failed" for status in diarization_statuses)
        unavailable = any(status in {"unavailable", "not_available"} for status in diarization_statuses)
        return {
            "status": "failed" if failed else "unavailable" if unavailable else "not_run",
            "speakers_detected": None,
            "source": None,
            "reason": diarization_reasons[0] if diarization_reasons else "Diarization was not enabled for this job or produced no speaker labels.",
            "segment_count": segment_count,
            "speaker_labels": [],
        }

    return {
        "status": "not_determined",
        "speakers_detected": None,
        "source": None,
        "reason": (
            "No readable ASR speaker evidence was found."
            if malformed_files == 0
            else "ASR speaker evidence could not be read."
        ),
        "segment_count": segment_count,
        "speaker_labels": [],
    }
