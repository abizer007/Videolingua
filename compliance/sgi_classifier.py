"""Rule-based synthetic media / SGI risk classifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance.schemas import write_json


def classify_sgi_risk(
    *,
    output_path: str | Path,
    target_language: str | None,
    voice_backend: str | None,
    reference_audio_used: bool,
    xtts_speaker_reference_used: bool,
    sarvam_generated_speech: bool,
    lip_sync_or_visual_modification_used: bool,
    final_mp4_replaces_original_audio: bool,
    consent_fields: dict[str, Any] | None = None,
    transcript_text: str = "",
    translated_text: str = "",
) -> dict[str, Any]:
    del transcript_text, translated_text
    backend = (voice_backend or "").strip().lower()
    reasons: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    synthetic_audio = bool(backend in {"xtts", "sarvam"} or sarvam_generated_speech or xtts_speaker_reference_used)
    uses_managed_tts = bool(sarvam_generated_speech or backend == "sarvam")
    uses_reference = bool(reference_audio_used or xtts_speaker_reference_used or backend == "xtts")
    level = "low"

    if synthetic_audio:
        level = "medium"
        reasons.append("The job creates synthetic dubbed audio.")
    if uses_reference:
        level = "high"
        reasons.append("Speaker-reference or voice-cloning style dubbing increases identity and impersonation risk.")
    if uses_managed_tts:
        reasons.append("Managed TTS creates synthetic speech but is not exact speaker cloning by itself.")
        if level == "low":
            level = "medium"
    if lip_sync_or_visual_modification_used:
        level = "high" if level in {"medium", "high"} else "medium"
        reasons.append("Lip-sync or visual modification increases synthetic media risk.")
    if final_mp4_replaces_original_audio:
        reasons.append("The final MP4 replaces or overlays original audio with generated speech.")
    if not (consent_fields or {}).get("content_owner_confirmation") and not (consent_fields or {}).get("contentOwnerConfirmation"):
        warnings.append("Content-owner rights/permission confirmation was not affirmatively recorded.")
    if uses_reference and not ((consent_fields or {}).get("speaker_consent") or (consent_fields or {}).get("speakerConsent")):
        warnings.append("Speaker consent was not affirmatively recorded for a speaker-reference path.")

    report = {
        "sgi_likelihood": level,
        "synthetic_audio": synthetic_audio,
        "synthetic_video_or_visual_modification": bool(lip_sync_or_visual_modification_used),
        "uses_voice_cloning_or_speaker_reference": uses_reference,
        "uses_managed_tts": uses_managed_tts,
        "depicts_real_person": None,
        "target_language": target_language,
        "voice_backend": voice_backend,
        "requires_disclosure": synthetic_audio or bool(lip_sync_or_visual_modification_used),
        "requires_provenance": synthetic_audio or bool(lip_sync_or_visual_modification_used),
        "requires_consent": uses_reference,
        "classification_reasons": reasons,
        "warnings": warnings,
        "errors": errors,
        "legal_conclusion": "not_provided_risk_classification_only",
    }
    write_json(output_path, report)
    return report
