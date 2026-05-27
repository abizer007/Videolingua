"""Synthetic Media Compliance Passport orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from compliance.abuse_risk_checks import check_abuse_risk
from compliance.audit_ledger import append_event, ledger_path
from compliance.consent_registry import create_consent_record, strict_consent_errors
from compliance.fingerprinting import generate_fingerprint_report
from compliance.provenance_manifest import generate_provenance_manifest
from compliance.retention_policy import generate_retention_policy
from compliance.schemas import (
    DISCLOSURE_TEXT,
    collect_text_from_json,
    compliance_mode,
    ensure_compliance_dir,
    env_true,
    find_first,
    new_id,
    read_json,
    responsible_ai_enabled,
    utc_now,
    write_json,
)
from compliance.sgi_classifier import classify_sgi_risk
from compliance.synthetic_disclosure import generate_disclosure_report


COMPLIANCE_ARTIFACTS = {
    "consent": "consent_record.json",
    "sgi_risk": "sgi_risk_report.json",
    "abuse_risk": "abuse_risk_report.json",
    "synthetic_disclosure": "synthetic_disclosure_report.json",
    "provenance": "provenance_manifest.json",
    "fingerprint": "fingerprint_report.json",
    "audit_ledger": "audit_ledger.jsonl",
    "retention_policy": "retention_policy.json",
    "compliance_passport": "compliance_passport.json",
    "compliance_passport_markdown": "compliance_passport.md",
}

XTTS_LANGS = {"ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh"}
SARVAM_LANGS = {"bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}


def _first_glob(base: Path, pattern: str) -> Path | None:
    return find_first(sorted(base.glob(pattern)))


def infer_job_artifacts(job_dir: str | Path) -> dict[str, Path | None]:
    job = Path(job_dir)
    return {
        "input_video": find_first([job / "input_video.mp4", job / "results" / "input_video.mp4"]),
        "final_video": _first_glob(job / "results", "*_dubbed_*.mp4") if (job / "results").is_dir() else None,
        "audio": _first_glob(job / "tts" / "output", "*.wav") if (job / "tts" / "output").is_dir() else None,
        "job_manifest": job / "job_manifest.json" if (job / "job_manifest.json").is_file() else None,
        "pipeline_result": job / "pipeline_result.json" if (job / "pipeline_result.json").is_file() else None,
        "translation_qa": _first_glob(job / "translation" / "output", "*translation_qa_report.json") if (job / "translation" / "output").is_dir() else None,
        "linguistic_integrity": _first_glob(job / "translation" / "output", "*linguistic_integrity_report.json") if (job / "translation" / "output").is_dir() else None,
        "phonetic_resolution": _first_glob(job / "tts" / "output", "*phonetic_resolution_report.json") if (job / "tts" / "output").is_dir() else None,
        "prosody": job / "prosody" / "hubert_prosody_report.json" if (job / "prosody" / "hubert_prosody_report.json").is_file() else None,
        "metrics": job / "evaluation" / "metrics_report.json" if (job / "evaluation" / "metrics_report.json").is_file() else None,
        "asr_json": _first_glob(job / "asr" / "output", "*.json") if (job / "asr" / "output").is_dir() else None,
        "translation_json": _first_glob(job / "translation" / "output", "*_transcription_*.json") if (job / "translation" / "output").is_dir() else None,
    }


def _nested_get(data: dict[str, Any] | None, *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _infer_context(job_dir: Path, context: dict[str, Any] | None, artifacts: dict[str, Path | None]) -> dict[str, Any]:
    context = dict(context or {})
    pipeline_result = read_json(artifacts.get("pipeline_result"))
    metrics = read_json(artifacts.get("metrics"))
    manifest = read_json(artifacts.get("job_manifest"))
    target_languages = context.get("target_languages") or context.get("languages")
    if not target_languages:
        target = (
            _nested_get(pipeline_result, "analysis", "run_evidence", "target_language")
            or _nested_get(metrics, "operational", "target_language")
            or _nested_get(manifest, "inputs", "target_language")
        )
        target_languages = [part.strip() for part in str(target or "").split(",") if part.strip()]
    if not target_languages and isinstance((pipeline_result or {}).get("localizedVideos"), list):
        target_languages = [
            str(item.get("language")).strip().lower()
            for item in pipeline_result.get("localizedVideos", [])
            if isinstance(item, dict) and item.get("language")
        ]
    voice_backend = context.get("voice_backend") or _nested_get(pipeline_result, "metrics", "voice_backend") or _nested_get(manifest, "routing", "selected_voice_backend")
    lang_base = str((target_languages or [""])[0]).strip().lower().replace("_", "-").split("-")[0]
    if not voice_backend and lang_base in SARVAM_LANGS:
        voice_backend = "sarvam"
    elif not voice_backend and lang_base in XTTS_LANGS:
        voice_backend = "xtts"
    voice_backend_l = str(voice_backend or "").strip().lower()
    reference_audio_used = bool(context.get("reference_audio_used") or _nested_get(manifest, "inputs", "reference_audio_path"))
    xtts_used = bool(context.get("xtts_speaker_reference_used") or voice_backend_l == "xtts")
    managed_tts = bool(context.get("managed_tts_used") or voice_backend_l == "sarvam")
    final_video = artifacts.get("final_video")
    return {
        **context,
        "target_languages": target_languages or [],
        "target_language": (target_languages or [""])[0] if isinstance(target_languages, list) else str(target_languages or ""),
        "voice_backend": voice_backend,
        "translation_backend": context.get("translation_backend") or _nested_get(pipeline_result, "metrics", "translation_backend") or _nested_get(manifest, "routing", "selected_translation_backend"),
        "asr_backend": context.get("asr_backend") or "configured_asr",
        "reference_audio_used": reference_audio_used,
        "xtts_speaker_reference_used": xtts_used,
        "voice_cloning_or_speaker_reference_used": bool(xtts_used or reference_audio_used and not managed_tts),
        "managed_tts_used": managed_tts,
        "lip_sync_or_visual_modification_used": bool(context.get("lip_sync_or_visual_modification_used", final_video is not None)),
        "final_mp4_replaces_original_audio": bool(context.get("final_mp4_replaces_original_audio", final_video is not None)),
        "multilingual_export": bool(context.get("multilingual_export", False)),
        "consent_fields": context.get("consent_fields") or context.get("responsible_ai_consent") or {},
        "user_purpose": context.get("user_purpose"),
    }


def _path_map(compliance_dir: Path) -> dict[str, Path]:
    return {key: compliance_dir / filename for key, filename in COMPLIANCE_ARTIFACTS.items()}


def _make_passport_markdown(passport: dict[str, Any]) -> str:
    warnings = passport.get("warnings") or []
    warning_text = "\n".join(f"- {item}" for item in warnings[:8]) or "- None recorded."
    return (
        "# Synthetic Media Compliance Passport\n\n"
        f"- Job: `{passport.get('job_id')}`\n"
        f"- Status: `{passport.get('overall_status')}`\n"
        f"- SGI risk level: `{passport.get('sgi_risk_level')}`\n"
        f"- Abuse risk status: `{passport.get('abuse_risk_status')}`\n"
        f"- Speaker consent recorded: `{passport.get('speaker_consent_recorded')}`\n"
        f"- Provenance manifest created: `{passport.get('provenance_manifest_created')}`\n"
        f"- Hashes generated: `{passport.get('hashes_generated')}`\n"
        f"- Visible disclosure applied: `{passport.get('visible_disclosure_applied')}`\n"
        f"- Safe for demo export: `{passport.get('safe_for_demo_export')}`\n\n"
        "## Warnings\n\n"
        f"{warning_text}\n\n"
        "This passport is compliance-readiness evidence. It is not legal advice, legal certification, C2PA certification, or a guarantee against misuse.\n"
    )


def build_responsible_ai_summary(passport: dict[str, Any] | None) -> dict[str, Any]:
    if not passport:
        return {
            "enabled": responsible_ai_enabled(),
            "mode": compliance_mode(),
            "passportStatus": None,
            "message": "Compliance passport will appear for new runs.",
        }
    warnings = passport.get("warnings") or []
    errors = passport.get("errors") or []
    artifacts = passport.get("artifacts") or {}
    return {
        "enabled": True,
        "mode": passport.get("mode") or compliance_mode(),
        "passportStatus": passport.get("overall_status"),
        "sgiRiskLevel": passport.get("sgi_risk_level"),
        "syntheticVoiceUsed": passport.get("synthetic_voice_used"),
        "speakerConsentRecorded": passport.get("speaker_consent_recorded"),
        "visibleDisclosureApplied": passport.get("visible_disclosure_applied"),
        "audioDisclosureApplied": passport.get("audio_disclosure_applied"),
        "provenanceManifestCreated": passport.get("provenance_manifest_created"),
        "hashesGenerated": passport.get("hashes_generated"),
        "auditLedgerCreated": passport.get("audit_ledger_created"),
        "safeForDemoExport": passport.get("safe_for_demo_export"),
        "warningsCount": len(warnings),
        "errorsCount": len(errors),
        "passportPath": artifacts.get("compliance_passport"),
        "provenancePath": artifacts.get("provenance_manifest"),
    }


def generate_compliance_bundle(
    *,
    job_dir: str | Path,
    job_id: str | None = None,
    output_dir: str | Path | None = None,
    context: dict[str, Any] | None = None,
    input_video_path: str | Path | None = None,
    final_video_path: str | Path | None = None,
    audio_path: str | Path | None = None,
    mode: str | None = None,
    raise_on_block: bool = False,
    final: bool = True,
) -> dict[str, Any]:
    if not responsible_ai_enabled():
        return {"enabled": False, "mode": compliance_mode(), "passport": None, "summary": build_responsible_ai_summary(None)}

    job = Path(job_dir)
    job_id = job_id or job.name
    compliance_dir = ensure_compliance_dir(job, output_dir)
    paths = _path_map(compliance_dir)
    mode = "strict" if (mode or compliance_mode()) == "strict" else "report_only"
    artifacts = infer_job_artifacts(job)
    if input_video_path:
        artifacts["input_video"] = Path(input_video_path)
    if final_video_path:
        artifacts["final_video"] = Path(final_video_path)
    if audio_path:
        artifacts["audio"] = Path(audio_path)
    ctx = _infer_context(job, context, artifacts)

    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="job_created", summary="Responsible AI evidence package initialized.")

    transcript_text = ctx.get("transcript_text") or collect_text_from_json(artifacts.get("asr_json"), keys=("text",))
    translated_text = ctx.get("translated_text") or collect_text_from_json(artifacts.get("translation_json"), keys=("translated_text", "translation", "text"))
    retention_days = int((ctx.get("consent_fields") or {}).get("retention_days") or (ctx.get("consent_fields") or {}).get("retentionDays") or 30)

    consent = create_consent_record(
        job_id=job_id,
        output_path=paths["consent"],
        target_languages=[str(item) for item in ctx.get("target_languages") or []],
        consent_fields=ctx.get("consent_fields"),
        reference_audio_used=bool(ctx.get("reference_audio_used")),
        voice_cloning_or_speaker_reference_used=bool(ctx.get("voice_cloning_or_speaker_reference_used")),
        managed_tts_used=bool(ctx.get("managed_tts_used")),
        retention_days=retention_days,
    )
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="consent_record_created", summary="Consent evidence record created.", artifact_path=paths["consent"])

    sgi = classify_sgi_risk(
        output_path=paths["sgi_risk"],
        target_language=ctx.get("target_language"),
        voice_backend=ctx.get("voice_backend"),
        reference_audio_used=bool(ctx.get("reference_audio_used")),
        xtts_speaker_reference_used=bool(ctx.get("xtts_speaker_reference_used")),
        sarvam_generated_speech=bool(ctx.get("managed_tts_used")),
        lip_sync_or_visual_modification_used=bool(ctx.get("lip_sync_or_visual_modification_used")),
        final_mp4_replaces_original_audio=bool(ctx.get("final_mp4_replaces_original_audio")),
        consent_fields=ctx.get("consent_fields"),
        transcript_text=transcript_text,
        translated_text=translated_text,
    )
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="sgi_risk_classified", summary=f"SGI risk classified as {sgi.get('sgi_likelihood')}.", artifact_path=paths["sgi_risk"])

    abuse = check_abuse_risk(
        output_path=paths["abuse_risk"],
        filename=str(artifacts.get("input_video") or job.name),
        target_language=ctx.get("target_language"),
        transcript_text=transcript_text,
        translated_text=translated_text,
        user_purpose=ctx.get("user_purpose"),
        consent_fields=ctx.get("consent_fields"),
        mode=mode,
    )
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="abuse_risk_checked", summary=f"Abuse risk status: {abuse.get('status')}.", artifact_path=paths["abuse_risk"])

    disclosure = generate_disclosure_report(
        output_path=paths["synthetic_disclosure"],
        job_id=job_id,
        final_video_path=artifacts.get("final_video"),
        compliance_dir=compliance_dir,
    )
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="disclosure_generated", summary="Synthetic disclosure report generated.", artifact_path=paths["synthetic_disclosure"])

    reports = {
        "job_manifest": str(artifacts.get("job_manifest")) if artifacts.get("job_manifest") else None,
        "translation_qa": str(artifacts.get("translation_qa")) if artifacts.get("translation_qa") else None,
        "linguistic_integrity": str(artifacts.get("linguistic_integrity")) if artifacts.get("linguistic_integrity") else None,
        "phonetic_resolution": str(artifacts.get("phonetic_resolution")) if artifacts.get("phonetic_resolution") else None,
        "prosody": str(artifacts.get("prosody")) if artifacts.get("prosody") else None,
        "metrics": str(artifacts.get("metrics")) if artifacts.get("metrics") else None,
        "consent": str(paths["consent"]),
        "sgi_risk": str(paths["sgi_risk"]),
        "abuse_risk": str(paths["abuse_risk"]),
        "synthetic_disclosure": str(paths["synthetic_disclosure"]),
    }
    provenance = generate_provenance_manifest(
        output_path=paths["provenance"],
        asset_id=None,
        job_id=job_id,
        input_video_path=artifacts.get("input_video"),
        output_video_path=artifacts.get("final_video"),
        pipeline={
            "asr_backend": ctx.get("asr_backend"),
            "translation_backend": ctx.get("translation_backend"),
            "tts_backend": ctx.get("voice_backend"),
            "voice_backend": ctx.get("voice_backend"),
            "voice_cloning_or_speaker_reference_used": bool(ctx.get("voice_cloning_or_speaker_reference_used")),
            "managed_tts_used": bool(ctx.get("managed_tts_used")),
            "lip_sync_used": bool(ctx.get("lip_sync_or_visual_modification_used")),
            "multilingual_export": bool(ctx.get("multilingual_export")),
        },
        reports=reports,
        disclosure=DISCLOSURE_TEXT,
    )
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="provenance_manifest_created", summary="C2PA-style sidecar provenance manifest created.", artifact_path=paths["provenance"])

    fingerprint = generate_fingerprint_report(
        job_id=job_id,
        output_path=paths["fingerprint"],
        input_video_path=artifacts.get("input_video"),
        output_video_path=artifacts.get("final_video"),
        audio_path=artifacts.get("audio"),
        provenance_manifest_path=paths["provenance"],
        job_manifest_id=str(artifacts.get("job_manifest")) if artifacts.get("job_manifest") else None,
    )
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="fingerprint_generated", summary="Output hashes and basic fingerprints generated.", artifact_path=paths["fingerprint"])

    retention = generate_retention_policy(output_path=paths["retention_policy"], retention_days=retention_days)
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="retention_policy_created", summary="Retention policy metadata created.", artifact_path=paths["retention_policy"])

    warnings = []
    errors = []
    for report in (consent, sgi, abuse, disclosure, provenance, fingerprint, retention):
        warnings.extend(str(item) for item in (report.get("warnings") or []))
        errors.extend(str(item) for item in (report.get("errors") or []))
    errors.extend(strict_consent_errors(consent) if mode == "strict" else [])
    if abuse.get("status") == "blocked":
        errors.extend(abuse.get("blocked_reasons") or [])
    if sgi.get("sgi_likelihood") == "high" and env_true("VIDIOLINGUA_BLOCK_HIGH_RISK_SGI", False):
        errors.append("High SGI risk is blocked by VIDIOLINGUA_BLOCK_HIGH_RISK_SGI=true.")

    overall_status = "blocked" if errors and mode == "strict" else "report_only" if mode == "report_only" else "warning" if warnings else "passed"
    safe_for_demo = not errors and abuse.get("status") != "blocked"
    passport = {
        "passport_id": new_id("passport"),
        "job_id": job_id,
        "created_at": utc_now(),
        "mode": mode,
        "overall_status": overall_status,
        "synthetic_voice_used": bool(sgi.get("synthetic_audio")),
        "speaker_reference_or_voice_cloning_used": bool(sgi.get("uses_voice_cloning_or_speaker_reference")),
        "managed_tts_used": bool(sgi.get("uses_managed_tts")),
        "lip_sync_or_visual_modification_used": bool(sgi.get("synthetic_video_or_visual_modification")),
        "speaker_consent_recorded": consent.get("speaker_consent"),
        "sgi_risk_level": sgi.get("sgi_likelihood"),
        "abuse_risk_status": abuse.get("status"),
        "visible_disclosure_applied": bool(disclosure.get("visible_disclosure_applied")),
        "audio_disclosure_applied": bool(disclosure.get("audio_disclosure_applied")),
        "provenance_manifest_created": Path(paths["provenance"]).is_file(),
        "metadata_embedded": False,
        "watermarking_applied": bool(disclosure.get("visible_disclosure_applied")),
        "hashes_generated": bool(fingerprint.get("input_video_sha256") or fingerprint.get("output_video_sha256")),
        "retention_policy_attached": Path(paths["retention_policy"]).is_file(),
        "audit_ledger_created": ledger_path(compliance_dir).is_file(),
        "safe_for_demo_export": safe_for_demo,
        "warnings": sorted(set(warnings)),
        "errors": sorted(set(errors)),
        "artifacts": {
            "consent_record": str(paths["consent"]),
            "sgi_risk_report": str(paths["sgi_risk"]),
            "abuse_risk_report": str(paths["abuse_risk"]),
            "synthetic_disclosure_report": str(paths["synthetic_disclosure"]),
            "provenance_manifest": str(paths["provenance"]),
            "fingerprint_report": str(paths["fingerprint"]),
            "audit_ledger": str(paths["audit_ledger"]),
            "retention_policy": str(paths["retention_policy"]),
            "compliance_passport": str(paths["compliance_passport"]),
            "compliance_passport_markdown": str(paths["compliance_passport_markdown"]),
        },
        "limitations": [
            "Compliance-readiness evidence only; not legal advice or certification.",
            "C2PA-style sidecar is not signed C2PA.",
            "Rule-based abuse detection is not comprehensive.",
            "Visible disclosure and metadata can be removed downstream.",
        ],
    }
    write_json(paths["compliance_passport"], passport)
    paths["compliance_passport_markdown"].write_text(_make_passport_markdown(passport), encoding="utf-8")
    append_event(compliance_dir=compliance_dir, job_id=job_id, event_type="compliance_passport_created", summary=f"Compliance passport status: {overall_status}.", artifact_path=paths["compliance_passport"])
    append_event(
        compliance_dir=compliance_dir,
        job_id=job_id,
        event_type="job_completed" if final and not errors else "job_failed" if errors else "job_completed",
        summary="Responsible AI evidence package finalized." if final else "Responsible AI preliminary evidence package updated.",
        artifact_path=paths["compliance_passport"],
    )

    if raise_on_block and errors and mode == "strict":
        raise RuntimeError("Responsible AI strict mode blocked the job: " + "; ".join(errors))

    return {
        "enabled": True,
        "mode": mode,
        "compliance_dir": str(compliance_dir),
        "passport": passport,
        "summary": build_responsible_ai_summary(passport),
    }
