"""Lightweight JSONL translation memory used as a QA hint layer."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from translation.base import normalize_language_code


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMORY_PATH = PROJECT_ROOT / "translation" / "cache" / "translation_memory.jsonl"


def normalize_source_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def build_memory_key(
    *,
    source_language: str,
    target_language: str,
    source_text: str,
    glossary_hash: str | None = None,
    translation_engine: str | None = None,
    domain: str | None = None,
) -> str:
    payload = {
        "source_language": normalize_language_code(source_language),
        "target_language": normalize_language_code(target_language),
        "source_text_hash": hashlib.sha256(normalize_source_text(source_text).encode("utf-8")).hexdigest(),
        "glossary_hash": glossary_hash,
        "translation_engine": (translation_engine or "").strip().lower() or None,
        "domain": (domain or "").strip().lower() or None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def memory_path_from_env() -> Path:
    return Path(os.environ.get("VIDIOLINGUA_TRANSLATION_MEMORY_PATH", DEFAULT_MEMORY_PATH))


def read_memory(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    memory_file = Path(path) if path else memory_path_from_env()
    if not memory_file.is_file():
        return {}
    entries: dict[str, dict[str, Any]] = {}
    for line in memory_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = item.get("key")
        if isinstance(key, str):
            entries[key] = item
    return entries


def append_memory_entry(
    *,
    key: str,
    source_language: str,
    target_language: str,
    source_text: str,
    translated_text: str,
    quality_status: str,
    translation_engine: str | None = None,
    glossary_hash: str | None = None,
    domain: str | None = None,
    path: str | Path | None = None,
) -> None:
    memory_file = Path(path) if path else memory_path_from_env()
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "key": key,
        "source_language": normalize_language_code(source_language),
        "target_language": normalize_language_code(target_language),
        "source_text_hash": hashlib.sha256(normalize_source_text(source_text).encode("utf-8")).hexdigest(),
        "translated_text": translated_text,
        "quality_status": quality_status,
        "translation_engine": translation_engine,
        "glossary_hash": glossary_hash,
        "domain": domain,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with memory_file.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
