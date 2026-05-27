# IndicTrans2 Setup

IndicTrans2 must run outside `.venv_tts`.

Recommended environment:

```text
.venv_indictrans2
```

Set:

```text
VIDIOLINGUA_INDICTRANS2_PYTHON=D:/Vidiolingua/.venv_indictrans2/Scripts/python.exe
```

## Policy

Supported pairs route to IndicTrans2 in `auto` mode. Unsupported pairs fail unless explicit fallback is enabled.

Phase 3A production behavior:

- `en -> kn`: selected engine is IndicTrans2.
- Missing `.venv_indictrans2` or model invocation fails loudly.
- Llama/deep-translator fallback is blocked for supported pairs unless explicitly configured for a later approved mode.

## RTX 4050 Settings

- Prefer distilled/smaller model variants where available.
- Use CUDA fp16 only in the IndicTrans2 env.
- Use batch size 1 by default.
- Run through `workers/indictrans2_worker.py` so memory is released after translation.

## Validation

```powershell
python -m tools.validate_indictrans2_translation --source-language en --target-language kn --text "This is a test of the translation system." --output outputs/validation/indictrans2_en_kn.json
```

Until the environment and model invocation are installed and approved, this command should fail loudly instead of falling back.
