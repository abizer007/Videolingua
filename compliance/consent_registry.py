"""Consent evidence records for dubbing jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance.schemas import env_int, new_id, parse_boolish, utc_now, write_json


def normalize_consent_fields(fields: dict[str, Any] | None) -> dict[str, Any]:
    fields = fields or {}
    intended_use = str(fields.get("intended_use") or fields.get("intendedUse") or "internal_demo").strip() or "internal_demo"
    scope = fields.get("consent_scope") or fields.get("consentScope") or ["voice_dubbing", "translation", intended_use]
    if isinstance(scope, str):
        scope = [item.strip() for item in scope.split(",") if item.strip()]
    return {
        "speaker_consent": parse_boolish(fields.get("speaker_consent", fields.get("speakerConsent"))),
        "content_owner_confirmation": parse_boolish(
            fields.get("content_owner_confirmation", fields.get("contentOwnerConfirmation"))
        ),
        "consent_scope": list(dict.fromkeys(str(item) for item in (scope or []) if str(item).strip())),
        "commercial_use_allowed": bool(parse_boolish(fields.get("commercial_use_allowed", fields.get("commercialUseAllowed"))) or False),
        "intended_use": intended_use,
        "retention_days": int(fields.get("retention_days") or fields.get("retentionDays") or env_int("VIDIOLINGUA_RETENTION_DAYS", 30)),
        "speaker_identity_verified": str(
            fields.get("speaker_identity_verified") or fields.get("speakerIdentityVerified") or "self_declaration"
        ),
        "notes": [str(note) for note in fields.get("notes", [])] if isinstance(fields.get("notes"), list) else [],
    }


def create_consent_record(
    *,
    job_id: str,
    output_path: str | Path,
    target_languages: list[str],
    consent_fields: dict[str, Any] | None,
    reference_audio_used: bool,
    voice_cloning_or_speaker_reference_used: bool,
    managed_tts_used: bool,
    retention_days: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_consent_fields(consent_fields)
    notes = list(normalized["notes"])
    speaker_consent = normalized["speaker_consent"]
    if managed_tts_used and not voice_cloning_or_speaker_reference_used:
        notes.append("Speaker cloning consent is not applicable because managed TTS was used without a reference voice.")
    if voice_cloning_or_speaker_reference_used and speaker_consent is not True:
        notes.append("Speaker consent was not affirmatively recorded for speaker-reference dubbing.")
    record = {
        "consent_record_id": new_id("consent"),
        "created_at": utc_now(),
        "job_id": job_id,
        "speaker_consent": speaker_consent,
        "content_owner_confirmation": normalized["content_owner_confirmation"],
        "consent_scope": normalized["consent_scope"] or ["voice_dubbing", "translation", "internal_demo"],
        "commercial_use_allowed": normalized["commercial_use_allowed"],
        "intended_use": normalized["intended_use"],
        "languages_allowed": target_languages,
        "retention_days": int(retention_days if retention_days is not None else normalized["retention_days"]),
        "withdrawal_supported": True,
        "speaker_identity_verified": normalized["speaker_identity_verified"],
        "reference_audio_used": bool(reference_audio_used),
        "voice_cloning_or_speaker_reference_used": bool(voice_cloning_or_speaker_reference_used),
        "managed_tts_used": bool(managed_tts_used),
        "stores_raw_biometric_embeddings": False,
        "stores_unnecessary_personal_details": False,
        "notes": sorted(set(notes)),
    }
    write_json(output_path, record)
    return record


def strict_consent_errors(record: dict[str, Any]) -> list[str]:
    if record.get("voice_cloning_or_speaker_reference_used") and record.get("speaker_consent") is not True:
        return ["Strict mode requires speaker_consent=true for speaker-reference dubbing."]
    return []
