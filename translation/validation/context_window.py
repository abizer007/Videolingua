"""Neighbor-aware translation QA heuristics."""

from __future__ import annotations

from collections import Counter
from typing import Any

from translation.validation.entity_preservation import extract_entities


def analyze_context_window(
    source_segments: list[dict[str, Any]],
    translated_segments: list[dict[str, Any]],
    *,
    window_size: int = 2,
    glossary_terms: list[str] | None = None,
) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    translated_texts = [str(segment.get("text") or "").strip() for segment in translated_segments]
    source_texts = [str(segment.get("text") or "").strip() for segment in source_segments]

    for index, text in enumerate(translated_texts):
        if not text and source_texts[index:index + 1] and source_texts[index].strip():
            warnings.append({"segment_id": _segment_id(source_segments, index), "reason": "empty translation inside context window"})
            continue
        start = max(0, index - window_size)
        end = min(len(translated_texts), index + window_size + 1)
        neighbors = [translated_texts[i] for i in range(start, end) if i != index and translated_texts[i]]
        if text and text in neighbors:
            same_source = any(source_texts[i] == source_texts[index] for i in range(start, end) if i != index)
            if not same_source:
                warnings.append(
                    {
                        "segment_id": _segment_id(source_segments, index),
                        "reason": "neighboring unrelated segments share the same translation",
                    }
                )

    entity_first_seen: dict[str, int] = {}
    for index, source_text in enumerate(source_texts):
        for entity in extract_entities(source_text, glossary_terms):
            entity_first_seen.setdefault(entity, index)

    translated_joined_lower = " ".join(translated_texts).lower()
    inconsistent_entities = [
        entity
        for entity, first_index in entity_first_seen.items()
        if first_index < len(source_texts) - 1 and entity.lower() not in translated_joined_lower
    ]
    for entity in inconsistent_entities:
        warnings.append({"entity": entity, "reason": "entity introduced in source context was not found in translated context"})

    counts = Counter(text for text in translated_texts if text)
    repeated_neighbors = sum(1 for value in counts.values() if value > 1)
    return {
        "window_size": window_size,
        "warning_count": len(warnings),
        "warnings": warnings,
        "repeated_translation_groups": repeated_neighbors,
        "context_entity_missing_count": len(inconsistent_entities),
    }


def _segment_id(segments: list[dict[str, Any]], index: int) -> str:
    if index < len(segments):
        return str(segments[index].get("id") if segments[index].get("id") is not None else index)
    return str(index)
