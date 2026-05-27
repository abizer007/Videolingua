# XTTS Voice Cloning

VidioLingua uses Coqui XTTS v2 for required local speaker cloning.

Required model:

```text
tts_models/multilingual/multi-dataset/xtts_v2
```

## Install

Install the TTS environment with the project requirements:

```powershell
python -m pip install -r requirements.txt
```

You also need `ffmpeg` and `ffprobe` on `PATH`.

## Required Config

Use these values when cloned voice output is required:

```env
VOICE_ENGINE=xtts
VIDIOLINGUA_TTS_ENGINE=xtts
XTTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2
VIDIOLINGUA_XTTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2
VIDIOLINGUA_XTTS_MODEL_PATH=/absolute/path/to/xtts_v2
VOICE_CLONING_REQUIRED=true
ALLOW_GENERIC_TTS_FALLBACK=false
SPEAKER_REFERENCE_AUDIO=/absolute/path/to/reference.wav
VIDIOLINGUA_VOICE_SAMPLE=/absolute/path/to/reference.wav
XTTS_LANGUAGE=en
XTTS_DEVICE=auto
XTTS_MODEL_LOAD_TIMEOUT_SECONDS=600
XTTS_GENERATION_TIMEOUT_SECONDS=300
```

`ALLOW_GENERIC_TTS_FALLBACK=false` is intentional. A bad generic voice is worse than a failed job.

## Reference Audio

Use clean, single-speaker speech. Best results usually come from 6 to 30 seconds of speech with minimal background noise, no music, no overlapping speakers, no heavy reverb, and no clipping.

The pipeline converts the reference to:

```text
outputs/intermediate/reference_clean.wav
```

Reference preprocessing is conservative: WAV conversion, mono conversion, and sample-rate conversion. It avoids aggressive denoising, destructive silence trimming, and loudness normalization because those can damage speaker identity.

The job fails if the reference is missing, unreadable, too short, too long, mostly silent, clipped, corrupted, or has an unusable sample rate.

## Generated Audio

XTTS intermediates are WAV files:

```text
outputs/intermediate/xtts_raw.wav
outputs/intermediate/xtts_clean.wav
```

The generated WAV is validated for duration, sample rate, clipping, silence, dropouts, and ffprobe decodability before later pipeline stages use it.

## Validation Command

Run a fast preflight first. This validates imports, local model files, device, output directory, and reference audio without generating speech:

```powershell
python -m tools.validate_xtts_voice_cloning `
  --preflight-only `
  --reference path\to\reference.wav `
  --output outputs\test_xtts_clone.wav `
  --language en `
  --model-path path\to\xtts_v2
```

The local model directory must contain `config.json`, `model.pth` or another `.pth` checkpoint, and `vocab.json` or `tokenizer.json`. If `--model-path` is omitted, the preflight checks known Coqui cache locations and fails before any runtime download attempt if files are not found.

## Smoke Test

After preflight passes, run one short smoke test:

```powershell
python -m tools.validate_xtts_voice_cloning `
  --smoke-test `
  --reference path\to\reference.wav `
  --output outputs\test_xtts_smoke.wav `
  --language en `
  --model-path path\to\xtts_v2 `
  --force-voice-regenerate
```

Expected outputs:

```text
outputs/intermediate/reference_clean.wav
outputs/intermediate/xtts_raw.wav
outputs/intermediate/xtts_clean.wav
outputs/test_xtts_smoke.wav
```

Run XTTS cloning without translation, lip sync, or video generation:

```powershell
python -m tools.validate_xtts_voice_cloning `
  --text "This is a short test of the cloned speaker voice." `
  --reference path\to\reference.wav `
  --output outputs\test_xtts_clone.wav `
  --language en `
  --force-voice-regenerate
```

The command exits nonzero if XTTS fails to load, the reference is invalid, `speaker_wav` is not used, generated audio is invalid, or fallback is attempted.

## Force Regeneration

Set:

```env
VIDIOLINGUA_FORCE_VOICE_REGENERATE=true
```

The XTTS cache key includes text hash, reference audio hash, XTTS model name, language code, voice settings, and preprocessing version. If a future cache layer is enabled, changing the reference audio changes the cache key.

## Troubleshooting Poor Similarity

- Confirm logs show `speaker_wav used: true`.
- Confirm the model is exactly `tts_models/multilingual/multi-dataset/xtts_v2`.
- Use a better reference: clean single-speaker speech, 6 to 30 seconds.
- Avoid music, noise, echo, clipping, overlapping speakers, and heavy denoising.
- Use an XTTS-supported language code: `ar`, `cs`, `de`, `en`, `es`, `fr`, `hu`, `it`, `ja`, `ko`, `nl`, `pl`, `pt`, `ru`, `tr`, `zh`.
- Listen to `outputs/intermediate/reference_clean.wav`; if it no longer sounds like the speaker, choose a cleaner source.

Speaker similarity is not claimed as objectively verified unless a speaker-embedding verifier is installed and wired in. The current implementation logs a placeholder similarity status and fails on conditions known to produce bad generic or damaged audio.
