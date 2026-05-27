# Sarvam TTS Setup

Sarvam AI is the managed Indian-language TTS backend for VidioLingua. It is used
for Hindi, Tamil, Bengali, Telugu, Kannada, Malayalam, Marathi, Gujarati,
Punjabi, and Odia. It is not exact voice cloning.

## Local Env

Store the API key only in `backend\.env` or another gitignored local env file:

```text
SARVAM_API_KEY=
VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam
VIDIOLINGUA_ENABLE_SARVAM=true
VIDIOLINGUA_SARVAM_MODEL=bulbul:v3
VIDIOLINGUA_SARVAM_SPEAKER=shubh
VIDIOLINGUA_SARVAM_PACE=1.0
VIDIOLINGUA_SARVAM_TEMPERATURE=0.45
VIDIOLINGUA_SARVAM_SAMPLE_RATE=24000
VIDIOLINGUA_SARVAM_OUTPUT_CODEC=wav
VIDIOLINGUA_SARVAM_TIMEOUT_SECONDS=120
VIDIOLINGUA_ENABLE_INDICF5=false
VIDIOLINGUA_INDICF5_EXECUTION_MODE=local_disabled
```

Never commit the API key. Never print it in logs or reports. Mask it as
`sk_****abcd`.

## Validation

Dry-run:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_dry_run.wav --dry-run
```

Real Kannada WAV:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_test.wav
```

Router validation:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Exact transcript of the reference audio." --cloning-required true --output outputs\validation\router_kn_sarvam_test.wav
```

Expected Sarvam metadata:

```text
engine=sarvam
managed_tts=true
exact_voice_clone=false
used_reference_audio=false
speaker_preservation=not_supported
```

Sarvam writes provider-specific raw and clean sidecars during real validation:

```text
<output>.sarvam_raw.wav
<output>.sarvam_clean.wav
```

If raw audio is near full scale, Sarvam applies safe peak normalization before
strict final validation. This is not voice cloning and does not change routing.

## Switching Backends

```text
VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam|indicf5|disabled
```

Keep `indicf5` disabled unless there is explicit approval to resume local
experiments. Indic Parler is forbidden.

## Speaker-Aware Managed Voice Selection - 2026-05-06

Sarvam speaker-aware routing uses `speaker_analysis\voice_assignment_plan.json`
when diarization computes speakers. This is managed preset voice selection, not
voice cloning.

Default profile config:

```text
config\sarvam_voice_profiles.example.json
```

Current local code/config proves `shubh` as the supported default speaker, so
the example maps all voice-fit hints to `shubh` until a verified supported
Sarvam speaker list is configured.

Manual per-speaker override can be supplied later with:

```text
VIDIOLINGUA_SARVAM_SPEAKER_OVERRIDES_JSON={"SPEAKER_00":"shubh"}
```

UI and reports must use wording such as `voice profile hint`,
`masculine_voice_fit`, `feminine_voice_fit`, `neutral`, and `unknown`. This is
not identity or demographic certainty; it is only a managed-voice fit hint.

## Reference Audio and Auto-Analyze - 2026-05-06

Sarvam upload requests may use `reference_mode=none`, `uploaded`, or
`auto_extract`. `none` is valid because Sarvam is managed TTS, not exact
speaker cloning. `auto_extract` asks the backend to analyze speaker/reference
candidates for voice-fit hints; if unavailable, the run continues with
`voice_profile_hint=unknown` and the default Sarvam speaker.
