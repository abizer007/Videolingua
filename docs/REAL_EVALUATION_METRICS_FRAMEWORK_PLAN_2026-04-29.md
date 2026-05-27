# Real Evaluation Metrics Framework Plan - 2026-04-29

## 1. Always Computable Metrics

These can be computed from job metadata and output artifacts after every job:

- total elapsed time and per-stage elapsed time from job status/history;
- transcript segment count from ASR JSON;
- translated segment count from translation JSON;
- source and target language from ASR/translation JSON;
- translation backend and fallback policy from translation JSON;
- voice backend, managed/exact-clone policy, and fallback flags from TTS route metadata/log-derived pipeline metadata;
- final MP4 existence, duration, byte size, video codec, resolution, fps, audio codec, audio sample rate, audio channels from ffprobe;
- TTS WAV duration, sample rate, channels, peak, RMS, silence ratio, clipping ratio from existing audio validation helpers;
- normalization applied true/false when clean/raw sidecars or provider metadata exist;
- validation passed true/false from audio/media checks.

## 2. Metrics Requiring Ground-Truth Transcript

These must stay unavailable unless a user provides a real transcript:

- ASR WER;
- ASR CER;
- ASR accuracy, defined as `max(0, 1 - WER)`.

The transcript may be uploaded as a file or submitted as text. It is saved under
`evaluation\ground_truth_transcript.txt`.

## 3. Metrics Requiring Reference Translation

These must stay unavailable unless a user provides a real reference
translation:

- BLEU-lite: local n-gram BLEU implementation, explicitly not SacreBLEU;
- chrF-lite: local character n-gram F-score implementation.

The reference translation may be uploaded as a file or submitted as text. It is
saved under `evaluation\reference_translation.txt`.

## 4. Metrics Requiring Evaluator Models

These must return `evaluator_not_installed` unless a real evaluator is wired:

- voice similarity from speaker embeddings;
- MOS proxy from an audio quality evaluator or human MOS input;
- LSE-C/LSE-D from a real lip-sync evaluator.

Human MOS can be stored as user-provided evidence, but it must be labeled as
human input, not model-estimated MOS.

## 5. Existing Files And Data

Current protected proof jobs already include:

- `pipeline_result.json`;
- ASR JSON in `asr\output`;
- translation JSON in `translation\output`;
- TTS WAV in `tts\output`;
- final MP4 in `results`.

Docs confirm ffprobe summaries for French and Kannada final MP4s and audio
validation details for the Kannada Sarvam WAV.

## 6. New Optional Inputs Needed

Backend upload/API fields:

- `ground_truth_transcript_file`;
- `ground_truth_transcript_text`;
- `reference_translation_file`;
- `reference_translation_text`;
- `human_mos_rating`;
- `human_quality_notes`.

These are optional and never block the normal pipeline.

## 7. Backend Modules To Compute Metrics

New package:

- `evaluation\text_metrics.py`: WER, CER, ASR accuracy, BLEU-lite, chrF-lite.
- `evaluation\audio_metrics.py`: WAV/audio stats, loudness proxy, duration drift.
- `evaluation\media_metrics.py`: ffprobe media inspection.
- `evaluation\metrics.py`: common status/value helpers and evaluator status stubs.
- `evaluation\report_builder.py`: job-folder artifact discovery and report assembly.

Existing:

- `voice\audio_validation.py` for audio decode/stats.
- `asr\speaker_analysis.py` for honest speaker analysis.

Tool:

- `tools\validate_metrics_report.py` to compute/write reports for existing jobs.

## 8. Frontend Components To Display Metrics

- `NEW_Frontend\app\upload\page.tsx`: add an Advanced evaluation section with optional transcript/reference inputs.
- `NEW_Frontend\lib\api.ts`: submit optional evaluation fields.
- `NEW_Frontend\lib\types.ts`: type `metricsReport`.
- `NEW_Frontend\app\pipeline\page.tsx`: show live operational metrics and stage timings when available.
- `NEW_Frontend\app\results\page.tsx`: show operational, audio/media, reference-based, and collapsed advanced evaluator panels from the report.

## 9. When A Metric Cannot Be Computed

- Missing ground-truth transcript: `requires_ground_truth`.
- Missing reference translation: `requires_reference_translation`.
- Missing evaluator model: `evaluator_not_installed`.
- Missing artifact: `missing_artifact`.
- Computation error: `error` with a debuggable reason.

No metric should be displayed as a fake value or as a large active metric card
when it is unavailable.

## 10. Validation Plan

Run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts asr evaluation
.\.venv_api\Scripts\python.exe -m tools.validate_metrics_report --job-dir outputs\kannada_sarvam_practical_test_clipfix --output outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json
.\.venv_api\Scripts\python.exe -m tools.validate_metrics_report --job-dir outputs\french_official_test --output outputs\french_official_test\evaluation\metrics_report.json
cd NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

Expected for proof jobs without references:

- operational/audio/media metrics compute;
- ASR WER/CER/accuracy return `requires_ground_truth`;
- BLEU/chrF return `requires_reference_translation`;
- MOS/LSE/voice similarity return `evaluator_not_installed`.

