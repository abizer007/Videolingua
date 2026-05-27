"""Deterministic translation cache keys."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from translation.base import normalize_language_code


def build_translation_cache_key(
    *,
    engine_name: str,
    model_name: str,
    source_language: str,
    target_language: str,
    source_text: str,
    translation_settings: dict[str, Any] | None = None,
    preprocessing_version: str = "translation-v1",
) -> str:
    payload = {
        "engine_name": engine_name,
        "model_name": model_name,
        "source_language": normalize_language_code(source_language),
        "target_language": normalize_language_code(target_language),
        "source_text_sha256": hashlib.sha256((source_text or "").encode("utf-8")).hexdigest(),
        "translation_settings": translation_settings or {},
        "preprocessing_version": preprocessing_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

