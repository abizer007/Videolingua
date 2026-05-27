"""Segment alignment, emptiness, ordering, and merge/loss checks."""

from __future__ import annotations

from typing import Any


def normalize_segment(segment: Any, index: int) -> dict[str, Any]:
    if isinstance(segment, dict):
        out = dict(segment)
        out.setdefault("id", str(index))
        out.setdefault("text", "")
        return out
    return {"id": str(index), "text": str(segment or "")}


def normalize_segments(segments: list[Any] | None) -> list[dict[str, Any]]:
    return [normalize_segment(segment, index) for index, segment in enumerate(segments or [])]


def check_segment_alignment(source_segments: list[Any], translated_segments: list[Any]) -> dict[str, Any]:
    source = normalize_segments(source_segments)
    translated = normalize_segments(translated_segments)
    source_ids = [str(segment.get("id")) for segment in source]
    translated_ids = [str(segment.get("id")) for segment in translated]
    count_match = len(source) == len(translated)
    ordering_match = source_ids[: len(translated_ids)] == translated_ids[: len(source_ids)]
    missing_ids = [sid for sid in source_ids if sid not in translated_ids]
    extra_ids = [tid for tid in translated_ids if tid not in source_ids]
    suspicious_merged = len(translated) < len(source)
    suspicious_split = len(translated) > len(source)
    status = "passed" if count_match and ordering_match else "failed"
    return {
        "status": status,
        "source_count": len(source),
        "translated_count": len(translated),
        "segment_count_match": count_match,
        "ordering_match": ordering_match,
        "missing_ids": missing_ids,
        "extra_ids": extra_ids,
        "suspicious_merged_segments": suspicious_merged,
        "suspicious_split_segments": suspicious_split,
    }


def check_empty_segments(source_segments: list[Any], translated_segments: list[Any]) -> dict[str, Any]:
    source = normalize_segments(source_segments)
    translated = normalize_segments(translated_segments)
    empty_ids: list[str] = []
    for index, source_segment in enumerate(source):
        translated_text = ""
        if index < len(translated):
            translated_text = str(translated[index].get("text") or "")
        if str(source_segment.get("text") or "").strip() and not translated_text.strip():
            empty_ids.append(str(source_segment.get("id") or index))
    translated_empty_count = sum(1 for segment in translated if not str(segment.get("text") or "").strip())
    return {
        "status": "failed" if empty_ids else "passed",
        "source_non_empty_translation_empty_ids": empty_ids,
        "empty_translated_text_count": translated_empty_count,
        "affected_segment_ids": empty_ids,
    }
