# Phase 3C IndicF5 Compatibility Fix Report

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Summary

The original blocker was confirmed:

```text
load_model() missing 1 required positional argument: 'ckpt_path'
```

Installed `f5-tts 1.1.20` expects:

```text
load_model(model_cls, model_cfg, ckpt_path, mel_spec_type='vocos', vocab_file='', ode_method='euler', use_ema=True, device='cuda')
```

The downloaded `models\indicf5\IndicF5\model.py` calls `load_model(...)`
without `ckpt_path`, matching an older API.

## Fixes Tried

### Option A: AI4Bharat Repo Install

Attempted inside `.venv_indicf5` only:

```powershell
.\.venv_indicf5\Scripts\python.exe -m pip install --upgrade --force-reinstall git+https://github.com/AI4Bharat/IndicF5.git
```

Result: timed out after 20 minutes. The timed-out install partially changed
`.venv_indicf5` torch packages to mismatched versions. This was repaired inside
`.venv_indicf5` only by force-reinstalling the approved CUDA PyTorch trio.

Verified final state:

```text
torch 2.5.1+cu121
torchvision 0.20.1+cu121
torchaudio 2.5.1+cu121
CUDA true
GPU NVIDIA GeForce RTX 4050 Laptop GPU
pip check: no broken requirements
```

### Option B: Worker ckpt_path Patch

Patched `workers\indicf5_worker.py` to resolve and validate:

```text
models\indicf5\IndicF5\model.safetensors
```

The worker now detects whether installed `load_model` requires `ckpt_path` and
injects the local checkpoint path when needed. `voice\engines\indicf5_engine.py`
passes `checkpoint_path` through the worker request.

## Current Blocker

The `ckpt_path` error is fixed, but real generation still does not complete.

First post-patch run:

```text
worker subprocess timed out after 300 seconds
```

Second and final allowed real run with longer timeout:

```text
IndicF5 model load failed: argument of type 'torch.device' is not iterable
```

Root cause inference: AI4Bharat's `model.py` constructs `device =
torch.device(...)` and passes that object into current `f5_tts` loading code.
Current `f5_tts.infer.utils_infer.load_checkpoint` checks `"cuda" in device`,
which expects a string-like device, not a `torch.device` object.

Per the no-looping rule, real generation attempts stopped here.

## Real Kannada WAV Status

Not generated.

Absent paths:

```text
outputs\validation\indicf5_kn_phase3c_compat.wav
outputs\validation\router_kn_phase3c_compat.wav
```

The validation used placeholder reference text, so even if it had completed it
would have been technical-only validation, not a voice-quality/fidelity claim.

## Safety Validation

- Missing Kannada reference text still fails clearly.
- French dry-run still selects `xtts`.
- No generic fallback was used.
- No Indic Parler runtime imports or requirements entries were found.
- Compile validation passed.
- XTTS health checks passed.

## Files Changed

- `workers\indicf5_worker.py`
- `voice\engines\indicf5_engine.py`
- `docs\PHASE3C_INDICF5_COMPAT_FIX_REPORT_2026-04-29.md`
- `docs\INDICF5_SETUP.md`
- `docs\TROUBLESHOOTING.md`
- `COMMAND_LOG.md`

## Protected Assets

- `.venv_tts`: untouched
- `.venv_indictrans2`: untouched
- `.venv_api`, `.venv_asr`, `.venv_bgm`: no package installs
- `models\xtts_v2`: untouched
- `outputs\french_official_test`: untouched
- Full video pipeline: not run
- Indic Parler: not installed or imported

## Next Recommended Fix

Do not retry real generation unchanged. The next focused fix should adapt the
worker's monkeypatch so current `f5_tts` receives a string device, not a
`torch.device`, when `ai4bharat/IndicF5` calls `load_model`.

Likely direction:

- extend the worker's `load_model` wrapper to coerce `device=torch.device(...)`
  into `device='cuda'` or `device='cpu'`
- keep `ckpt_path` injection
- rerun one real worker validation

This should be a source-only worker patch, not a new dependency install.
