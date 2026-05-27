"""Translation memory checks for QA reporting."""

from __future__ import annotations

from typing import Any

from translation.cache.translation_memory import build_memory_key, read_memory


def analyze_memory_hits(
    source_segments: list[dict[str, Any]],
    translated_segments: list[dict[str, Any]],
    *,
    source_language: str,
    target_language: str,
    glossary_hash: str | None = None,
    translation_engine: str | None = None,
    domain: str | None = None,
    memory_path: str | None = None,
) -> dict[str, Any]:
    memory = read_memory(memory_path)
    hits: list[dict[str, Any]] = []
    consistency_warnings: list[dict[str, Any]] = []
    for index, source_segment in enumerate(source_segments):
        translated_text = ""
        if index < len(translated_segments):
            translated_text = str(translated_segments[index].get("text") or "")
        key = build_memory_key(
            source_language=source_language,
            target_language=target_language,
            source_text=str(source_segment.get("text") or ""),
            glossary_hash=glossary_hash,
            translation_engine=translation_engine,
            domain=domain,
        )
        item = memory.get(key)
        if not item:
            continue
        hits.append({"segment_id": str(source_segment.get("id") or index), "quality_status": item.get("quality_status")})
        previous = str(item.get("translated_text") or "").strip()
        if previous and translated_text.strip() and previous != translated_text.strip():
            consistency_warnings.append(
                {
                    "segment_id": str(source_segment.get("id") or index),
                    "reason": "translation differs from memory entry",
                }
            )
    return {
        "enabled": True,
        "hits": len(hits),
        "hit_segments": hits,
        "consistency_warning_count": len(consistency_warnings),
        "consistency_warnings": consistency_warnings,
    }
