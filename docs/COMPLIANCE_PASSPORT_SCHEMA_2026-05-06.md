# Compliance Passport Schema

Date: 2026-05-06

The Responsible AI & Provenance Engine writes sidecars under:

```text
<job_dir>\compliance
```

Validation can also write to an external folder, for example:

```text
outputs\validation\responsible_ai_compliance_test\compliance
```

## Consent Record

File: `consent_record.json`

Key fields: `consent_record_id`, `job_id`, `speaker_consent`, `content_owner_confirmation`, `consent_scope`, `commercial_use_allowed`, `languages_allowed`, `retention_days`, `withdrawal_supported`, `speaker_identity_verified`, `reference_audio_used`, `voice_cloning_or_speaker_reference_used`, `managed_tts_used`, `notes`.

The schema does not store raw biometric embeddings, unnecessary personal details, API keys, or secrets.

## SGI Risk Report

File: `sgi_risk_report.json`

Key fields: `sgi_likelihood`, `synthetic_audio`, `synthetic_video_or_visual_modification`, `uses_voice_cloning_or_speaker_reference`, `uses_managed_tts`, `requires_disclosure`, `requires_provenance`, `requires_consent`, `classification_reasons`, `warnings`, `errors`.

This is a risk classification, not a legal conclusion.

## Abuse Risk Report

File: `abuse_risk_report.json`

Key fields: `status`, `risk_level`, `mode`, `checker_type`, `checks`, `warnings`, `blocked_reasons`, `human_review_recommended`, `limitations`.

The checker is a first-pass rule-based guardrail.

## Synthetic Disclosure Report

File: `synthetic_disclosure_report.json`

Key fields: `visible_disclosure_applied`, `audio_disclosure_applied`, `disclosure_text`, `disclosed_output_path`, `metadata_only_disclosure`, `warnings`, `limitations`.

Visible disclosure is optional and creates `compliance\disclosed_output.mp4` only when enabled. It never overwrites final MP4s.

## Provenance Manifest

File: `provenance_manifest.json`

Key fields: `provenance_manifest_id`, `asset_id`, `job_id`, `synthetic_media`, `disclosure`, `input`, `output`, `pipeline`, `reports`, `c2pa_status`, `warnings`, `limitations`.

Current `c2pa_status` is `sidecar_only_not_signed`.

## Fingerprint Report

File: `fingerprint_report.json`

Key fields: `fingerprint_id`, `input_video_sha256`, `output_video_sha256`, `audio_sha256`, `provenance_manifest_sha256`, `job_manifest_id`, `file_size_bytes`, `duration_sec`, `perceptual_video_hash`, `audio_fingerprint`.

Perceptual hashes are explicitly marked unavailable without dependency.

## Audit Ledger

File: `audit_ledger.jsonl`

One JSON object per event: `event_id`, `timestamp`, `job_id`, `event_type`, `summary`, `artifact_path`, optional `sha256`.

## Retention Policy

File: `retention_policy.json`

Key fields: `retention_policy_id`, `retention_days`, `created_at`, `delete_after`, `applies_to`, `withdrawal_supported`, `deletion_not_implemented_yet`, `notes`.

This phase does not delete files.

## Compliance Passport

Files: `compliance_passport.json`, `compliance_passport.md`

Key fields: `passport_id`, `job_id`, `overall_status`, `synthetic_voice_used`, `speaker_reference_or_voice_cloning_used`, `managed_tts_used`, `lip_sync_or_visual_modification_used`, `speaker_consent_recorded`, `sgi_risk_level`, `abuse_risk_status`, `visible_disclosure_applied`, `audio_disclosure_applied`, `provenance_manifest_created`, `metadata_embedded`, `watermarking_applied`, `hashes_generated`, `retention_policy_attached`, `audit_ledger_created`, `safe_for_demo_export`, `warnings`, `errors`, `artifacts`, `limitations`.

## API Summary

Status and result payloads expose:

```json
{
  "responsibleAI": {
    "enabled": true,
    "mode": "report_only",
    "passportStatus": "report_only",
    "sgiRiskLevel": "high",
    "syntheticVoiceUsed": true,
    "speakerConsentRecorded": null,
    "visibleDisclosureApplied": false,
    "provenanceManifestCreated": true,
    "hashesGenerated": true,
    "auditLedgerCreated": true,
    "safeForDemoExport": true,
    "warningsCount": 1,
    "errorsCount": 0,
    "passportPath": "...",
    "provenancePath": "..."
  }
}
```
