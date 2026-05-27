# Responsible AI & Provenance Engine Plan

Date: 2026-05-06

## 1. Current Pipeline Integration Points

The backend currently runs upload, audio preparation, ASR, translation, voice generation, audio validation, lip-sync/mux, output validation, metrics evaluation, and result assembly. Durable job metadata already exists in `job_manifest.json`, and status/result API payloads already expose `metrics`, `analysis`, `metricsReport`, and manifest summaries. The frontend surfaces these on upload, pipeline, results, and differentiators pages.

The new engine should attach to the same artifact-driven pattern:

- At job creation: initialize a `compliance` folder, audit ledger, consent record, SGI classification, and abuse-risk report.
- After route selection: update SGI/consent context with XTTS vs Sarvam, reference audio, managed TTS, and cloning/speaker-reference status.
- After final MP4 exists: generate disclosure report, provenance sidecar, hashes/fingerprints, retention policy, audit events, and compliance passport.
- On failure: preserve partial artifacts and write a failure audit event without hiding the pipeline error.

## 2. Responsible AI Architecture

The engine is a stdlib-only package under `compliance/` with report-only default behavior. It generates evidence sidecars and warnings while preserving French XTTS and Kannada IndicTrans2 + Sarvam execution.

Default config:

```text
VIDIOLINGUA_ENABLE_RESPONSIBLE_AI=true
VIDIOLINGUA_COMPLIANCE_MODE=report_only
VIDIOLINGUA_REQUIRE_SPEAKER_CONSENT=false
VIDIOLINGUA_APPLY_VISIBLE_DISCLOSURE=false
VIDIOLINGUA_APPLY_AUDIO_DISCLOSURE=false
VIDIOLINGUA_EMBED_PROVENANCE_METADATA=true
VIDIOLINGUA_GENERATE_COMPLIANCE_PASSPORT=true
VIDIOLINGUA_BLOCK_HIGH_RISK_SGI=false
VIDIOLINGUA_RETENTION_DAYS=30
```

Strict mode is opt-in and may block missing speaker consent for speaker-reference jobs, high-risk abuse reports, or missing disclosure/provenance before export.

## 3. Legal / Ethical Research Summary

The research file `docs/RESPONSIBLE_AI_PROVENANCE_RESEARCH_2026-05-06.md` verifies sources for:

- India SGI/deepfake/IT Rules developments and official misinformation/impersonation concern.
- DPDP Act and DPDP Rules themes: data minimization, notices, consent withdrawal, erasure, breach handling.
- CERT-In incident/log evidence context.
- C2PA as a content provenance standard.
- NIST synthetic content transparency and GAI risk management.
- FTC voice cloning impersonation and fraud risk.

The feature will be described as responsible AI and provenance readiness, not as legal certification.

## 4. Backend Modules To Create

```text
compliance/
  __init__.py
  schemas.py
  consent_registry.py
  sgi_classifier.py
  abuse_risk_checks.py
  synthetic_disclosure.py
  provenance_manifest.py
  watermarking.py
  fingerprinting.py
  audit_ledger.py
  retention_policy.py
  compliance_passport.py
```

## 5. Report Schemas

Reports are JSON sidecars under `<job_dir>/compliance/`:

- `consent_record.json`
- `sgi_risk_report.json`
- `abuse_risk_report.json`
- `synthetic_disclosure_report.json`
- `provenance_manifest.json`
- `fingerprint_report.json`
- `audit_ledger.jsonl`
- `retention_policy.json`
- `compliance_passport.json`
- `compliance_passport.md`

Schemas are documented separately in `docs/COMPLIANCE_PASSPORT_SCHEMA_2026-05-06.md`.

## 6. Consent Flow

Upload accepts optional consent fields:

- rights/permission confirmation
- speaker consent for speaker-reference jobs
- intended use
- commercial-use allowed
- retention days

The backend records only booleans, scope, allowed languages, retention, self-declaration/admin verification status, and notes. It does not store raw biometric embeddings, unnecessary personal details, or secrets. Sarvam managed TTS marks speaker-reference consent as not applicable where no reference voice is used.

## 7. SGI Risk Classification Strategy

The classifier is rule-based and non-legal:

- XTTS speaker-reference dubbing: medium/high to high SGI likelihood.
- Sarvam managed TTS: synthetic audio true, exact speaker cloning false.
- Lip-sync/visual modification: raises risk.
- Final MP4 replacing audio: requires disclosure and provenance.
- Subtitles-only would be lower risk, but current pipeline creates synthetic audio.

## 8. Abuse-Risk Strategy

The first pass is a conservative keyword/rule-based checker over filename, purpose, transcript, and translation. It flags impersonation, fake emergencies, financial-transfer fraud, government/certificate/order language, elections, non-consensual intimate/sexual content, minors, forged documents, and violence/public-order deception.

Report-only mode emits warnings. Strict mode can block high-risk jobs.

## 9. Disclosure / Watermarking Strategy

Default disclosure is metadata-only:

```text
AI-generated dubbed audio / synthetic localization
```

Visible disclosure uses ffmpeg `drawtext` only when explicitly enabled and writes a new `compliance/disclosed_output.mp4`; it never overwrites final outputs or protected proof artifacts. Audio disclosure remains disabled by default and only reported as future/strict-mode capable.

## 10. Provenance / Fingerprint Strategy

The system writes a C2PA-style JSON sidecar with input/output hashes, route evidence, report links, disclosure text, and `c2pa_status=sidecar_only_not_signed`. Fingerprinting computes SHA-256 hashes, sizes, and ffprobe durations when available. Perceptual hashes are marked unavailable without dependency.

## 11. API / Frontend Integration Plan

Status/result payloads receive:

```json
{
  "responsibleAI": {
    "enabled": true,
    "mode": "report_only",
    "passportStatus": "report_only",
    "sgiRiskLevel": "medium",
    "syntheticVoiceUsed": true,
    "speakerConsentRecorded": null,
    "visibleDisclosureApplied": false,
    "provenanceManifestCreated": true,
    "hashesGenerated": true,
    "auditLedgerCreated": true,
    "safeForDemoExport": true,
    "warningsCount": 0,
    "errorsCount": 0,
    "passportPath": "...",
    "provenancePath": "..."
  }
}
```

No arbitrary file serving is added in this phase.

## 12. Differentiators Page Integration Plan

`NEW_Frontend/app/differentiators/page.tsx` will get a new major section directly below the full HuBERT/prosody section, with no separate Responsible AI page. The section will include:

- real problem and motivation
- verified source cards
- defense-in-depth architecture
- generated artifact list
- compliance passport preview
- "what this is / is not"
- roadmap

The top grid gets an anchor link card for `#responsible-ai-provenance`.

## 13. Protection Of Existing Working Paths

The implementation is additive and does not:

- run the full video pipeline
- load IndicF5 locally
- enable IndicF5
- install dependencies
- mutate virtual environments
- touch `models/xtts_v2`
- overwrite known-good French/Kannada/proof outputs
- expose Sarvam secrets
- add generic fallback
- introduce Indic Parler

Validation reads protected Kannada output and writes to `outputs/validation/responsible_ai_compliance_test`.

## 14. Validation Plan

Run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation prosody compliance
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_compliance_passport --job-dir outputs\kannada_sarvam_practical_test_clipfix --output outputs\validation\responsible_ai_compliance_test --mode report_only
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\responsible_ai_router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\responsible_ai_router_fr.wav --dry-run
corepack pnpm run lint
corepack pnpm run build
```

## 15. Risks And Rollback Notes

- Rule-based abuse checks are a first-pass guardrail only.
- Provenance is sidecar-only, not signed C2PA.
- Visible labels can be removed by editing.
- Metadata can be stripped by platforms.
- Consent records are self-declaration unless an admin verification process is later added.
- Retention policy metadata does not delete files in this phase.

Rollback is straightforward: disable `VIDIOLINGUA_ENABLE_RESPONSIBLE_AI`, remove frontend display references, and leave generated compliance sidecars as inert artifacts.
