# Phase 3C IndicF5 Compatibility And Memory Plan

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Root Cause

Installed package:

```text
f5-tts 1.1.20
```

Installed API signature:

```text
load_model(model_cls, model_cfg, ckpt_path, mel_spec_type='vocos', vocab_file='', ode_method='euler', use_ema=True, device='cuda')
```

Downloaded custom model code:

```text
models\indicf5\IndicF5\model.py
```

Call site:

```text
model.py line 53: self.ema_model = torch.compile(load_model(
model.py line 58: device=device
```

`model.py` creates:

```text
model.py line 40: device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
```

Current `f5_tts.infer.utils_infer.load_checkpoint` expects a string-like device:

```text
utils_infer.py line 194: if "cuda" in device
```

So two compatibility problems exist:

1. `ckpt_path` is required by installed `f5-tts`, but AI4Bharat `model.py` does not pass it.
2. `device` is a `torch.device` object, but installed `f5-tts` checks string containment.

## Resolved Paths

Model directory:

```text
models\indicf5\IndicF5
```

Checkpoint:

```text
models\indicf5\IndicF5\model.safetensors
```

Vocab:

```text
models\indicf5\IndicF5\checkpoints\vocab.txt
```

## Patch Strategy

Patch project worker code, not installed packages.

Safer target:

```text
workers\indicf5_worker.py
```

Reason:

- site-packages edits are brittle and hard to reproduce
- `.venv_indicf5` may be recreated later
- project worker code can document and guard all compatibility behavior
- worker isolation protects API/TTS/XTTS processes from heavy model imports

## Memory Strategy

Repeated full generation is risky on this laptop. A previous attempt caused an
OS-level `python.exe` out-of-memory notification.

Validation must proceed in stages:

1. diagnose-only: validate paths/runtime without loading model
2. load-only: load model without generation
3. tiny generation: one short Kannada sentence only
4. router validation only after direct worker generation succeeds

The parent engine now uses a configurable subprocess timeout and kills the child
process with `taskkill /PID <pid> /T /F` on Windows timeout.

Default smoke controls:

```text
VIDIOLINGUA_INDICF5_DEVICE=cuda
VIDIOLINGUA_INDICF5_DTYPE=float16
VIDIOLINGUA_INDICF5_TIMEOUT_SECONDS=600
VIDIOLINGUA_INDICF5_MODEL_DIR=models\indicf5\IndicF5
VIDIOLINGUA_INDICF5_CKPT_PATH=models\indicf5\IndicF5\model.safetensors
VIDIOLINGUA_INDICF5_MAX_TEXT_CHARS=120
VIDIOLINGUA_INDICF5_MAX_REF_SECONDS=12
```

## Stop Conditions

Stop local validation if load-only or tiny generation times out twice, causes OS
OOM, or requires package installs/site-packages edits.
