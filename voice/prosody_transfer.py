"""Practical cross-lingual prosody guidance for TTS preparation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from voice.prosody_presets import get_preset
from voice.speech_rate import count_words, words_per_minute


SENTENCE_END_RE = re.compile(r"[.!?।!?]$")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _segment_text(segment: dict[str, Any]) -> str:
    return str(segment.get("text") or segment.get("translation") or "").strip()


def _prepared_text(text: str, source_style: str, pause_after_sec: float | None) -> str:
    prepared = (text or "").strip()
    if not prepared:
        return prepared
    if source_style == "question" and not prepared.endswith("?"):
        prepared = prepared.rstrip(".।!") + "?"
    elif source_style == "exclamation" and not prepared.endswith("!"):
        prepared = prepared.rstrip(".।?") + "!"
    elif not SENTENCE_END_RE.search(prepared):
        prepared = prepared + "."
    if pause_after_sec and pause_after_sec >= 0.7:
        prepared = prepared + " "
    return prepared


def _pace_for_pressure(voice_backend: str, pressure: float, base_pace: float) -> float:
    backend = (voice_backend or "").lower()
    if pressure <= 1.05:
        return base_pace
    if backend == "sarvam":
        return max(0.85, min(1.18, base_pace * min(1.12, pressure)))
    return max(0.9, min(1.1, base_pace * min(1.08, pressure)))


def build_tts_prosody_plan(
    prosody_profile: dict[str, Any],
    translation_payload: dict[str, Any],
    *,
    target_language: str,
    voice_backend: str,
    preset_name: str | None = None,
    output_path: str | Path | None = None,
    hubert_source_reference: str | None = None,
) -> dict[str, Any]:
    preset = get_preset(preset_name)
    source_segments = prosody_profile.get("segments") if isinstance(prosody_profile.get("segments"), list) else []
    target_segments = translation_payload.get("segments") if isinstance(translation_payload.get("segments"), list) else []
    pauses = prosody_profile.get("pauses") if isinstance(prosody_profile.get("pauses"), list) else []
    pause_after: dict[int, float] = {}
    for pause in pauses:
        if isinstance(pause, dict):
            idx = pause.get("after_segment_index")
            if isinstance(idx, int):
                pause_after[idx] = _safe_float(pause.get("duration_sec"))

    backend_key = "sarvam" if voice_backend.lower() == "sarvam" else "xtts"
    backend_controls = dict(preset.get(backend_key, {}))
    base_pace = _safe_float(backend_controls.get("pace"), 1.0)
    warnings: list[str] = []
    planned_segments: list[dict[str, Any]] = []
    total_source_duration = 0.0
    total_target_words = 0

    for index, target in enumerate(target_segments):
        if not isinstance(target, dict):
            continue
        source = source_segments[index] if index < len(source_segments) and isinstance(source_segments[index], dict) else {}
        text = _segment_text(target)
        source_duration = _safe_float(source.get("duration_sec") or (_safe_float(target.get("end")) - _safe_float(target.get("start"))), 0.0)
        target_words = count_words(text)
        estimated_target_wpm = words_per_minute(target_words, source_duration) if source_duration else None
        source_wpm = source.get("speech_rate_wpm")
        try:
            source_wpm_value = float(source_wpm) if source_wpm is not None else None
        except (TypeError, ValueError):
            source_wpm_value = None
        pressure = 1.0
        if estimated_target_wpm and source_wpm_value and source_wpm_value > 0:
            pressure = max(0.1, estimated_target_wpm / source_wpm_value)
        duration_pressure = "normal"
        if pressure > 1.35:
            duration_pressure = "high"
            warnings.append(f"Segment {index} has high duration pressure ({pressure:.2f}x).")
        elif pressure > 1.12:
            duration_pressure = "moderate"
        source_style = str(source.get("punctuation_style") or "statement")
        prepared = _prepared_text(text, source_style, pause_after.get(index))
        planned_segments.append(
            {
                "segment_id": str(target.get("segment_id") or target.get("id") or index),
                "index": index,
                "source_duration_sec": round(source_duration, 3),
                "target_word_count": target_words,
                "source_speech_rate_wpm": round(source_wpm_value, 3) if source_wpm_value is not None else None,
                "estimated_target_wpm": round(estimated_target_wpm, 3) if estimated_target_wpm is not None else None,
                "duration_pressure_ratio": round(pressure, 3),
                "duration_pressure": duration_pressure,
                "recommended_pace": round(_pace_for_pressure(voice_backend, pressure, base_pace), 3),
                "pause_after_sec": round(pause_after[index], 3) if index in pause_after else 0.0,
                "punctuation_strategy": source_style,
                "emphasis_strategy": source.get("emphasis_hints") or [],
                "tts_prepared_text": prepared,
            }
        )
        total_source_duration += source_duration
        total_target_words += target_words

    max_pressure = max((item["duration_pressure_ratio"] for item in planned_segments), default=1.0)
    recommended_pace = _pace_for_pressure(voice_backend, max_pressure, base_pace)
    controls_used = {
        **backend_controls,
        "pace": round(recommended_pace, 3) if backend_key == "sarvam" else backend_controls.get("pace"),
        "preset": preset["name"],
    }
    plan = {
        "schema_version": 1,
        "engine": "Prosody & Elocution Engine",
        "preset": preset["name"],
        "target_language": target_language,
        "voice_backend": voice_backend,
        "status": "computed",
        "global": {
            "source_speech_rate_wpm": prosody_profile.get("global", {}).get("speech_rate_wpm") if isinstance(prosody_profile.get("global"), dict) else None,
            "source_speech_rate_class": prosody_profile.get("global", {}).get("speech_rate_class") if isinstance(prosody_profile.get("global"), dict) else None,
            "pause_count": prosody_profile.get("global", {}).get("pause_count") if isinstance(prosody_profile.get("global"), dict) else None,
            "max_duration_pressure_ratio": round(max_pressure, 3),
            "duration_pressure": "high" if max_pressure > 1.35 else "moderate" if max_pressure > 1.12 else "normal",
            "recommended_pace": round(recommended_pace, 3),
            "estimated_target_words": total_target_words,
            "source_duration_sec": round(total_source_duration, 3),
        },
        "backend_controls": controls_used,
        "pause_insertion_plan": [
            {"after_segment_index": key, "duration_sec": round(value, 3), "strategy": "preserve_lightly"}
            for key, value in sorted(pause_after.items())
        ],
        "segments": planned_segments,
        "hubert": {
            "source_embedding_reference": hubert_source_reference,
            "used_for_guidance": bool(hubert_source_reference),
            "note": "HuBERT references guide validation/similarity; black-box TTS prosody control remains limited.",
        },
        "warnings": warnings,
        "errors": [],
        "note": "Canonical translation text is unchanged; tts_prepared_text is an optional delivery hint.",
    }
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan


def apply_plan_to_translation_payload(translation_payload: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(translation_payload, ensure_ascii=False))
    plan_segments = plan.get("segments") if isinstance(plan.get("segments"), list) else []
    segments = updated.get("segments") if isinstance(updated.get("segments"), list) else []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict) or index >= len(plan_segments):
            continue
        plan_segment = plan_segments[index]
        if isinstance(plan_segment, dict):
            segment["tts_prepared_text"] = plan_segment.get("tts_prepared_text") or segment.get("text")
            segment["prosody_guidance"] = {
                "duration_pressure": plan_segment.get("duration_pressure"),
                "duration_pressure_ratio": plan_segment.get("duration_pressure_ratio"),
                "recommended_pace": plan_segment.get("recommended_pace"),
                "pause_after_sec": plan_segment.get("pause_after_sec"),
                "emphasis_strategy": plan_segment.get("emphasis_strategy"),
            }
    updated["prosody_guidance"] = {
        "status": plan.get("status"),
        "preset": plan.get("preset"),
        "voice_backend": plan.get("voice_backend"),
        "plan_path": plan.get("path"),
        "note": plan.get("note"),
    }
    return updated
