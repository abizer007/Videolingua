"""Schema helpers for Vidiolingua prosody profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PROSODY_PROFILE_SCHEMA_VERSION = 1
PROSODY_ENGINE_VERSION = "prosody-elocution-2026-05-05"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SegmentProsody:
    segment_id: str
    index: int
    start_sec: float
    end_sec: float
    duration_sec: float
    text: str
    word_count: int
    speech_rate_wpm: float | None
    rate_class: str
    energy_class: str
    average_rms: float | None
    peak_rms: float | None
    emphasis_hints: list[str] = field(default_factory=list)
    punctuation_style: str = "statement"

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "index": self.index,
            "start_sec": round(self.start_sec, 3),
            "end_sec": round(self.end_sec, 3),
            "duration_sec": round(self.duration_sec, 3),
            "text": self.text,
            "word_count": self.word_count,
            "speech_rate_wpm": round(self.speech_rate_wpm, 3) if self.speech_rate_wpm is not None else None,
            "rate_class": self.rate_class,
            "energy_class": self.energy_class,
            "average_rms": round(self.average_rms, 6) if self.average_rms is not None else None,
            "peak_rms": round(self.peak_rms, 6) if self.peak_rms is not None else None,
            "emphasis_hints": self.emphasis_hints,
            "punctuation_style": self.punctuation_style,
        }


def base_profile(*, source_audio_path: str, asr_json_path: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": PROSODY_PROFILE_SCHEMA_VERSION,
        "engine": "Prosody & Elocution Engine",
        "engine_version": PROSODY_ENGINE_VERSION,
        "created_at": utc_now(),
        "source_audio_path": source_audio_path,
        "asr_json_path": asr_json_path,
        "global": {},
        "pauses": [],
        "energy_profile": {},
        "pitch_profile": {
            "status": "unavailable",
            "reason": "Pitch/F0 extraction is not enabled in the lightweight stdlib analyzer.",
        },
        "intonation_proxy": {},
        "emotion_tone_proxy": {
            "status": "heuristic_only",
            "note": "Tone hints are derived from timing, punctuation, and energy only; no emotion classifier is used.",
        },
        "segments": [],
        "summary": {},
        "warnings": [],
        "errors": [],
    }
