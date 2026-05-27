"""Deterministic cloned voice cache keys."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from voice.audio_validation import file_sha256
from voice.base import normalize_voice_language


def _optional_file_sha256(path: str | Path | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    return file_sha256(candidate) if candidate.is_file() else None


def build_voice_cache_key(
    *,
    engine_name: str,
    model_name: str,
    target_language: str,
    target_text: str,
    reference_audio_path: str | Path | None,
    reference_text: str | None = None,
    voice_settings: dict[str, Any] | None = None,
    preprocessing_version: str = "voice-v1",
) -> str:
    payload = {
        "engine_name": engine_name,
        "model_name": model_name,
        "target_language": normalize_voice_language(target_language),
        "target_text_sha256": hashlib.sha256((target_text or "").encode("utf-8")).hexdigest(),
        "reference_audio_sha256": _optional_file_sha256(reference_audio_path),
        "reference_text_sha256": hashlib.sha256((reference_text or "").encode("utf-8")).hexdigest()
        if reference_text is not None
        else None,
        "voice_settings": voice_settings or {},
        "preprocessing_version": preprocessing_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

