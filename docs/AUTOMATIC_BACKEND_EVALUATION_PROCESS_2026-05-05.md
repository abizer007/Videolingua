# Automatic Backend Evaluation Process - 2026-05-05

After the main pipeline creates ASR JSON, translation JSON, TTS WAV, and final MP4, `evaluation.worker.run_evaluation()` writes:

```text
outputs\<job>\evaluation\metrics_report.json
```

## ASR

True WER/CER/accuracy use a transcript or subtitle sidecar. Auto-reference uses independent ASR agreement when multiple distinct ASR outputs exist. Otherwise the worker computes transcript reliability from ASR confidence, empty segment ratio, and transcript structure.

## Translation

True BLEU-lite/chrF-lite require `evaluation/reference_translation.txt`. Auto-reference uses configured independent evaluator translation fields when present. Otherwise the worker computes a translation quality estimate from script match, segment alignment, empty outputs, expansion ratio, and suspicious length checks.

The translation QA/context layer now writes `translation_qa_report.json` and
embeds a compact `translation_qa` summary in translation JSON for new runs.
`evaluation.report_builder` includes those fields in `translation`, including
QA status, warnings/errors, script match, empty segments, number/entity issues,
and expansion warnings. This is an integrity report, not a claim that a new
translation model was trained.

## Voice / MOS-Like

Human MOS is used only when supplied by an expert. Otherwise the worker computes an audio naturalness proxy from clipping, silence, peak, RMS/loudness proxy, sample rate, and duration drift, then converts it to a clearly labeled MOS-like `1-5` value.

## Sync / LSE-Like

LSE-C/LSE-D are shown only when a true evaluator and checkpoint are installed and wired. Current validation uses an A/V sync proxy from final MP4 streams, FPS, duration, and TTS WAV duration drift.

The 2026-05-06 Wav2Lip safety pass adds a separate `lipsync` evidence object to
new automatic reports when pipeline evidence is present. It reports method,
visual sync requested/applied, fallback status, Wav2Lip preflight status,
selected Python, checkpoint status, alignment level, duration padding/trimming,
and Wav2Lip errors/warnings. LSE-C/LSE-D remain `not_installed` or
`unavailable`; no score is invented.

## Voice Similarity

Sarvam is `not_applicable` because managed TTS does not preserve exact speaker identity. XTTS uses speaker embedding cosine only if an evaluator exists; otherwise it can compute a weak acoustic proxy when reference and generated WAVs exist.

## Overall Score

`overall.overall_quality_index` combines available ASR, translation, voice, sync, output validation, and speaker components. Missing or not-applicable components are excluded and weights are redistributed.

## Validation Results

Commands:

- `.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation`: passed.
- `corepack pnpm run lint`: passed after Corepack cache escalation.
- `corepack pnpm run build`: passed.

French report: `outputs\french_official_test\evaluation\metrics_report.json`

- Overall `93.565`, grade `Excellent`
- ASR `84.37%`, `asr_structural_confidence_proxy`
- Translation `100.0%`, `artifact_translation_quality_proxy`
- Voice `4.873 / 5`, `audio_naturalness_proxy`
- Sync `100.0%`, `av_duration_stream_proxy`
- Speaker `59.615%`, `weak_acoustic_similarity_proxy`

Kannada report: `outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json`

- Overall `91.326`, grade `Excellent`
- ASR `65.0%`, `asr_structural_confidence_proxy`
- Translation `100.0%`, `artifact_translation_quality_proxy`
- Voice `4.899 / 5`, `audio_naturalness_proxy`
- Sync `100.0%`, `av_duration_stream_proxy`
- Speaker `not_applicable` for Sarvam

## Limitations

Current ASR and translation scores are proxies when no human/independent reference is present. BLEU/chrF are unavailable unless a reference exists. LSE-C/LSE-D and speaker embedding cosine require optional evaluator dependencies.

## Job Manifest Coordination

The evaluation stage is now represented in `job_manifest.json` as
`metrics_evaluation`. New jobs register `evaluation\metrics_report.json` in the
manifest artifact map after the automatic worker writes it.

This does not change metric formulas or evaluator behavior. The manifest only
adds orchestration evidence:

- whether the metrics stage ran
- whether `metrics_report.json` exists
- the last completed checkpoint before a failure
- recovery hints for future resume/retry support

Historical protected outputs were not retrofitted during this pass.
# 2026-05-05 Language Integrity Metrics Addendum

Metrics reports now discover linguistic integrity and phonetic resolution reports when present.

Translation metrics include:

- `linguistic_integrity_status`
- `linguistic_integrity_score`
- `linguistic_integrity_script_status`
- `linguistic_integrity_number_warnings`
- `linguistic_integrity_name_warnings`
- `linguistic_integrity_expansion_warnings`

Voice/audio metrics include:

- `phonetic_resolution_status`
- `phonetic_risk_score`
- `pronunciation_dictionary_used`
- `acronyms_detected`
- `ambiguity_warnings`
# 2026-05-05 Prosody Metrics Addendum

The evaluation report builder now reads prosody artifacts when present:

- source prosody profile status
- elocution preset
- speech-rate class
- pause count and pause preservation proxy
- duration pressure and drift
- HuBERT feature/report status
- adapter status and confidence
- speed guardrail violations

These metrics are proxy evidence, not a claim of perfect emotion or prosody transfer.
## 2026-05-06 Speaker Analysis Validation Addendum

Speaker analysis has separate validation tools and artifacts:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_diarization --audio Vidiolingua_Test_Official.mp4 --output outputs\validation\speaker_diarization_test.json
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_mapping --asr-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --diarization-json outputs\validation\speaker_diarization_test.json --output outputs\validation\speaker_segment_map_test.json
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_speaker_plan --speaker-map outputs\validation\speaker_segment_map_test.json --target-language kn --output outputs\validation\sarvam_speaker_voice_plan_test.json
```

Diarization failure is a real validation state. Reports must preserve
`speaker_count=null`, the exact error, and the recommended fix instead of
turning a failed run into `speaker_count=0`.
