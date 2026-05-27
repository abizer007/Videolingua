# Real Evaluation Metrics Framework - 2026-04-29

## Metrics Implemented

Added a dependency-light `evaluation` package:

- `evaluation\text_metrics.py`
- `evaluation\audio_metrics.py`
- `evaluation\media_metrics.py`
- `evaluation\metrics.py`
- `evaluation\report_builder.py`
- `evaluation\worker.py`
- `evaluation\reference_builder.py`
- `evaluation\asr_eval.py`
- `evaluation\translation_eval.py`
- `evaluation\voice_eval.py`
- `evaluation\sync_eval.py`
- `evaluation\speaker_eval.py`
- `evaluation\quality_schema.py`

Added:

- `tools\validate_metrics_report.py`

New jobs build `evaluation\metrics_report.json` at completion and include the
report in API result payloads as `metricsReport`.

2026-05-05 update: the primary report path is now automatic. The worker writes
`evaluation_mode=automatic` reports with `asr`, `translation`, `voice`, `sync`,
`speaker`, `output_validation`, and `overall` sections. True reference metrics
remain true-reference only; auto-reference and proxy metrics are labeled in the
metric metadata.

## Formulas Used

ASR:

- WER = word-level Levenshtein edit distance / reference word count.
- CER = character-level Levenshtein edit distance / reference character count.
- ASR accuracy = `max(0, 1 - WER)`.

Translation:

- BLEU-lite = local sentence-level n-gram BLEU with add-one smoothing and
  brevity penalty. This is not SacreBLEU and is labeled `BLEU-lite`.
- chrF-lite = local character n-gram F-score across 1-6 character n-grams.

Audio:

- Duration, sample rate, channels, peak, RMS, silence ratio, clipping ratio
  come from `voice.audio_validation.analyze_audio`.
- Loudness proxy is RMS dBFS: `20 * log10(rms)`.
- Duration drift is generated WAV duration minus source segment timeline end.

Media:

- MP4 duration, size, codecs, resolution, fps, sample rate, and channels come
  from ffprobe.

## Always Computed

When artifacts exist, the report computes:

- total elapsed time when available in pipeline result metadata;
- transcript and translated segment counts;
- source/target language;
- translation backend;
- voice backend, including legacy artifact inference from target language;
- fallback flags;
- TTS WAV audio stats;
- final MP4 media stats;
- speaker analysis from ASR speaker labels only.

## Requires Ground Truth

These return `requires_ground_truth` unless
`evaluation\ground_truth_transcript.txt` or upload text/file input exists:

- ASR WER;
- ASR CER;
- ASR accuracy.

## Requires Reference Translation

These return `requires_reference_translation` unless
`evaluation\reference_translation.txt` or upload text/file input exists:

- BLEU-lite;
- chrF-lite.

## Requires Evaluator Models

These return `evaluator_not_installed` unless a real evaluator is installed and
wired:

- voice similarity;
- MOS proxy;
- LSE-C/LSE-D.

Human MOS is accepted as optional user input and labeled as `source=human_rating`.

## Automatic Fallbacks

When expert references are absent, VideoLingua now computes:

- ASR transcript reliability from ASR word confidence and segment structure.
- Translation quality estimate from script match, segment alignment, empty
  output count, expansion ratio, and suspicious length ratio.
- Voice naturalness proxy and MOS-like value from generated WAV audio signals.
- A/V sync proxy from MP4 stream/duration/FPS and TTS WAV duration.
- XTTS weak acoustic speaker proxy when reference and generated WAVs exist.
- Sarvam speaker similarity as `not_applicable`.

## How To Provide Reference Files

API/form fields:

- `ground_truth_transcript_file`
- `ground_truth_transcript_text`
- `reference_translation_file`
- `reference_translation_text`
- `human_mos_rating`
- `human_quality_notes`

Saved paths:

```text
evaluation\ground_truth_transcript.txt
evaluation\reference_translation.txt
evaluation\human_quality.json
```

CLI validation can also pass:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_metrics_report --job-dir outputs\some_job --ground-truth-transcript path\truth.txt --reference-translation path\reference.txt
```

## Why Fake Metrics Are Forbidden

The UI must not show ASR accuracy, BLEU, MOS, LSE-C/LSE-D, or voice similarity
unless the backend actually computed them from required references or evaluator
models. Missing prerequisites are reported as statuses, not invented numbers.

## Validation Results

Compile:

```text
.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts asr evaluation
passed
```

Known job metrics:

```text
outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json
operational_validation=true
segments=1
translation_backend=indictrans2
voice_backend=Sarvam
audio_status=computed
media_status=computed
speaker_status=not_run
asr_wer_status=requires_ground_truth
bleu_status=requires_reference_translation
mos_status=evaluator_not_installed
```

```text
outputs\french_official_test\evaluation\metrics_report.json
operational_validation=true
segments=5
translation_backend=google
voice_backend=XTTS
audio_status=computed
media_status=computed
speaker_status=not_run
asr_wer_status=requires_ground_truth
bleu_status=requires_reference_translation
mos_status=evaluator_not_installed
```

Text metric sanity check:

```text
WER/CER/accuracy computed from provided text.
BLEU-lite and chrF-lite return 1.0 for exact reference/hypothesis matches.
```

Frontend:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
```

## Safety Confirmation

- No fake metric scores were added.
- No hardcoded quality numbers were added.
- No secrets were exposed.
- No Sarvam key was added to frontend.
- No Python virtual environment was mutated.
- No local IndicF5 load or generation was run.
- `models\xtts_v2` was untouched.
- Existing media artifacts in protected outputs were not regenerated.

## Automatic Metrics Schema Update - 2026-05-05

The metrics framework now treats artifact-derived metrics as the primary
quality evidence and keeps reference/evaluator metrics optional.

Primary automatic sections:

- `operational`: elapsed time, stage timings where available, terminal stage,
  source/target language, translation backend, voice backend, fallback flags.
- `transcript`: ASR segment count, transcript character/word counts, average
  segment duration, average words per segment, detected source language, and
  speaker-analysis status.
- `translation`: translated segment count, translated character/word counts,
  source/translation segment count match, expansion ratio, empty segment count,
  suspiciously long segment count, selected backend.
- `voice_audio`: TTS WAV presence, duration, sample rate, channels, peak, RMS,
  clipping ratio, silence ratio, normalization flag, duration drift.
- `media_output`: final MP4 presence, duration, size, codec, resolution, FPS,
  audio metadata, stream presence.
- `validation`: audio validation, media validation, result-file presence,
  warnings, and errors.

Optional section:

- `optional_reference_metrics`: WER, CER, ASR accuracy, BLEU, chrF, MOS,
  LSE-C/LSE-D, and voice similarity. These report prerequisite status unless
  actual reference data or evaluator output exists.

Speaker behavior remains explicit: a numeric speaker count is returned only
when ASR/diarization output contains speaker labels. Otherwise the UI reports
`not_run` or `not_determined`.
