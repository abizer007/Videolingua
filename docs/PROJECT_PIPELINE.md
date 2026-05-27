# Project Pipeline

VidioLingua runs as stage-isolated subprocesses:

```text
source video
-> audio extraction
-> ASR / transcription
-> translation routing
-> translation QA / context checks
-> voice routing and generation
-> audio validation
-> lip-sync or ffmpeg mux
-> final MP4
```

## Visual Lip-sync / Wav2Lip Safety

The lip-sync stage now separates audio muxing from visual mouth animation:

- `VIDIOLINGUA_LIPSYNC_MODE=ffmpeg_mux` keeps the existing audio-only ffmpeg mux path and never attempts Wav2Lip.
- `VIDIOLINGUA_LIPSYNC_MODE=wav2lip_optional` attempts Wav2Lip only after runtime preflight and records explicit fallback evidence if it returns to ffmpeg.
- `VIDIOLINGUA_LIPSYNC_MODE=wav2lip_required` fails clearly if preflight or Wav2Lip generation fails; it does not silently produce an ffmpeg-only video.

Wav2Lip runtime readiness is checked by:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_wav2lip_runtime --output outputs\validation\wav2lip_runtime_preflight.json
```

The selector prefers `VIDIOLINGUA_WAV2LIP_PYTHON`, then `.venv_lipsync`, then `.venv_tts` when imports pass. `.venv_api` is not a default Wav2Lip runtime.

The ffmpeg mux path preserves full source-video duration by explicitly padding or trimming generated audio before mux. Main mux no longer depends on `-shortest` to decide output length.

## Job Lifecycle Hardening

The frontend/backend job lifecycle was hardened on 2026-05-06 to prevent stale
browser state and old failed jobs from poisoning new runs after long-lived tabs
or backend restarts.

- Frontend state is versioned under `vidiolingua:v1:*`.
- New uploads clear stale active job/result/terminal state and create a fresh
  run session.
- Polling stops permanently on `complete`, `failed`, `cancelled`, `error`, or
  `timeout`, and in-flight fetches are aborted on page unmount.
- Job status/result responses include no-store headers and explicit terminal
  metadata.
- Manifest writes retry Windows file-lock failures and write recovery manifests
  if primary replacement fails.
- IndicTrans2 worker temp files are job-scoped for production runs and timeout
  errors include worker command, request/response paths, cleanup status, and
  stdout/stderr tails.

The v0-based frontend revamp now lives in:

```text
NEW_Frontend
```

Implemented frontend pages:

```text
/
/upload
/pipeline
/results
/architecture
/backends
/economics
/multilingual-export
```

`NEW_Frontend` uses `NEXT_PUBLIC_API_URL` for the FastAPI base URL and stores no
backend secrets.

Current known-good practical XTTS output is protected:

```text
outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

## Translation Routing

Phase 3A wires production `translation/run_translate.py` through the router.

The intended policy is:

- `preferred_engine=indictrans2`: force IndicTrans2 and fail if unsupported.
- `preferred_engine=llama`: use Ollama/Llama only when explicitly requested.
- `preferred_engine=deep_translator`: use deep-translator only when explicitly requested.
- `preferred_engine=auto`: use IndicTrans2 for supported pairs.
- Unsupported pairs fail unless LLM or deep-translator fallback is explicitly allowed.

No silent fallback is allowed.

## Translation QA / Context Layer

After primary translation, `translation/run_translate.py` runs the translation
integrity layer. The layer is additive: it checks the translated segment JSON
and writes `translation_qa_report.json` without changing the selected primary
translation engine.

Implemented checks include:

- empty translated segments
- segment count alignment
- expansion ratio anomalies
- repeated translation/tokens/punctuation
- number/date/currency-like token preservation
- lightweight entity/proper-noun preservation
- optional glossary preservation
- target script ratio and English leakage
- sentence-boundary punctuation loss
- neighboring segment continuity
- translation-memory consistency hints

The compact summary is exposed as `translationQA` in API status/result payloads
and as translation QA metrics in `metricsReport.translation`. Optional LLM
post-editing remains disabled by default and must not be described as a silent
fallback or as replacing IndicTrans2.

Production compatibility note: existing `VIDIOLINGUA_TRANSLATION_ENGINE=google`
remains usable for unsupported pairs such as `en -> fr`. For supported
IndicTrans2 pairs such as `en -> kn`, production routing upgrades to
IndicTrans2 and fails loudly if the worker is not installed.

## Voice Routing

Phase 3A wires production `tts/run_tts.py` and `app/routers/tts_router.py`
through the voice router for cloned backends while preserving the existing
XTTS segment generation path.

The intended policy is:

- Sarvam AI is the practical managed backend for Hindi, Tamil, Bengali, Telugu,
  Kannada, Malayalam, Marathi, Gujarati, Punjabi, and Odia.
- Sarvam is not exact voice cloning and does not use reference audio.
- XTTS is primary for XTTS-supported languages such as French, English, Spanish,
  German, Japanese, and the other Coqui XTTS language codes.
- IndicF5 remains disabled/local-experimental because Windows local load-only
  validation timed out and created memory risk.
- Generic/system/browser/preset-speaker TTS is blocked when cloning is required.
- Indic Parler-TTS is forbidden and must not be imported or installed.

Reference text is optional for XTTS and not used by Sarvam. It remains required
only for explicitly enabled IndicF5 experiments.

XTTS reference audio can now be supplied in two supported ways:

- uploaded manually as `voiceSample`;
- auto-extracted from the source video with `autoReference=true`.

Auto-reference extraction writes a job-local `reference\auto_reference.wav` and
`reference\auto_reference_metadata.json`, validates the WAV, and fails loudly if
the clip is silent, clipped, too short, undecodable, or otherwise unsafe. Sarvam
does not require this reference path because it is managed TTS, not exact voice
cloning.

Pipeline status and results now expose an `analysis` object with real run
evidence only: speaker-analysis status, reference-audio mode/validation,
translation and voice route, TTS WAV validation, final MP4 inspection, and
advanced evaluator requirement notes. ASR accuracy, BLEU, MOS, lip-sync scores,
and voice similarity are not reported unless future evaluator data exists.

## Evaluation Metrics

After completion, new jobs build:

```text
evaluation\metrics_report.json
```

The report is also included in API result payloads as `metricsReport`.

Always-computed report sections use existing artifacts:

- `operational`
- `audio`
- `media`
- `speaker`

Reference-based sections compute only when optional references exist:

- `asr.wer`, `asr.cer`, `asr.accuracy` require a ground-truth transcript.
- `translation.bleu` and `translation.chrf` require a reference translation.

Evaluator sections remain honest:

- `advanced.mos`, `advanced.lse_c`, `advanced.lse_d`, and
  `advanced.voice_similarity` return `evaluator_not_installed` unless a real
  evaluator or human rating is available.

Validate an existing job without rerunning the pipeline:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_metrics_report --job-dir outputs\some_job
```

Current metrics report schema:

```text
operational
transcript
translation
voice_audio
media_output
validation
optional_reference_metrics
warnings
errors
```

The first six sections are generated from job artifacts when files exist. The
optional section only computes WER/CER, BLEU/chrF, MOS, lip-sync, or speaker
similarity scores when the corresponding reference input or evaluator model is
actually available.

## Job Manifest Orchestration

New jobs now write a durable sidecar:

```text
<job_dir>\job_manifest.json
```

The manifest records job identity, inputs, routing decisions, stage checkpoints,
artifact evidence, errors, and retry/resume metadata. It is additive and does
not replace `pipeline_result.json`.

Manifest stages:

```text
receive_upload
prepare_audio
asr
translation
voice_generation
audio_validation
lipsync_mux
output_validation
metrics_evaluation
complete
```

Retry and resume execution are not implemented yet. The manifest records
`last_completed_stage`, `failed_stage`, `resume_supported=false`, and human
readable hints so a future resume engine can be built without changing the
current successful French XTTS or Kannada IndicTrans2 + Sarvam paths.

Validate a manifest without running media stages:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_job_manifest --job-dir outputs\some_job --print-summary
```

Historical protected outputs may not have a manifest yet. The validator reports
that as historical absence unless `--retrofit` is explicitly supplied.

## Deep Technical Architecture Documentation

The frontend Architecture page now includes a repo-backed deep technical section
covering runtime isolation, worker subprocesses, package/component/deployment
maps, artifact flow, dependency-conflict history, and engineering decisions.

Research and runtime matrix:

```text
docs\DEEP_TECHNICAL_ARCHITECTURE_RESEARCH_2026-05-06.md
docs\RUNTIME_ENVIRONMENT_MATRIX_2026-05-06.md
```

Mermaid sources:

```text
docs\architecture\package_diagram.mmd
docs\architecture\component_diagram.mmd
docs\architecture\deployment_diagram.mmd
docs\architecture\sequence_pipeline_run.mmd
docs\architecture\sequence_indictrans2_worker.mmd
docs\architecture\sequence_voice_backend_selection.mmd
docs\architecture\artifact_flow_diagram.mmd
```

The frontend renders a static, dependency-free version of the diagrams and
tables so no Mermaid package is required.

## Responsible AI & Provenance Engine

New jobs now write responsible AI and provenance readiness sidecars:

```text
<job_dir>\compliance\
  consent_record.json
  sgi_risk_report.json
  abuse_risk_report.json
  synthetic_disclosure_report.json
  provenance_manifest.json
  fingerprint_report.json
  audit_ledger.jsonl
  retention_policy.json
  compliance_passport.json
  compliance_passport.md
```

Default mode is `report_only`: reports, warnings, provenance sidecars,
fingerprints, audit events, retention metadata, and a compliance passport are
generated without blocking the existing French XTTS or Kannada IndicTrans2 +
Sarvam paths. Strict mode is opt-in through
`VIDIOLINGUA_COMPLIANCE_MODE=strict`.

This is compliance-readiness evidence only. It is not legal certification, C2PA
certification, legal advice, tamper-proof watermarking, identity proof, or
complete abuse prevention.

Validate an existing job without rerunning the media pipeline:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_compliance_passport --job-dir outputs\kannada_sarvam_practical_test_clipfix --output outputs\validation\responsible_ai_compliance_test --mode report_only
```


Switch Indian-language voice backend with:

```text
VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam|indicf5|disabled
```

## Multilingual Audio Export

VideoLingua now has an additive packaging-only export layer for OTT-style
delivery:

```text
existing single-language TTS WAVs
-> per-language AAC tracks
-> HLS alternate-audio package
-> optional multi-audio MP4
-> multilingual_manifest.json
```

Proof output:

```text
outputs\multilingual_exports\official_fr_kn_test
```

The packaging tool is:

```powershell
.\.venv_api\Scripts\python.exe -m tools.create_multilingual_export --source-video Vidiolingua_Test_Official.mp4 --track fr=outputs\french_official_test\tts\output\Vidiolingua_Test_Official_transcription_fr.wav --track kn=outputs\kannada_sarvam_practical_test_clipfix\tts\output\Vidiolingua_Test_Official_transcription_kn.wav --output-dir outputs\multilingual_exports\official_fr_kn_test --create-hls --create-mp4
```

Additive API endpoints:

```text
POST /api/multilingual-export
GET /api/multilingual-export/{export_id}
GET /api/multilingual-export/{export_id}/file/{path}
```

The export records French as XTTS speaker-reference voice and Kannada as
IndicTrans2 + Sarvam managed Indian-language TTS. Sarvam remains
`is_exact_clone=false`; XTTS is described cautiously as speaker-reference voice,
not guaranteed exact identity.

## Validation

Light checks:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test." --output outputs/validation/router_translation_en_kn.json
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_test.wav
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Exact transcript." --cloning-required true --output outputs\validation\router_kn_sarvam_test.wav
```
# 2026-05-05 Language Integrity Addendum

The translation-to-voice path now includes two automatic gates:

1. `Grammar and Linguistic Integrity Engine` runs after translation and before TTS. It writes `translation\output\*.linguistic_integrity_report.json` plus aggregate `translation\linguistic_integrity_report.json` where the job structure permits it.
2. `Phonetic and Ambiguity Resolution Layer` runs at the start of TTS. It writes `tts\output\*.phonetic_resolution_report.json` plus aggregate `tts\phonetic_resolution_report.json`.

Pipeline order:

```text
ASR -> Translation -> Translation QA -> Linguistic Integrity -> Phonetic Resolver -> TTS -> Audio Validation -> Lip-sync/Mux
```

The new gates are additive. They do not replace IndicTrans2, XTTS, or Sarvam routing, and they do not add generic fallback.
# 2026-05-05 Prosody & Elocution Engine Addendum

The pipeline now has an additive Prosody & Elocution Engine:

- After ASR, `prosody/source_prosody_profile.json` records speech rate, pauses, segment timing, energy, and heuristic emphasis hints.
- After translation, `prosody/tts_prosody_plan.json` records duration pressure, pause guidance, punctuation strategy, preset, and backend controls.
- Before TTS, canonical translated text remains unchanged while optional `tts_prepared_text` can carry delivery hints.
- After TTS, `prosody/prosody_validation_report.json` and, when available, `prosody/hubert_prosody_report.json` record source-vs-dub delivery evidence.
- HuBERT runs in `.venv_prosody` only and never blocks the main XTTS/Sarvam path when unavailable.
## Speaker Analysis Addendum - 2026-05-06

Speaker diarization is now a backend artifact stage after ASR. It writes durable
speaker turns, ASR segment mapping, speaker profiles, reference candidates, and
voice assignment plans under `speaker_analysis` in each job directory.

Failure is explicit: diarization failures use `status=failed` or
`status=unavailable` with `speaker_count=null`. The backend must not emit fake
`speaker_count=0` for failed diarization.

Validation commands:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_diarization --audio Vidiolingua_Test_Official.mp4 --output outputs\validation\speaker_diarization_test.json
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_mapping --asr-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --diarization-json outputs\validation\speaker_diarization_test.json --output outputs\validation\speaker_segment_map_test.json
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_speaker_plan --speaker-map outputs\validation\speaker_segment_map_test.json --target-language kn --output outputs\validation\sarvam_speaker_voice_plan_test.json
```
