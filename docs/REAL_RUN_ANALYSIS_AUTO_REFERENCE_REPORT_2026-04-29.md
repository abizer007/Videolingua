# Real Run Analysis Auto Reference Report - 2026-04-29

## 1. Fake Metrics Removed

- Removed the active `Future hooks` result panel that showed ASR accuracy, BLEU, MOS, LSE-C, and voice similarity as `Not measured`.
- Removed `IndicF5 loaded` from main pipeline/results metric panels.
- Removed the fake default speaker count behavior from backend metadata. Speaker count is now numeric only when ASR/diarization output contains speaker labels.

## 2. Real Metrics Added

New result/status payloads include an `analysis` object with:

- `run_evidence`: source language, target language, translation backend, voice backend, fallback flags, total elapsed seconds.
- `speaker_analysis`: computed/not run/not determined status and count only when labels exist.
- `reference_audio`: uploaded, auto-extracted, or not-required mode plus validation details.
- `output_inspection`: final MP4 existence, duration, byte size, codec, resolution, fps, audio codec, sample rate, channels.
- `audio_validation`: TTS WAV existence, duration, sample rate, channels, peak, clipping ratio, normalization flag, validation status.
- `advanced_metrics`: requirement statuses only, with no fake scores.

## 3. Speaker Analysis Behavior

Added `asr\speaker_analysis.py`.

Behavior:

- If ASR segments contain speaker labels, count unique non-empty labels.
- If ASR segments exist but labels are missing, return `not_run` with reason `Diarization was not enabled for this job or produced no speaker labels.`
- If ASR evidence cannot be read, return `not_determined`.
- The UI no longer renders `Speakers detected: 0` for jobs where diarization did not run.

## 4. Auto-Reference Extraction Behavior

Added `voice\reference_extractor.py`.

Behavior:

- Backend accepts `autoReference=true` / `auto_reference=true`.
- When XTTS needs a reference and no upload is present, the pipeline extracts `reference\auto_reference.wav` under the job folder.
- The extractor prefers ASR speech windows, then falls back to an early-middle source-video segment.
- ffmpeg writes mono PCM WAV with light filtering/loudness normalization.
- Existing `voice.audio_validation.validate_reference_audio` validates duration, decodeability, silence, clipping, and sample rate.
- Metadata is written to `reference\auto_reference_metadata.json`.
- Extraction failure is loud and asks the user to upload a clean manual reference. No generic TTS fallback is introduced.

## 5. Frontend Upload Changes

`NEW_Frontend\app\upload\page.tsx` now exposes:

- Upload a reference audio file.
- Auto-extract from uploaded video.

XTTS routes require either uploaded reference audio or auto-extraction. Sarvam routes do not require reference audio and state that Sarvam is managed Indian-language speech, not exact cloning.

## 6. Backend Metadata Changes

- `backend\main.py` validates XTTS upload requests and stores auto-reference options in `voiceOptions`.
- `backend\job_store.py` stores and exposes `analysis`.
- `backend\pipeline_runner.py` populates real analysis metadata and writes `pipeline_result.json` for API jobs.

## 7. Validation Commands And Results

```text
corepack pnpm run lint
passed

corepack pnpm run build
passed

.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts asr
passed

.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
passed; Sarvam enabled, key masked, IndicF5 false/local_disabled, XTTS ready

.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\analysis_fix_router_kn.wav --dry-run
passed; selected_engine=sarvam

.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\analysis_fix_router_fr.wav --dry-run
passed; selected_engine=xtts
```

Manual lightweight checks:

```text
speaker_analysis without labels -> not_run, speakers_detected=null
speaker_analysis with SPEAKER_00/SPEAKER_01 -> computed, speakers_detected=2
French upload without reference or autoReference -> rejected
French upload with autoReference=true -> accepted
Kannada Sarvam upload without reference -> accepted
auto-reference extraction from Vidiolingua_Test_Official.mp4 -> passed
  path=.runtime_tmp\auto_reference_validation_3b46a7b3ab784242b1533c42047233c8\auto_reference.wav
  duration=12.0s sample_rate=22050 channels=1 peak=0.706696 source=fallback_early_middle
```

## 8. Real Web UI Test Result

Not run in this pass. The requested build and light backend checks passed. No heavy pipeline loop was started.

## 9. Remaining Limitations

- ASR diarization still depends on WhisperX/PyAnnote runtime and Hugging Face token availability.
- Auto-reference quality depends on source-video speech quality and ASR segment quality.
- Existing historical protected `pipeline_result.json` files still contain older fields and were not modified.
- Next build still reports that type validation is skipped by project config.

## 10. Future Evaluator Metrics

- ASR accuracy requires ground-truth transcript.
- BLEU/COMET requires reference translation.
- MOS requires humans or an evaluator model.
- LSE-C/LSE-D requires a lip-sync evaluator.
- Voice similarity requires a speaker embedding evaluator.

## Real Metrics Framework Follow-Up

The evaluation framework now computes real reports through
`evaluation\report_builder.py` and `tools\validate_metrics_report.py`.

Implemented:

- WER, CER, and ASR accuracy when ground-truth transcript is provided.
- BLEU-lite and chrF-lite when reference translation is provided.
- Audio duration, sample rate, channels, peak, RMS, silence ratio, clipping
  ratio, loudness proxy, and duration drift from real WAV data.
- MP4 duration, byte size, codecs, resolution, fps, audio sample rate, and audio
  channels through ffprobe.
- Evaluator-model metrics return `evaluator_not_installed` unless a real
  evaluator or human rating is provided.

Generated reports:

```text
outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json
outputs\french_official_test\evaluation\metrics_report.json
```

## Safety Confirmation

- No fake scores were added.
- No secrets were exposed.
- No Sarvam key was placed in frontend.
- No Python virtual environment was mutated.
- No backend dependencies were installed.
- No local IndicF5 load or generation was run.
- `models\xtts_v2` was untouched.
- Protected output folders were untouched.
