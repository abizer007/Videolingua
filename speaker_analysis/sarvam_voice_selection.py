"""Speaker-aware Sarvam managed-TTS voice planning."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_SARVAM_SPEAKER = "shubh"


def _normalize_language(language: str) -> str:
    code = (language or "").strip().lower().replace("_", "-").split("-")[0]
    return "or" if code == "od" else code


def _load_profile_config(path: str | Path | None = None) -> dict[str, Any]:
    raw_path = path or os.environ.get("VIDIOLINGUA_SARVAM_VOICE_PROFILE_CONFIG", "").strip()
    if not raw_path:
        raw_path = Path(__file__).resolve().parents[1] / "config" / "sarvam_voice_profiles.example.json"
    config_path = Path(raw_path)
    if not config_path.is_file():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _manual_overrides() -> dict[str, str]:
    raw = os.environ.get("VIDIOLINGUA_SARVAM_SPEAKER_OVERRIDES_JSON", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if value}


def select_sarvam_voice_for_speaker(
    speaker: dict[str, Any],
    *,
    target_language: str,
    config: dict[str, Any] | None = None,
    default_voice: str | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    language = _normalize_language(target_language)
    speaker_id = str(speaker.get("speaker_id") or "unknown")
    raw_hint = str(speaker.get("voice_profile_hint") or "unknown").strip().lower()
    hint_aliases = {
        "masculine": "masculine_voice_fit",
        "feminine": "feminine_voice_fit",
    }
    hint = hint_aliases.get(raw_hint, raw_hint)
    if hint not in {"masculine_voice_fit", "feminine_voice_fit", "neutral", "unknown"}:
        hint = "unknown"
    confidence = str(speaker.get("confidence") or speaker.get("voice_profile_confidence") or "low").strip().lower()
    hint_source = str(speaker.get("hint_source") or speaker.get("voice_profile_method") or "unknown").strip().lower()
    if hint_source not in {"visual_heuristic", "audio_heuristic", "user_override", "unknown"}:
        hint_source = "unknown"
    config = config or {}
    default_voice = default_voice or os.environ.get("VIDIOLINGUA_SARVAM_SPEAKER", DEFAULT_SARVAM_SPEAKER).strip() or DEFAULT_SARVAM_SPEAKER
    overrides = overrides or {}

    selected = None
    reason = "Sarvam managed TTS voice chosen using current default because no profile-specific supported voice is configured."
    if speaker_id in overrides:
        selected = overrides[speaker_id]
        reason = "Manual Sarvam speaker override selected for this detected speaker."
    else:
        language_map = config.get(language) if isinstance(config.get(language), dict) else {}
        mapped = language_map.get(hint) or language_map.get("unknown")
        if mapped:
            selected = str(mapped)
            reason = (
                "Sarvam managed TTS voice chosen from the target-language unknown/default mapping."
                if hint == "unknown"
                else "Sarvam managed TTS voice chosen using speaker voice-profile hint and target language."
            )
    if not selected:
        selected = default_voice

    return {
        "speaker_id": speaker_id,
        "segment_count": speaker.get("segment_count", 0),
        "total_speech_sec": speaker.get("total_speech_sec", 0.0),
        "reference_audio_path": speaker.get("reference_audio_path"),
        "voice_profile_hint": hint,
        "confidence": confidence if confidence in {"low", "medium", "high"} else "low",
        "hint_source": hint_source,
        "selected_tts_voice": selected,
        "selection_reason": reason,
        "override_supported": True,
        "managed_tts": True,
        "exact_voice_clone": False,
        "sarvam_is_managed_tts_not_cloning": True,
    }


def build_sarvam_voice_plan(
    speaker_profiles: dict[str, Any],
    *,
    target_language: str,
    output_path: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    if speaker_profiles.get("status") != "computed":
        plan = {
            "status": speaker_profiles.get("status", "unavailable"),
            "target_language": _normalize_language(target_language),
            "voice_backend": "sarvam",
            "managed_tts": True,
            "exact_voice_clone": False,
            "speakers": [],
            "warnings": ["Sarvam voice plan unavailable because speaker profiles were not computed."],
            "errors": list(speaker_profiles.get("errors") or []),
        }
        return _write_if_requested(plan, output_path)

    config = _load_profile_config(config_path)
    overrides = _manual_overrides()
    speakers = [
        select_sarvam_voice_for_speaker(
            speaker,
            target_language=target_language,
            config=config,
            overrides=overrides,
        )
        for speaker in speaker_profiles.get("speakers") or []
        if isinstance(speaker, dict)
    ]
    plan = {
        "status": "computed",
        "target_language": _normalize_language(target_language),
        "voice_backend": "sarvam",
        "managed_tts": True,
        "exact_voice_clone": False,
        "speakers": speakers,
        "warnings": [
            "Sarvam is managed TTS, not exact voice cloning.",
            "Voice profile hints are voice-fit suggestions, not identity detection.",
        ],
        "errors": [],
    }
    return _write_if_requested(plan, output_path)


def _write_if_requested(plan: dict[str, Any], output_path: str | Path | None) -> dict[str, Any]:
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return plan
