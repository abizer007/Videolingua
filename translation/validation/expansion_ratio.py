"""Translation expansion-ratio heuristics for dubbing pressure."""

from __future__ import annotations

from typing import Any

from translation.base import normalize_language_code


DEFAULT_THRESHOLDS = {
    "default": (0.25, 4.0),
    "kn": (0.20, 5.0),
    "hi": (0.20, 5.0),
    "mr": (0.20, 5.0),
    "ta": (0.20, 5.0),
    "te": (0.20, 5.0),
    "ml": (0.20, 5.0),
    "bn": (0.20, 5.0),
    "gu": (0.20, 5.0),
    "pa": (0.20, 5.0),
    "or": (0.20, 5.0),
}


def thresholds_for_language(target_language: str) -> tuple[float, float]:
    return DEFAULT_THRESHOLDS.get(normalize_language_code(target_language), DEFAULT_THRESHOLDS["default"])


def _word_count(text: str) -> int:
    return len([part for part in (text or "").split() if part.strip()])


def analyze_expansion_ratios(
    source_segments: list[dict[str, Any]],
    translated_segments: list[dict[str, Any]],
    target_language: str,
) -> dict[str, Any]:
    min_ratio, max_ratio = thresholds_for_language(target_language)
    segment_ratios: list[dict[str, Any]] = []
    outliers: list[dict[str, Any]] = []
    source_chars_total = 0
    translated_chars_total = 0
    source_words_total = 0
    translated_words_total = 0
    for index, source_segment in enumerate(source_segments):
        translated_segment = translated_segments[index] if index < len(translated_segments) else {"id": source_segment.get("id"), "text": ""}
        source_text = str(source_segment.get("text") or "").strip()
        translated_text = str(translated_segment.get("text") or "").strip()
        source_chars = len(source_text)
        translated_chars = len(translated_text)
        source_words = _word_count(source_text)
        translated_words = _word_count(translated_text)
        source_chars_total += source_chars
        translated_chars_total += translated_chars
        source_words_total += source_words
        translated_words_total += translated_words
        ratio = translated_chars / max(1, source_chars)
        word_ratio = translated_words / max(1, source_words) if source_words else None
        item = {
            "segment_id": str(source_segment.get("id") or index),
            "source_chars": source_chars,
            "translated_chars": translated_chars,
            "char_ratio": round(ratio, 6),
            "source_words": source_words,
            "translated_words": translated_words,
            "word_ratio": round(word_ratio, 6) if isinstance(word_ratio, float) else None,
        }
        segment_ratios.append(item)
        if source_text and translated_text and (ratio < min_ratio or ratio > max_ratio):
            outliers.append({**item, "reason": "outside language ratio threshold"})
    average_ratio = translated_chars_total / max(1, source_chars_total)
    return {
        "status": "warning" if outliers else "passed",
        "min_ratio": min_ratio,
        "max_ratio": max_ratio,
        "source_chars": source_chars_total,
        "translated_chars": translated_chars_total,
        "source_words": source_words_total,
        "translated_words": translated_words_total,
        "average_char_ratio": round(average_ratio, 6),
        "average_word_ratio": round(translated_words_total / max(1, source_words_total), 6) if source_words_total else None,
        "outlier_segments": outliers,
        "segment_ratios": segment_ratios,
        "dubbing_pressure_warnings": len(outliers),
    }
