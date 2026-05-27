# Responsible AI & Provenance Engine Report

Date: 2026-05-06

## Implemented

Added a stdlib-only backend package under `compliance/` that generates responsible AI evidence packages for dubbing jobs:

- consent evidence
- synthetic media / SGI risk classification
- first-pass abuse and impersonation guardrail
- synthetic disclosure report
- optional visible disclosure copy
- C2PA-style provenance sidecar
- SHA-256 fingerprint report
- append-only audit ledger
- retention metadata
- Synthetic Media Compliance Passport JSON and Markdown

Default mode is `report_only`. Strict mode is opt-in through `VIDIOLINGUA_COMPLIANCE_MODE=strict`.

## Pipeline Integration

`backend/pipeline_runner.py` now creates/updates compliance artifacts:

- preliminary package after upload/routing context
- translation-stage package after transcript/translation evidence exists
- final package after output validation and final MP4 discovery
- partial package on pipeline failure when possible

The integration is additive and does not change XTTS, IndicTrans2, Sarvam, lip-sync, metrics, or fallback routing.

## API Integration

`backend/main.py` accepts `responsibleAIConsent` form data. `backend/job_store.py` exposes a compact `responsibleAI` status/result object. `evaluation/report_builder.py` includes a `responsible_ai` section when compliance artifacts are present.

## Frontend Integration

The upload page includes a responsible AI consent block. Pipeline/results pages surface mode, SGI risk, consent, disclosure, provenance, hashes, passport status, safe-for-demo/export, warnings, and errors.

The differentiators page has a major `Responsible AI & Provenance Engine` section below the HuBERT/prosody section and a top-grid implemented card linking to the same-page anchor.

## Validation Result

Command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_compliance_passport --job-dir outputs\kannada_sarvam_practical_test_clipfix --output outputs\validation\responsible_ai_compliance_test --mode report_only
```

Result:

- passport status: `report_only`
- SGI risk level: `high`
- abuse risk status: `passed`
- synthetic voice used: `true`
- managed TTS used: `true`
- provenance manifest created: `true`
- hashes generated: `true`
- audit ledger created: `true`
- safe for demo/export: `true`
- warnings: `1`
- errors: `0`

Validation output:

```text
outputs\validation\responsible_ai_compliance_test\compliance
```

## Legal / Ethical Positioning

This is responsible AI and provenance readiness. It is not legal advice, legal certification, C2PA certification, tamper-proof watermarking, identity proof, or guaranteed abuse prevention.

## Limitations

- Abuse checks are rule-based and can miss misuse.
- Provenance is sidecar-only and unsigned.
- Visible disclosure is optional and removable by editing.
- Metadata can be stripped.
- Consent is self-declaration unless an external verification workflow is added.
- Retention policy metadata does not delete files yet.
