# Real Run Analysis And Auto Reference Plan - 2026-04-29

## 1. Where Fake Or Future Metrics Currently Appear

- `NEW_Frontend\app\results\page.tsx` renders a `Future hooks` panel with ASR accuracy, BLEU, MOS, LSE-C, and voice similarity as `Not measured`.
- `NEW_Frontend\app\results\page.tsx` renders `IndicF5 loaded` in the main validation panel.
- `NEW_Frontend\app\pipeline\page.tsx` includes `indicf5_loaded` and speaker count labels in the general live metric map.
- `NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx` shows `Speakers detected: ...` during ASR and completion, and `IndicF5 loaded: ...` during TTS.
- `backend\pipeline_runner.py` initializes `speaker_count = 0`, then writes `speakers_detected` and `speakersDetected` even when diarization did not run or ASR segments contain no speaker labels.

## 2. What Should Be Removed

- Remove the active product-style `Future hooks` panel from the results page.
- Remove active rows for ASR accuracy, BLEU, MOS, LSE-C, and voice similarity.
- Remove `IndicF5 loaded: No` from main job metric and validation panels.
- Remove fake default `Speakers detected: 0`; only show a count when ASR or diarization output actually contains speaker labels.

## 3. Real Metrics Available Today

- Job status: stage, progress, elapsed seconds, stage history, current target language, source language and confidence when ASR reports them.
- ASR JSON: transcript segment count, language, language confidence, speaker labels if diarization ran or ASR output includes labels.
- Translation JSON: target language, source language, selected translation engine, fallback policy, IndicTrans2 support flag.
- TTS WAV files: existence, count, duration through ffprobe, and audio stats through `voice.audio_validation.analyze_audio`.
- Sarvam engine metadata: managed TTS, not exact clone, peak normalization in per-segment sidecars/logs.
- Final MP4: existence, size, duration, video codec, resolution, fps, audio codec, sample rate, channels through ffprobe.
- Backend policy evidence: XTTS selected, Sarvam selected, exact clone true/false, managed TTS true/false, generic fallback false.

## 4. Metrics That Can Be Computed Cheaply Now

- Speaker analysis status from ASR segment `speaker` labels:
  - `computed` with unique speaker count when labels exist.
  - `not_run` when no labels exist and diarization is not evidenced.
  - `not_determined` for malformed or unusable ASR files.
- Reference audio metadata:
  - uploaded, auto-extracted, or not required.
  - path, duration, sample rate, channels, peak, and validation status.
- Final TTS WAV validation:
  - duration, sample rate, channels, peak, clipping ratio, validation passed.
- Final MP4 inspection in bytes, not only MB.
- Compact advanced evaluator requirement statuses without fake scores.

## 5. Metrics Requiring Future Ground Truth Or Evaluator Models

- ASR accuracy requires a ground-truth transcript.
- BLEU or COMET requires a reference translation.
- MOS requires human ratings or a validated evaluator model.
- LSE-C/LSE-D requires a lip-sync evaluator.
- Voice similarity requires speaker embedding comparison against a reference speaker.
- CSIM/FID-style media metrics require dedicated evaluator models and a defined evaluation protocol.

## 6. Speaker Detection Current State

- ASR supports diarization only when WhisperX/PyAnnote and a Hugging Face token are available.
- The fallback faster-whisper path emits `speaker: null`.
- Current backend code counts unique speaker labels but defaults to `0`, which makes "not run" look like "zero speakers".
- Correct behavior is to create a speaker analysis object with status and reason, then only surface numeric counts when real labels exist.

## 7. Auto-Reference Extraction Current State

- `backend\pipeline_runner.py` already extracts a reference if cloning is required and no uploaded reference exists.
- It first may use Demucs when configured, otherwise raw early audio, then later tries ASR-guided per-speaker reference creation.
- This behavior is implicit and not tied to an explicit frontend/backend request field.
- It does not store a dedicated `outputs\<job>\reference\auto_reference.wav` artifact or JSON metadata.
- It can fail, but the UI cannot clearly distinguish uploaded reference, auto-extracted reference, or Sarvam not-required behavior.

## 8. Backend Files To Modify

- `backend\main.py`
  - accept `autoReference` or `auto_reference` form field.
  - validate XTTS upload jobs require uploaded reference or auto-reference.
  - store the request in `voiceOptions`.
- `backend\job_store.py`
  - persist and expose an `analysis` object in status/result responses.
- `backend\pipeline_runner.py`
  - respect explicit `auto_reference`.
  - remove default speaker count `0`.
  - create real `analysis` metadata.
  - write `pipeline_result.json` with analysis.
  - include reference mode and validation status in metrics for compatibility.
- `asr\speaker_analysis.py`
  - lightweight helper to inspect ASR/diarization output and return honest status.
- `voice\reference_extractor.py`
  - backend utility using ffmpeg and `voice.audio_validation` to extract, normalize, validate, and write auto-reference metadata.

## 9. Frontend Files To Modify

- `NEW_Frontend\lib\types.ts`
  - add `analysis`, `autoReference`, and reference mode types.
- `NEW_Frontend\lib\api.ts`
  - send `autoReference` and honest voice options.
- `NEW_Frontend\app\upload\page.tsx`
  - add upload-vs-auto reference controls.
  - block XTTS submit unless uploaded reference or auto-reference is selected.
  - keep Sarvam reference optional and clearly managed, not exact cloning.
- `NEW_Frontend\app\pipeline\page.tsx`
  - show real run evidence, reference mode, speaker status, and validation status.
  - suppress `IndicF5 loaded` from main panels.
- `NEW_Frontend\components\vidiolingua\pipeline-timeline.tsx`
  - replace fake speaker count and IndicF5 noise with speaker-analysis/reference status.
- `NEW_Frontend\app\results\page.tsx`
  - replace `Future hooks` with measured output and collapsed/small evaluator requirements.

## 10. Validation Plan

- Frontend:
  - `corepack pnpm run lint`
  - `corepack pnpm run build`
- Backend:
  - `.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts asr`
  - `.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config`
  - Kannada router dry-run expects Sarvam.
  - French router dry-run expects XTTS.
- Lightweight tests/manual checks:
  - speaker analysis returns `not_run` instead of fake `0` when no labels exist.
  - XTTS upload validation requires uploaded reference or auto-reference.
  - Sarvam route does not require reference.
  - auto-reference extraction utility can validate an extracted reference without loading IndicF5 or touching protected outputs.
- Real web UI:
  - If safe after build, run at most one Kannada UI job because Sarvam does not require reference audio.
  - Run at most one retry after a meaningful fix.

