# IndicF5 Setup

IndicF5 must run outside the known-good `.venv_tts` environment.

Recommended environment:

```text
.venv_indicf5
```

Do not install IndicF5 dependencies into `.venv_tts` unless explicitly approved.

## Requirements

- Accept the `ai4bharat/IndicF5` model terms on Hugging Face if required.
- Configure a Hugging Face token in a local env file or shell.
- Install the approved requirements into `.venv_indicf5`.
- Set `VIDIOLINGUA_INDICF5_PYTHON` to `.venv_indicf5\Scripts\python.exe`.

## Reference Audio

IndicF5 requires:

- clean reference WAV
- exact transcript of that same reference audio

Do not guess the reference transcript. Do not pass target text as the reference transcript.

Phase 3A supported inputs:

```text
--reference-text "Exact transcript"
--reference-text-path path\to\reference.txt
VIDIOLINGUA_REFERENCE_TEXT=Exact transcript
VIDIOLINGUA_REFERENCE_TEXT_PATH=path\to\reference.txt
```

For XTTS these values are ignored. For IndicF5 they are required.

## Kannada Validation

```powershell
python -m tools.validate_indicf5_voice --text "Kannada text" --reference samples/reference_clean.wav --reference-text "Exact transcript of the reference audio." --language kn --output outputs/validation/indicf5_kn.wav
```

## Common Failures

- Missing model access: accept terms and configure token.
- Missing reference audio: provide a valid WAV.
- Missing reference text: provide exact transcript.
- Bad speaker conditioning: use 6-30 seconds of clean single-speaker speech.
- Cache issues: cache keys must include engine, model, language, target text, reference audio hash, reference text hash, and settings.
