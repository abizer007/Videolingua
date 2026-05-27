# Phase 3C IndicF5 Memory-Safe Compatibility Report

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Summary

Applied a source-only worker compatibility patch for the AI4Bharat IndicF5
custom model code and added staged diagnostic/load-only behavior. No packages
were installed, no torch packages were reinstalled, no models were downloaded,
and no full video pipeline was run in this phase.

The worker diagnose-only check passed. The model load-only check timed out and
triggered the stop condition, so tiny generation and router-real generation were
not attempted.

## Root Cause

Installed `f5-tts 1.1.20` exposes:

```text
load_model(model_cls, model_cfg, ckpt_path, mel_spec_type='vocos', vocab_file='', ode_method='euler', use_ema=True, device='cuda')
```

Downloaded AI4Bharat custom code:

```text
models\indicf5\IndicF5\model.py
```

Important call sites:

```text
model.py line 40: device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.py line 53: self.ema_model = torch.compile(load_model(
model.py line 58: device=device
```

Installed `f5_tts.infer.utils_infer.load_checkpoint` expects string-like device:

```text
utils_infer.py line 194: if "cuda" in device
```

Therefore the compatibility fix needs both:

- local `ckpt_path` injection
- `torch.device(...)` to string coercion at the worker monkeypatch boundary

## Code Patched

`workers\indicf5_worker.py`:

- accepts `--diagnose`, `--load-only`, and `--no-generate`
- supports request fields `diagnose_only`, `load_only`, and `generate`
- reads request JSON with `utf-8-sig` tolerance
- resolves `model_dir`, `checkpoint_path`, and `vocab_path`
- supports `VIDIOLINGUA_INDICF5_CKPT_PATH`
- validates reference audio, reference text, output writability, checkpoint, vocab, max text chars, and max reference seconds before model load
- injects local `ckpt_path` when current `f5_tts.load_model` requires it
- coerces `device` to string before calling current `f5_tts.load_model`
- logs memory snapshots when available
- writes response JSON on failure

`voice\engines\indicf5_engine.py`:

- supports `VIDIOLINGUA_INDICF5_CKPT_PATH`
- defaults timeout to `600`
- passes dtype, max text chars, and max reference seconds
- uses `Popen` and attempts `taskkill /PID <pid> /T /F` on timeout

## Resolved Paths

Model directory:

```text
D:\Vidiolingua\models\indicf5\IndicF5
```

Checkpoint:

```text
D:\Vidiolingua\models\indicf5\IndicF5\model.safetensors
```

Vocab:

```text
D:\Vidiolingua\models\indicf5\IndicF5\checkpoints\vocab.txt
```

## Validation Results

Compile:

```text
passed
```

IndicF5 env health:

```text
torch: 2.5.1+cu121
cuda: True
device: NVIDIA GeForce RTX 4050 Laptop GPU
```

Base imports:

```text
IndicF5 base imports OK
```

Diagnose-only:

```text
passed
```

Diagnostic response reported:

```text
device: cuda
dtype: float16
cuda_available: true
reference_duration_sec: 10.0
model_loaded: false
generated: false
```

Load-only:

```text
failed: IndicF5 worker load-only timed out after 600 seconds and was killed.
```

No surviving `.venv_indicf5` Python worker process was found after the timeout.

## Generation Status

Tiny real Kannada generation was not attempted because load-only timed out.

No WAV was created:

```text
outputs\validation\indicf5_kn_phase3c_memorysafe.wav
```

Router-real Kannada validation was not attempted because direct worker
generation did not pass.

## OOM Status

No new OS-level OOM was directly observed by this agent during this phase, but
load-only timing out means local model loading is still not safe enough to
continue. The previous OS-level `python.exe` out-of-memory notification remains
a serious risk.

## Safety Status

Missing reference text and French XTTS checks were not rerun after the load-only
stop condition. The prior Phase 3C checks showed:

- missing Kannada reference text fails clearly
- French routes to XTTS
- no generic fallback
- no Indic Parler

No code in this patch imports Indic Parler, XTTS, IndicTrans2, deep-translator,
gTTS, Hume, or ElevenLabs in the IndicF5 worker.

## Protected Assets

- `.venv_tts`: untouched
- `.venv_indictrans2`: untouched
- `.venv_api`, `.venv_asr`, `.venv_bgm`: no package installs
- `models\xtts_v2`: untouched
- `outputs\french_official_test`: untouched
- Full video pipeline: not run
- Indic Parler: not installed or imported

## Recommendation

Stop local IndicF5 generation on this laptop/runtime for now. Keep the
diagnostic scaffolding and model files, but do not continue brute-force local
generation until the memory/model-load strategy changes.

Recommended next options:

- try IndicF5 on a cloud GPU with more memory
- keep IndicF5 disabled for local demos and use IndicTrans2 plus XTTS-supported languages
- investigate a lighter Indic TTS backend later
- manually tune Windows pagefile/CUDA memory outside automation before another local load-only attempt
