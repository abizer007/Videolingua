# IndicF5 Fresh Setup

Date refreshed: 2026-04-29

This document replaces the failed earlier IndicF5 attempt. The old runtime files
and artifacts are archived under:

```text
_legacy\failed_indicf5_attempt_20260429
```

Fresh `.venv_indicf5` has now been created and dependencies are installed. The
`ai4bharat/IndicF5` model files downloaded successfully, but real generation is
currently blocked by upstream `f5-tts` API compatibility issues:

```text
load_model() missing 1 required positional argument: 'ckpt_path'
argument of type 'torch.device' is not iterable
```

The `ckpt_path` mismatch was patched in the worker. The current remaining
blocker is local model loading/memory behavior after the device compatibility
patch. See:

```text
docs\PHASE3C_INDICF5_INSTALL_REPORT_2026-04-29.md
docs\PHASE3C_INDICF5_COMPAT_FIX_REPORT_2026-04-29.md
docs\PHASE3C_INDICF5_MEMORYSAFE_COMPAT_REPORT_2026-04-29.md
```

## Runtime Target

Use only:

```text
D:\Vidiolingua\.venv_indicf5
```

Preferred Python:

```text
D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe
```

Do not mutate `.venv_tts`, `.venv_indictrans2`, `.venv_api`, `.venv_asr`, or
`.venv_bgm`.

## Setup Command

Dry run:

```powershell
.\scripts\setup_indicf5_env.ps1
```

Install command used after approval:

```powershell
.\scripts\setup_indicf5_env.ps1 -Run
```

The script targets only `.venv_indicf5`, installs CUDA PyTorch there, then
installs `requirements-indicf5.txt` there. Model validation still requires the
worker compatibility fix described in the install report.

## Required Inputs

IndicF5 requires:

- target text
- reference audio
- exact transcript of the reference audio

The reference transcript can come from:

```text
--reference-text
--reference-text-path
VIDIOLINGUA_REFERENCE_TEXT
VIDIOLINGUA_REFERENCE_TEXT_PATH
sidecar .txt beside the reference wav
```

Do not substitute target text as reference text.

## Validation

Kannada policy check:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Exact transcript of the reference audio." --cloning-required true --output outputs\validation\router_kn_phase3c_fresh_scaffold.wav --dry-run
```

Missing reference text should fail:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\router_kn_missing_reftext_phase3c_fresh_scaffold.wav --dry-run
```

French should continue routing to XTTS:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\router_fr_phase3c_fresh_scaffold.wav --dry-run
```

## Model And HF Access

Default model:

```text
ai4bharat/IndicF5
```

The model is gated and requires Hugging Face access. Do not start interactive
login from automation. The fresh model/cache location should stay under:

```text
models\indicf5
.hf_cache\indicf5
```

Downloaded files now present:

```text
models\indicf5\IndicF5\config.json
models\indicf5\IndicF5\model.py
models\indicf5\IndicF5\model.safetensors
models\indicf5\IndicF5\checkpoints\vocab.txt
```

## CUDA Notes

On RTX 4050, use CUDA with `batch_size=1`. The worker fails loudly if CUDA is
explicitly requested but unavailable. CPU fallback should not happen silently.

Current local status: diagnose-only passes, but load-only model validation
timed out after 600 seconds. Do not run generation locally until a safer
memory/model-load strategy is approved.

## Forbidden Backends

Indic Parler is forbidden. Generic fallback is forbidden when cloning is
required. Browser/system TTS and preset-speaker backends must not masquerade as
voice cloning.

## Rollback

Disable IndicF5 routing by setting:

```text
VIDIOLINGUA_ENABLE_INDICF5=false
```

Restore quarantined files only if explicitly approved, using the manifest in
`_legacy\failed_indicf5_attempt_20260429`.
