# XTTS Voice Cloning Repair Plan

## 1. Where Coqui XTTS is currently imported/loaded

Coqui XTTS is imported lazily in `app/services/xtts_tts_service.py` inside `_get_tts_model()`:

```python
from TTS.api import TTS
_tts_instance = TTS(_XTTS_MODEL_NAME, gpu=use_gpu)
```

`tts/run_tts.py` imports `app.services.xtts_tts_service` inside `_synthesize_xtts()`.

`app/routers/tts_router.py` also imports `app.services.xtts_tts_service` inside `synthesize_tts()` when the router selects `xtts`.

## 2. Which XTTS model is used

The current default model is:

```text
tts_models/multilingual/multi-dataset/xtts_v2
```

It is configured in `app/services/xtts_tts_service.py` through `VIDIOLINGUA_XTTS_MODEL`.

## 3. Whether the project uses `tts_models/multilingual/multi-dataset/xtts_v2`

Yes. The service default is `tts_models/multilingual/multi-dataset/xtts_v2`, and `scripts/verify_stack.py` also checks that exact model.

Risk: callers can override `VIDIOLINGUA_XTTS_MODEL` with a wrong model and the code does not clearly reject it when cloning is required.

## 4. Where reference speaker audio is passed

Reference audio is passed through these paths:

- `backend/main.py` saves uploaded `voiceSample` to the job directory.
- `backend/pipeline_runner.py` may extract a raw sample or ASR-guided speaker reference and sets `VIDIOLINGUA_VOICE_SAMPLE` for the TTS subprocess.
- `tts/run_tts.py` reads `VIDIOLINGUA_VOICE_SAMPLE` and passes it as `speaker_wav`.
- `app/services/xtts_tts_service.py` receives `speaker_wav` in `synthesize_to_wav()`.

`backend/pipeline_runner.py` also creates `VIDIOLINGUA_SPEAKER_REFS_JSON`, but `tts/run_tts.py` does not currently consume it, so per-speaker references are not actually used.

## 5. Whether `speaker_wav` is actually passed into XTTS

Sometimes. In `app/services/xtts_tts_service.py`, `_synthesize_chunks()` passes:

```python
tts.tts_to_file(text=chunk, speaker_wav=speaker_wav, language=lang, file_path=tmp_path, ...)
```

But if `speaker_wav` is missing, the same function instead calls XTTS with:

```python
tts.tts_to_file(text=chunk, speaker=default_speaker, language=lang, file_path=tmp_path, ...)
```

That default-speaker path is a generic voice fallback and is unacceptable when voice cloning is required.

## 6. Whether language is passed correctly

The XTTS service maps the target language to an XTTS-supported base language code and passes it as `language=lang`.

Risk: unsupported languages silently fall back to `en`, which can harm output quality and should fail clearly when XTTS cloning is required.

## 7. Whether any fallback speaker/default voice is being used

Yes. Current fallback paths include:

- `app/services/xtts_tts_service.py`: missing reference becomes "neutral speaker".
- `tts/run_tts.py`: `auto` can fall back to `legacy` when no reference exists or the language is unsupported.
- `tts/run_tts.py`: XTTS failure can fall back to legacy unless `VIDIOLINGUA_REQUIRE_VOICE_CLONE=true` or `voice_options.cloned` is true.
- `backend/pipeline_runner.py`: voice sample extraction failure prints that XTTS will use neutral speaker.

These are the primary causes of generic output.

## 8. Whether generated audio is being damaged after XTTS generation

Potentially yes.

- `app/services/xtts_tts_service.py` resamples XTTS output to 22050 Hz and peak-normalizes the entire combined output to 0.95.
- `tts/run_tts.py` then time-stretches every segment to fit ASR timing via ffmpeg `atempo`, which can make output robotic or choppy when the generated segment length differs too much from the target.
- `tts/run_tts.py` concatenates stretched segments without crossfade.
- Legacy TTS generates MP3 first, but XTTS intermediate generation stays WAV.

The repair should keep raw XTTS WAVs, validate them before timing changes, use conservative loudness handling, and fail if post-processing produces clipped, silent, or choppy output.

## 9. Audio preprocessing currently applied to the reference speaker

Current reference preprocessing paths:

- `_extract_voice_sample()` extracts the first 30 seconds from video as 22050 Hz mono WAV. This may include silence, music, noise, or multiple speakers.
- `_extract_clean_voice_sample()` can use Demucs, converts vocals to 22050 Hz mono, and picks the highest-RMS window.
- `_make_reference_clip()` applies highpass, lowpass, `afftdn`, and `loudnorm`.
- `_concat_reference_clips()` applies `loudnorm`.

Risk: aggressive denoise/loudnorm can alter speaker identity. Raw first-30s extraction can include poor or wrong speech.

## 10. Audio preprocessing currently applied to generated speech

Current generated-speech processing:

- XTTS chunks are written to temporary WAV files.
- Chunks are read into numpy arrays.
- Audio is converted to mono.
- Audio is resampled to 22050 Hz.
- A 20 ms silence gap is inserted between chunks.
- The full combined signal is normalized to 95% peak.
- `tts/run_tts.py` time-stretches segments to timing slots and concatenates with silence.

There is no strict output validation before lip sync.

## 11. Root causes of poor speaker similarity

1. Missing or failed reference extraction does not stop the pipeline.
2. XTTS is allowed to synthesize with a default speaker instead of `speaker_wav`.
3. `auto` engine selection can choose legacy/gTTS when cloning was expected.
4. XTTS errors can be swallowed and replaced by legacy output unless clone-required flags are set.
5. Speaker reference validation logs warnings but still proceeds.
6. Unsupported XTTS language falls back to English.
7. Per-speaker reference mapping is prepared but not used.
8. Reference preprocessing can be too aggressive, while raw fallback can be too dirty.
9. Generated output validation is missing.
10. There is no standalone XTTS validation command proving `speaker_wav` was used.
11. There is no cache key discipline for future cached XTTS outputs.

## 12. Files that need changes

Primary changes:

- `app/services/xtts_tts_service.py`
- `tts/run_tts.py`
- `backend/pipeline_runner.py`
- `.env.example`
- `requirements.txt`

New files:

- `voice/audio_validation.py`
- `voice/reference_audio.py`
- `voice/xtts_cloner.py`
- `tools/validate_xtts_voice_cloning.py`
- `XTTS_VOICE_CLONING.md`
- focused tests or validation scripts for the new strict paths

Optional follow-up:

- `app/routers/tts_router.py` should pass explicit `speaker_wav` to XTTS and obey clone-required fallback rules if that router is used for synthesis.

## 13. Exact implementation plan

1. Add strict audio validation utilities.
   - Probe files with ffprobe.
   - Decode WAV with `soundfile` when available or stdlib `wave` for basic PCM WAV.
   - Validate existence, readability, duration, sample rate, clipping, silence ratio, corruption, and basic dropout/choppiness signals.

2. Add reference audio preparation.
   - Require a real input path.
   - Convert safely to `outputs/intermediate/reference_clean.wav` or a caller-provided intermediate directory.
   - Use PCM WAV, mono, conservative trimming, and no aggressive normalization.
   - Fail loudly on silence, clipping, unreadable files, or too-short speech.

3. Replace the permissive XTTS service with a strict cloner API.
   - Expose `VoiceCloneConfig`, `VoiceCloneResult`, `VoiceCloningError`, and `clone_voice()`.
   - Load `tts_models/multilingual/multi-dataset/xtts_v2` explicitly by default.
   - Require `speaker_wav`.
   - Pass `speaker_wav=<reference_clean.wav>` and `language=<code>` to every XTTS call.
   - Write `outputs/intermediate/xtts_raw.wav` and `outputs/intermediate/xtts_clean.wav`.
   - Validate both outputs and return metadata proving model, language, reference path, generated path, and fallback status.

4. Keep compatibility for existing callers.
   - Make `app/services/xtts_tts_service.py::synthesize_to_wav()` delegate to `clone_voice()`.
   - Remove the default speaker path when clone-required mode is active.
   - Treat `VOICE_CLONING_REQUIRED=true`, `VIDIOLINGUA_REQUIRE_VOICE_CLONE=true`, or `voice_options.cloned=true` as hard requirements.

5. Harden `tts/run_tts.py`.
   - Default to required voice cloning unless explicitly disabled.
   - Block generic fallback when cloning is required.
   - Fail if no reference exists before synthesis starts.
   - Consume `VIDIOLINGUA_SPEAKER_REFS_JSON` for segment speaker-specific references.
   - Validate assembled WAV before handing it to lip sync.
   - Add `--force-voice-regenerate`-equivalent environment support for future cache use.

6. Harden `backend/pipeline_runner.py`.
   - Set `VOICE_ENGINE=xtts`, `XTTS_MODEL`, `VOICE_CLONING_REQUIRED=true`, `ALLOW_GENERIC_TTS_FALLBACK=false`, `SPEAKER_REFERENCE_AUDIO`, and `XTTS_LANGUAGE` for TTS.
   - If reference extraction fails and cloning is required, fail the job instead of using neutral speech.
   - Keep WAV intermediates.

7. Add validation command.
   - `python -m tools.validate_xtts_voice_cloning --text ... --reference ... --output ... --language en`
   - It must validate reference audio, run XTTS, validate generated audio, print a clear report, and exit nonzero on failure.

8. Add tests for strict behavior.
   - Missing reference fails.
   - Empty reference fails.
   - XTTS call receives `speaker_wav`.
   - Generic fallback is blocked when cloning is required.
   - Cache key changes when reference hash changes.
   - Generated output validation catches invalid WAVs.
   - Chunk joins are smoothed.
   - Language is passed.
   - Wrong model/config fails clearly.
   - Pipeline TTS stage requires XTTS output instead of old generic audio.

9. Document the new behavior.
   - Required model and install steps.
   - Good reference audio selection.
   - Config values.
   - Validation command.
   - Force regeneration.
   - Troubleshooting poor similarity.
   - Why generic fallback is disabled.
