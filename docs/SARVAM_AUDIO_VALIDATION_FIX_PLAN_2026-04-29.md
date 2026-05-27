# Sarvam Audio Validation Fix Plan - 2026-04-29

## Failure Path

The failed full Kannada pipeline selected Sarvam correctly:

```text
selected_engine=sarvam
managed_tts=true
exact_voice_clone=false
speaker_preservation=not_supported
```

Sarvam wrote the API response WAV directly to the requested segment path:

```text
outputs\kannada_sarvam_practical_test\tts\output\tmpqyst3qcy\raw_0000.wav
```

That path was inside the TTS temporary directory and was removed after the TTS
stage failed. No raw Sarvam segment WAV remains on disk from that run.

## Observed Validation Result

The shared generated-audio validator rejected the first Sarvam segment:

```text
generated audio is clipped (peak=1.000, clipped=0.000%)
```

Because the validator reported only clipping, it had already decoded the audio
and did not report invalid duration, invalid sample rate, silence, dropout, or
corruption. The observed failure was peak-level full-scale audio, not a routing
failure.

The error text incorrectly said `Invalid XTTS generated audio` because the
validator was originally written for XTTS and reused by Sarvam.

## Proposed Fix

Add Sarvam-specific raw cleanup in `voice\engines\sarvam_engine.py`:

1. Decode the base64 API response.
2. Write it to a provider-specific raw sidecar beside the requested output.
3. Analyze the raw WAV for basic validity.
4. If the raw peak is near full scale, apply safe peak normalization to target
   peak `0.95`.
5. Write a provider-specific clean sidecar and copy the clean bytes to the
   requested output path.
6. Run strict generated-audio validation on the requested output path.
7. Fail loudly if the cleaned audio remains invalid.

Add a small reusable helper to `voice\audio_validation.py` for PCM16 WAV peak
normalization. Do not change global clipping thresholds. Also update generated
audio validation wording to be provider-neutral.

## Files To Modify

- `voice\engines\sarvam_engine.py`
- `voice\audio_validation.py`
- docs and command log after validation
