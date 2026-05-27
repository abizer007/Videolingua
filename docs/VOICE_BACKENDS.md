# Voice Backends

Allowed voice backends:

- XTTS
- Sarvam AI
- IndicF5 only as disabled/local-experimental scaffolding

Forbidden voice backends:

- Indic Parler-TTS
- Browser/system TTS
- Random generic TTS fallback
- Preset-speaker backends pretending to be cloning

## Routing Policy

Sarvam AI is now the practical managed backend for Indian regional TTS:

```text
hi, ta, bn, te, kn, ml, mr, gu, pa, or/od -> Sarvam
```

XTTS remains the primary backend for XTTS-supported languages:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh -> XTTS
```

Sarvam is managed Indian-language TTS, not exact voice cloning. When it is used
with `cloning_required=true`, the metadata must remain honest:

```text
used_reference_audio=false
exact_voice_clone=false
managed_tts=true
speaker_preservation=not_supported
```

## Sarvam

Runtime config belongs in `backend\.env` or another gitignored local env file:

```text
VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam
VIDIOLINGUA_ENABLE_SARVAM=true
SARVAM_API_KEY=
VIDIOLINGUA_SARVAM_MODEL=bulbul:v3
VIDIOLINGUA_SARVAM_SPEAKER=shubh
VIDIOLINGUA_SARVAM_PACE=1.0
VIDIOLINGUA_SARVAM_TEMPERATURE=0.45
VIDIOLINGUA_SARVAM_SAMPLE_RATE=24000
VIDIOLINGUA_SARVAM_OUTPUT_CODEC=wav
VIDIOLINGUA_SARVAM_TIMEOUT_SECONDS=120
```

Never commit or log the API key. Mask it as `sk_****abcd`.

Sarvam audio is cleaned in a provider-specific raw/clean flow before final
validation. Near-full-scale raw WAVs are attenuated to a safe target peak, then
strict generated-audio validation runs on the cleaned requested output. Broken,
silent, corrupt, or heavily clipped audio still fails loudly.

Validate Kannada Sarvam TTS:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_test.wav
```

## XTTS

The known-good local model path is:

```text
models\xtts_v2
```

Do not pass:

```text
models\xtts_v2\model.pth
```

The XTTS path must pass `speaker_wav` and `language` to Coqui. The current strict
path is `app/services/xtts_tts_service.py` -> `voice/xtts_cloner.py`.

## IndicF5

IndicF5 files and scaffolding stay in the repo, but local execution is disabled
because native Windows load-only validation timed out and created memory risk.
Do not run local IndicF5 load or generation.

Current safe config:

```text
VIDIOLINGUA_ENABLE_INDICF5=false
VIDIOLINGUA_INDICF5_EXECUTION_MODE=local_disabled
```

Backend switch:

```text
VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam|indicf5|disabled
```

Only use `indicf5` after explicitly changing the execution mode to an enabled
mode with approval. `local_disabled` and `local_experimental` are not production
execution modes.

## Fallbacks

When `cloning_required=true`, generic fallback is blocked. Sarvam is allowed as
the configured managed Indian-language TTS backend, but it must not be described
as speaker cloning.

## Frontend UX

The v0-based `NEW_Frontend` revamp exposes backend capability copy as:

- `XTTS speaker-reference voice` for XTTS-supported global languages.
- `Sarvam managed Indian-language voice` for regional Indian languages.
- `IndicF5 disabled / local experimental` as roadmap/status only.

The frontend requires reference audio for XTTS routes and treats it as optional
for Sarvam routes. Sarvam UI copy says it is managed regional speech and not
exact speaker cloning. No frontend secret variable is used for Sarvam.

XTTS frontend/API jobs now allow either a manual `voiceSample` upload or
`autoReference=true`. Auto-reference is implemented in the backend, not only the
UI: the pipeline extracts `reference\auto_reference.wav` from the source video,
writes `reference\auto_reference_metadata.json`, validates the clip, and fails
loudly if no usable reference can be produced.

Sarvam routes do not require reference audio. If a user supplies one, it must
not be described as exact speaker cloning because Sarvam uses a managed voice.

User-facing analysis panels should not show `IndicF5 loaded: No` as a primary
metric. IndicF5 remains documented only as disabled/local experimental status.

## Economics Page Update - 2026-05-05

The frontend now has a native economics route at:

```text
NEW_Frontend\app\economics\page.tsx
```

Voice backend cost framing:

- XTTS: local compute/runtime for supported global speaker-reference routes.
- Sarvam: managed Indian-language TTS API cost; not exact voice cloning and no
  frontend key exposure.
- IndicF5: disabled/local experimental roadmap status only.
- Managed API alternatives: shown as source-backed comparison data, not current
  runtime cost unless the backend actually routes through that provider.

No ROI, quality, or benchmark numbers are claimed unless backed by measured
Vidiolingua artifacts or external provider pricing with source labels.
# 2026-05-05 Phonetic Resolution Addendum

Before TTS, Vidiolingua now builds a phonetic resolution report and can attach `tts_prepared_text` per segment. Canonical translated text is preserved as display text.

Supported preparation includes pronunciation dictionary replacements, safe acronym expansion, homophone/date ambiguity warnings, and backend notes for XTTS and Sarvam. Kannada/Hindi and other Indian-language scripts are not aggressively romanized.

This layer does not claim perfect pronunciation. Sarvam remains managed Indian-language TTS, not exact voice cloning. IndicF5 remains disabled/local experimental and Indic Parler remains forbidden.
# 2026-05-05 Prosody & Elocution Engine Addendum

XTTS remains the primary speaker-reference backend for supported global languages. When the prosody engine is enabled, presets can safely guide XTTS temperature, repetition penalty, max chunk size, crossfade, and punctuation-aware prepared text.

Sarvam remains managed Indian-language TTS, not exact voice cloning. Prosody presets can guide Sarvam pace, temperature, and speaker inside bounded limits.

HuBERT is a separate pretrained feature extractor for prosody similarity and validation. Vidiolingua does not train HuBERT from scratch and does not use HuBERT as a replacement for XTTS or Sarvam.

# 2026-05-06 Speaker-Aware Dubbing Addendum

Speaker analysis now writes `voice_assignment_plan.json` for downstream TTS.

XTTS remains the primary speaker-reference backend for supported global
languages. Multi-speaker XTTS jobs require per-speaker references for
speaker-aware routing; the backend no longer silently reuses one reference for
multiple detected speakers unless explicitly configured with
`VIDIOLINGUA_ALLOW_SINGLE_REFERENCE_FOR_ALL_SPEAKERS=true`.

Sarvam remains managed Indian-language TTS, not exact speaker cloning. For
Sarvam jobs, Vidiolingua can select a preset voice per detected speaker using a
voice-profile hint and manual override. These hints are labeled as voice fit
only (`masculine_voice_fit`, `feminine_voice_fit`, `neutral`, `unknown`) and are
not identity or demographic certainty.

# 2026-05-06 Reference Mode Addendum

Reference mode is now normalized as `uploaded`, `auto_extract`, or `none`.
Sarvam accepts `none`; XTTS accepts `uploaded` or `auto_extract` and rejects
`none` with a clear upload validation error. XTTS auto-extract writes a
validated candidate WAV under the job-local `speaker_analysis\references`
folder before TTS uses it.
