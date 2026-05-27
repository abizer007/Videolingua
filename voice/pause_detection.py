"""Pause detection from ASR segment timing."""

from __future__ import annotations

from typing import Any


def detect_pauses_from_segments(
    segments: list[dict[str, Any]],
    *,
    min_pause_sec: float = 0.18,
) -> list[dict[str, float | int | str]]:
    pauses: list[dict[str, float | int | str]] = []
    previous_end: float | None = None
    previous_index: int | None = None
    for index, segment in enumerate(segments):
        try:
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", start))
        except (TypeError, ValueError):
            continue
        if previous_end is not None:
            gap = max(0.0, start - previous_end)
            if gap >= min_pause_sec:
                pauses.append(
                    {
                        "after_segment_index": previous_index if previous_index is not None else max(0, index - 1),
                        "before_segment_index": index,
                        "start_sec": round(previous_end, 3),
                        "end_sec": round(start, 3),
                        "duration_sec": round(gap, 3),
                        "class": classify_pause(gap),
                    }
                )
        previous_end = max(previous_end or 0.0, end)
        previous_index = index
    return pauses


def classify_pause(duration_sec: float) -> str:
    if duration_sec < 0.25:
        return "micro"
    if duration_sec < 0.7:
        return "short"
    if duration_sec < 1.5:
        return "medium"
    return "long"


def pause_summary(pauses: list[dict[str, object]]) -> dict[str, object]:
    durations = [
        float(item.get("duration_sec", 0.0))
        for item in pauses
        if isinstance(item, dict)
    ]
    total = sum(durations)
    return {
        "pause_count": len(durations),
        "average_pause_sec": round(total / len(durations), 3) if durations else 0.0,
        "total_pause_sec": round(total, 3),
        "long_pause_count": sum(1 for value in durations if value >= 1.5),
    }
