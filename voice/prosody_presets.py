"""Prosody preset loading and defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESET = "balanced"


BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
    "balanced": {
        "description": "Moderate pacing and light pause preservation.",
        "xtts": {"temperature": 0.52, "repetition_penalty": 8.5, "max_chars": 180, "crossfade_ms": 25, "punctuation_aware_chunking": True},
        "sarvam": {"pace": 1.0, "temperature": 0.45, "speaker": "shubh"},
        "hubert": {"use_hubert_adapter": True, "min_confidence": "low", "scoring_weight": 0.35},
        "guidance": {"duration_pressure_limit": 1.25, "pause_strength": "light"},
    },
    "expressive": {
        "description": "Slightly higher TTS variation and stronger emphasis hints.",
        "xtts": {"temperature": 0.62, "repetition_penalty": 8.0, "max_chars": 160, "crossfade_ms": 35, "punctuation_aware_chunking": True},
        "sarvam": {"pace": 0.95, "temperature": 0.55, "speaker": "shubh"},
        "hubert": {"use_hubert_adapter": True, "min_confidence": "low", "scoring_weight": 0.45},
        "guidance": {"duration_pressure_limit": 1.2, "pause_strength": "moderate"},
    },
    "broadcast": {
        "description": "Clear, steady delivery with guarded rate changes.",
        "xtts": {"temperature": 0.48, "repetition_penalty": 8.8, "max_chars": 190, "crossfade_ms": 20, "punctuation_aware_chunking": True},
        "sarvam": {"pace": 0.98, "temperature": 0.4, "speaker": "shubh"},
        "hubert": {"use_hubert_adapter": True, "min_confidence": "low", "scoring_weight": 0.35},
        "guidance": {"duration_pressure_limit": 1.18, "pause_strength": "light"},
    },
    "fast_sync": {
        "description": "Tighter duration matching with conservative speed guardrails.",
        "xtts": {"temperature": 0.5, "repetition_penalty": 8.5, "max_chars": 150, "crossfade_ms": 15, "punctuation_aware_chunking": True},
        "sarvam": {"pace": 1.12, "temperature": 0.42, "speaker": "shubh"},
        "hubert": {"use_hubert_adapter": True, "min_confidence": "low", "scoring_weight": 0.3},
        "guidance": {"duration_pressure_limit": 1.1, "pause_strength": "minimal"},
    },
    "calm": {
        "description": "Slower, calmer pacing with wider pauses.",
        "xtts": {"temperature": 0.45, "repetition_penalty": 8.8, "max_chars": 190, "crossfade_ms": 30, "punctuation_aware_chunking": True},
        "sarvam": {"pace": 0.9, "temperature": 0.35, "speaker": "shubh"},
        "hubert": {"use_hubert_adapter": True, "min_confidence": "low", "scoring_weight": 0.3},
        "guidance": {"duration_pressure_limit": 1.3, "pause_strength": "moderate"},
    },
    "presentation": {
        "description": "Measured delivery for technical presentations and narration.",
        "xtts": {"temperature": 0.5, "repetition_penalty": 8.7, "max_chars": 175, "crossfade_ms": 25, "punctuation_aware_chunking": True},
        "sarvam": {"pace": 0.96, "temperature": 0.4, "speaker": "shubh"},
        "hubert": {"use_hubert_adapter": True, "min_confidence": "low", "scoring_weight": 0.35},
        "guidance": {"duration_pressure_limit": 1.22, "pause_strength": "light"},
    },
}


def prosody_engine_enabled() -> bool:
    value = os.environ.get("VIDIOLINGUA_ENABLE_PROSODY_ENGINE", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def hubert_enabled() -> bool:
    value = os.environ.get("VIDIOLINGUA_ENABLE_HUBERT_PROSODY", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def hubert_fails_main_pipeline() -> bool:
    value = os.environ.get("VIDIOLINGUA_HUBERT_FAILS_MAIN_PIPELINE", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def fail_on_prosody_error() -> bool:
    value = os.environ.get("VIDIOLINGUA_PROSODY_FAIL_ON_ERROR", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def selected_preset_name(name: str | None = None) -> str:
    chosen = (name or os.environ.get("VIDIOLINGUA_PROSODY_PRESET", DEFAULT_PRESET)).strip().lower()
    return chosen if chosen in load_presets() else DEFAULT_PRESET


def load_presets(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    presets = dict(BUILTIN_PRESETS)
    config_path = Path(path) if path else PROJECT_ROOT / "config" / "prosody_presets.json"
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            loaded = data.get("presets") if isinstance(data, dict) else data
            if isinstance(loaded, dict):
                for key, value in loaded.items():
                    if isinstance(value, dict):
                        presets[str(key)] = value
        except (OSError, json.JSONDecodeError):
            pass
    return presets


def get_preset(name: str | None = None) -> dict[str, Any]:
    presets = load_presets()
    chosen = (name or os.environ.get("VIDIOLINGUA_PROSODY_PRESET", DEFAULT_PRESET)).strip().lower()
    if chosen not in presets:
        chosen = DEFAULT_PRESET
    return {"name": chosen, **presets[chosen]}
