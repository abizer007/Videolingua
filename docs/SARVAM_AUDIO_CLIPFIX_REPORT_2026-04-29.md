# Sarvam Audio Clipfix Report - 2026-04-29

## Root Cause

The first full Kannada Sarvam pipeline run failed in TTS because Sarvam returned
a valid WAV whose raw peak reached full scale:

```text
peak=1.000
```

The shared generated-audio validator rejected the raw segment before the
pipeline could assemble final TTS audio. Routing was correct: translation used
IndicTrans2 and voice used Sarvam.

## Files Changed

- `voice\engines\sarvam_engine.py`
- `voice\audio_validation.py`
- `docs\SARVAM_AUDIO_VALIDATION_FIX_PLAN_2026-04-29.md`
- `docs\SARVAM_AUDIO_CLIPFIX_REPORT_2026-04-29.md`
- `docs\TROUBLESHOOTING.md`
- `docs\SARVAM_TTS_SETUP.md`
- `docs\VOICE_BACKENDS.md`
- `COMMAND_LOG.md`

Runtime backups were created before editing:

```text
_snapshots\sarvam_clipfix_20260429_213150
```

## Old Behavior

Sarvam decoded the API response and wrote the WAV bytes directly to the
requested output path. It then ran strict generated-audio validation on that raw
WAV. Near-full-scale Sarvam audio could fail with a clipping error even when the
file was otherwise decodable, non-silent, and usable.

The validator error text also said `Invalid XTTS generated audio`, even when the
selected provider was Sarvam.

## New Behavior

Sarvam now uses a provider-specific raw/clean flow:

1. Write the API response to a `.sarvam_raw.wav` sidecar.
2. Analyze basic audio properties.
3. Fail loudly for corrupt, silent, too-short, invalid-rate, or heavily clipped
   raw audio.
4. If the raw peak is near full scale, apply safe PCM16 peak normalization to
   target peak `0.95`.
5. Write a `.sarvam_clean.wav` sidecar.
6. Copy the cleaned WAV to the requested output path.
7. Run strict generated-audio validation on the cleaned output.

Global XTTS validation thresholds were not relaxed. The generated-audio error
wording is now provider-neutral.

## Small Validation

Compile:

```text
passed
```

Config inspect:

```text
Sarvam enabled, key masked, Indic backend=sarvam, IndicF5=false/local_disabled, XTTS ready
```

Real Sarvam Kannada validation:

```text
outputs\validation\sarvam_kn_after_clipfix.wav
```

Result:

```text
passed
raw_peak=0.95694
clean_peak=0.95694
sample_rate=24000
duration=1.365333s
clipping_ratio=0.0
```

Real Kannada router validation:

```text
outputs\validation\router_kn_sarvam_after_clipfix.wav
```

Result:

```text
selected_engine=sarvam
passed
raw_peak=0.95731
clean_peak=0.95731
sample_rate=24000
duration=1.194667s
clipping_ratio=0.0
```

French router dry-run selected XTTS. XTTS `BeamSearchScorer` health passed.
No Indic Parler runtime or requirements matches were found in the equivalent
existing-path scan.

## Full Kannada Pipeline Result

The full Kannada practical pipeline was rerun exactly once after small
validation passed:

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --model-path models\xtts_v2 --mode practical --output-dir outputs\kannada_sarvam_practical_test_clipfix
```

Result:

```text
passed
```

Stage timing from pipeline output:

```text
ASR: 64.4s
Translation: 69.1s
TTS: 16.0s
Lipsync/mux: 6.2s
Total: 166s
```

Translation backend:

```text
IndicTrans2
```

Voice backend:

```text
Sarvam
```

TTS log showed the clipfix being used:

```text
Sarvam raw audio near full scale; applying safe peak normalization (peak=1.000, target_peak=0.95)
```

Final TTS WAV:

```text
outputs\kannada_sarvam_practical_test_clipfix\tts\output\Vidiolingua_Test_Official_transcription_kn.wav
```

Final TTS WAV validation summary:

```text
duration=30.655011s
sample_rate=22050
channels=1
peak=0.95941
clipping_ratio=0.0
```

Final MP4:

```text
outputs\kannada_sarvam_practical_test_clipfix\results\Vidiolingua_Test_Official_dubbed_kn.mp4
```

Pipeline result:

```text
outputs\kannada_sarvam_practical_test_clipfix\pipeline_result.json
```

Translation JSON:

```text
outputs\kannada_sarvam_practical_test_clipfix\translation\output\Vidiolingua_Test_Official_transcription_kn.json
```

## ffprobe Summary

Final MP4:

```text
size=78,710,653 bytes
duration=30.655011s
format=mov,mp4,m4a,3gp,3g2,mj2
```

Video stream:

```text
exists=true
codec=h264
profile=Main
resolution=1920x1080
fps=30
duration=30.633333s
```

Audio stream:

```text
exists=true
codec=aac
profile=LC
sample_rate=44100
channels=2
duration=30.655011s
```

## Safety Confirmations

- No full Sarvam API key was printed or written to docs/logs.
- XTTS was untouched and was not used for Kannada.
- `models\xtts_v2` was untouched.
- `.venv_tts` was not mutated.
- `.venv_indictrans2` was not mutated.
- IndicF5 remained disabled/local_disabled and did not load.
- No generic TTS fallback was used.
- No Indic Parler was used.
- `outputs\french_official_test` was untouched.
- `outputs\french_after_phase3a_router_integration_test` was untouched.

## Honest Voice Note

Sarvam is managed Indian-language TTS. It is not exact voice cloning and does
not preserve the reference speaker exactly.
