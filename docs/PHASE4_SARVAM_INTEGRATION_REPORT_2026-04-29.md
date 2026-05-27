# Phase 4 Sarvam Integration Report - 2026-04-29

Phase 4 adds Sarvam AI as the managed Indian-language TTS backend.

## Scope

Changed routing so Hindi, Tamil, Bengali, Telugu, Kannada, Malayalam, Marathi,
Gujarati, Punjabi, and Odia select Sarvam by default when
`VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam`.

Added a lightweight Sarvam engine that:

- reads `SARVAM_API_KEY` from env
- posts to `https://api.sarvam.ai/text-to-speech`
- uses `bulbul:v3`, `wav`, `24000`, `pace=1.0`, and `temperature=0.45`
- decodes the first base64 WAV from `audios`
- validates the generated WAV
- records honest managed-TTS metadata

## Safety

No local IndicF5 model load or generation should be run in this phase. IndicF5
configuration is set to disabled/local-disabled. `.venv_tts`,
`.venv_indictrans2`, `models\xtts_v2`, and `outputs\french_official_test` are
protected.

## Validation Commands

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_dry_run.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Exact transcript of the reference audio." --cloning-required true --output outputs\validation\router_kn_sarvam_dry_run.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "यह एक परीक्षण है।" --target-language hi --reference test_speaker_ref.wav --reference-text "Exact transcript of the reference audio." --cloning-required true --output outputs\validation\router_hi_sarvam_dry_run.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\router_fr_xtts_dry_run.wav --dry-run
```

Real Sarvam validation should run only after dry-runs pass.
