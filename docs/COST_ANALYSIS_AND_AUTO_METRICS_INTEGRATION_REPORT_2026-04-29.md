# Cost Analysis And Auto Metrics Integration Report

Date completed: 2026-05-05
Requested filename date: 2026-04-29
Workspace: `D:\Vidiolingua`

## 1. What Was Wrong

The previous cost work created standalone artifacts:

- `assets\cost_financial_analysis.html`
- `assets\cost_financial_analysis.png`
- `docs\cost_financial_analysis_notes.md`

That made the work feel like a pasted report rather than part of the Vidiolingua frontend. The PNG/HTML are now superseded and ignored as generated standalone report artifacts.

## 2. Frontend Integration

Created native route:

```text
NEW_Frontend\app\economics\page.tsx
```

Navigation label:

```text
Economics
```

The page uses the existing `SiteNavigation`, `SiteFooter`, typography, border/card system, spacing rhythm, and light editorial layout. It does not embed the standalone screenshot or HTML.

## 3. Data Sources Used

Measured Vidiolingua data:

- `outputs\french_official_test\pipeline_result.json`
- `outputs\french_official_test\evaluation\metrics_report.json`
- `outputs\kannada_sarvam_practical_test_clipfix\pipeline_result.json`
- `outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json`

External research sources:

- Sarvam pricing
- ElevenLabs API pricing
- Google Cloud Text-to-Speech pricing
- Google Cloud Translation pricing
- AWS Translate pricing
- RunPod RTX 4090 pricing
- Lambda GPU Cloud pricing
- Rev pricing
- Voquent pricing/dubbing pages
- Microsoft Learn WER definition
- ACL BLEU and chrF papers
- ITU-T MOS terminology
- SyncNet/Wav2Lip-style lip-sync metric references

Detailed table:

```text
docs\COST_ANALYSIS_RESEARCH_SOURCES_2026-04-29.md
```

Machine-readable frontend data:

```text
NEW_Frontend\lib\cost-analysis-data.ts
```

## 4. Numbers Rejected Or Not Used

- No Techgium screenshot values were copied.
- No old standalone report cloud-throughput estimates were used as measured facts.
- Azure Speech pricing was researched but not used as a concrete numeric card because the accessible pricing crawl exposed region/tier placeholders rather than stable USD values.
- Rask/platform credit calculations from the earlier standalone notes were not reused.

## 5. Assumptions

Provider pricing is shown as external planning data with source, URL, access date, evidence kind, and confidence. It is not a guaranteed quote.

Future hosted GPU economics remain assumption-based until Vidiolingua is benchmarked on a real hosted CUDA deployment.

## 6. Why No Fake ROI Was Added

The repo has validated French and Kannada outputs, but it does not contain a controlled manual-dubbing baseline, hosted throughput benchmark, human QA timing study, or production concurrency model. Therefore the frontend shows cost drivers and source-backed comparisons without claiming savings percentages, ROI, speedups, BLEU, MOS, or lip-sync scores.

## 7. Automatic Metrics

The metrics framework now writes:

```text
outputs\<job>\evaluation\metrics_report.json
```

Report sections:

- `operational`
- `transcript`
- `translation`
- `voice_audio`
- `media_output`
- `reference_audio`
- `validation`
- `optional_reference_metrics`
- `warnings`
- `errors`

## 8. Metrics Computed Without User Input

- elapsed time and stage timing where available
- source/target language
- translation backend
- voice backend
- fallback flags
- ASR segment count
- transcript characters and words
- average segment duration
- average words per segment
- speaker-analysis status
- translated segment count
- translated characters and words
- segment-count match
- expansion ratio
- empty/suspicious translation segment counts
- TTS WAV presence, duration, sample rate, channels, peak, RMS, clipping ratio, silence ratio, normalization flag, duration drift
- MP4 presence, duration, size, video codec, resolution, FPS, audio codec, audio sample rate/channels, stream presence
- audio/media validation status

## 9. Metrics Requiring References Or Evaluators

- WER/CER/ASR accuracy require a ground-truth transcript.
- BLEU/chrF require a reference translation.
- MOS requires a human rating or evaluator.
- LSE-C/LSE-D require a lip-sync evaluator.
- Voice similarity requires a speaker embedding evaluator.

## 10. Frontend Changes

- `NEW_Frontend\app\upload\page.tsx`: renamed the default advanced area to collapsed `Expert evaluation inputs`.
- `NEW_Frontend\app\pipeline\page.tsx`: hides speaker counts unless speaker analysis was actually computed.
- `NEW_Frontend\app\results\page.tsx`: replaces reference-heavy presentation with run evidence, transcript/translation analysis, voice/audio analysis, output inspection, and optional evaluator metrics.
- `NEW_Frontend\components\vidiolingua\site-navigation.tsx`: adds `Economics`.
- `NEW_Frontend\components\vidiolingua\site-footer.tsx`: adds `Economics`.

## 11. Backend Changes

- `evaluation\report_builder.py`: expanded automatic metrics report schema.
- `tools\validate_metrics_report.py`: updated summary output for the expanded schema.
- Existing `backend\pipeline_runner.py`, `backend\job_store.py`, and `backend\main.py` already wrote and exposed `metricsReport`; the new schema is picked up by the same integration path.

## 12. Validation Results

Frontend:

```text
corepack pnpm run lint: passed
corepack pnpm run build: passed
```

Backend:

```text
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation: passed
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config: passed
```

Metrics report generation:

```text
outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json
operational_validation=true
asr_segments=1
translated_segments=1
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
asr_segments=5
translated_segments=5
translation_backend=google
voice_backend=XTTS
audio_status=computed
media_status=computed
speaker_status=not_run
asr_wer_status=requires_ground_truth
bleu_status=requires_reference_translation
mos_status=evaluator_not_installed
```

Router dry-runs:

```text
kn -> sarvam
fr -> xtts
```

## 13. Remaining Limitations

- Historical proof job `pipeline_result.json` files only contain coarse elapsed time, so per-stage timing is empty for those old artifacts.
- French historical translation backend is recorded as `google`; this is repo-measured history, not a recommended future default.
- No hosted GPU throughput benchmark exists yet.
- No MOS, LSE-C/LSE-D, or speaker-similarity evaluator is installed.
- Azure numeric TTS pricing was not included because the accessible pricing page did not expose stable concrete USD values in the crawl.

## 14. Safety Confirmation

- No fake metrics were added.
- No fake ROI was added.
- No fake benchmark claims were added.
- No secrets were exposed.
- No Sarvam key was added to frontend.
- No Python virtual environment was mutated.
- No local IndicF5 load or generation was run.
- `models\xtts_v2` was untouched.
- Protected MP4 outputs were not overwritten.
