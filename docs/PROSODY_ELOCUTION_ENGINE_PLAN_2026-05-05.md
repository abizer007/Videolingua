# Prosody & Elocution Engine Plan - 2026-05-05

## Positioning

Vidiolingua uses pretrained HuBERT speech representations plus a lightweight project-trained prosody adapter to compare and guide rhythm, pauses, energy, and delivery across source and dubbed speech.

## Implementation Plan

1. Add source prosody analysis after ASR.
2. Add punctuation-aware TTS prosody planning after translation.
3. Keep canonical translations unchanged and write optional `tts_prepared_text`.
4. Apply safe XTTS and Sarvam preset controls before TTS.
5. Run prosody validation after generated audio.
6. Extract HuBERT features in `.venv_prosody` only.
7. Train a lightweight adapter under ignored `models/prosody_hubert_adapter`.
8. Surface reports in job manifest, pipeline results, metrics, and frontend panels.

## Safety Constraints

- XTTS, Sarvam, and IndicTrans2 remain the existing primary routes.
- IndicF5 stays disabled.
- No generic fallback is introduced.
- HuBERT failure reports unavailable and does not fail French/Kannada dubbing.
- Protected outputs and model folders are not regenerated or overwritten.
