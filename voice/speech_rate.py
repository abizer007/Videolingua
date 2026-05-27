"""Speech-rate helpers for prosody analysis.

The functions here intentionally use lightweight text/timing features. They do
not infer emotion, and they do not require ASR model dependencies.
"""

from __future__ import annotations

import re
from typing import Any


WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def segment_duration(segment: dict[str, Any]) -> float:
    try:
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, end - start)


def words_per_minute(words: int, duration_sec: float) -> float | None:
    if duration_sec <= 0:
        return None
    return (float(words) / duration_sec) * 60.0


def classify_rate(wpm: float | None) -> str:
    if wpm is None:
        return "unknown"
    if wpm < 105:
        return "slow"
    if wpm <= 170:
        return "balanced"
    if wpm <= 220:
        return "fast"
    return "rushed"


def rate_similarity(source_wpm: float | None, target_wpm: float | None) -> float | None:
    if source_wpm is None or target_wpm is None or source_wpm <= 0 or target_wpm <= 0:
        return None
    ratio = min(source_wpm, target_wpm) / max(source_wpm, target_wpm)
    return max(0.0, min(1.0, ratio))
