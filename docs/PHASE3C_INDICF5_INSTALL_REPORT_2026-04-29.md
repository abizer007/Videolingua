# Phase 3C IndicF5 Install Report

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Summary

Fresh `.venv_indicf5` was created with Python 3.11.11. CUDA PyTorch and IndicF5
dependencies were installed only into `.venv_indicf5`. CUDA works on the NVIDIA
GeForce RTX 4050 Laptop GPU.

`ai4bharat/IndicF5` model files were downloaded into `models\indicf5\IndicF5`,
but real Kannada generation did not complete. The current blocker is an upstream
API mismatch between the downloaded `ai4bharat/IndicF5` `model.py` and installed
`f5-tts 1.1.20`:

```text
load_model() missing 1 required positional argument: 'ckpt_path'
```

No full video pipeline was run.

## Python Used

```text
D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe
```

Created:

```text
D:\Vidiolingua\.venv_indicf5
```

## Commands Run

```powershell
D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe -m venv .venv_indicf5
.\.venv_indicf5\Scripts\python.exe -m ensurepip --upgrade --default-pip
.\.venv_indicf5\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv_indicf5\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
.\.venv_indicf5\Scripts\python.exe -m pip install -r requirements-indicf5.txt
.\.venv_indicf5\Scripts\python.exe -m pip install "f5-tts>=1.1,<2.0" "pydub>=0.25,<1.0"
.\.venv_indicf5\Scripts\hf.exe --help
.\.venv_indicf5\Scripts\hf.exe auth whoami
.\.venv_indicf5\Scripts\hf.exe download ai4bharat/IndicF5 model.py config.json checkpoints/vocab.txt --local-dir models\indicf5\IndicF5
```

Validation commands included config inspection, import checks, a real
`tools.validate_indicf5_voice` attempt, dry-run router checks, XTTS health
checks, and a no-Parler scan. Details are recorded in `COMMAND_LOG.md`.

## Packages Installed

Key package versions:

- `torch 2.5.1+cu121`
- `torchvision 0.20.1+cu121`
- `torchaudio 2.5.1+cu121`
- `transformers 4.57.6`
- `huggingface_hub 0.36.2`
- `soundfile 0.13.1`
- `numpy 2.2.6`
- `f5-tts 1.1.20`
- `pydub 0.25.1`
- `vocos 0.1.0`
- `datasets 4.8.5`
- `ema-pytorch 0.7.9`
- `transformers-stream-generator 0.0.5`
- `wandb 0.26.1`

`pip check` reports no broken requirements.

## CUDA Result

```text
torch: 2.5.1+cu121
cuda: True
cuda version: 12.1
gpu: NVIDIA GeForce RTX 4050 Laptop GPU
```

## Hugging Face Access

HF CLI is available in `.venv_indicf5`.

```text
hf auth whoami -> Abizer007
```

The first worker attempt could not see the login token after `HF_HOME` was
redirected to the workspace. The worker was updated to read the existing local
token before switching to workspace-local caches. After that, the gated
`model.safetensors` download succeeded.

## Model And Cache Paths

Downloaded model files:

```text
models\indicf5\IndicF5\config.json
models\indicf5\IndicF5\model.py
models\indicf5\IndicF5\model.safetensors
models\indicf5\IndicF5\checkpoints\vocab.txt
```

`model.safetensors` size:

```text
1,402,789,408 bytes
```

Workspace-local cache paths:

```text
.hf_cache\indicf5
.hf_cache\indicf5\hub
.runtime_tmp\indicf5
.numba_cache\indicf5
.cache\indicf5
```

The Vocos vocoder began downloading into `.hf_cache\indicf5\hub`; measured cache
files total approximately `54,377,815` bytes.

## Real Kannada Generation

Status: blocked before WAV generation.

Command attempted with the best available sidecar transcript from
`test_speaker_ref.txt`:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_indicf5_voice --text "ಇದು ಕನ್ನಡ ಧ್ವನಿ ಸಂಶ್ಲೇಷಣೆಯ ಪರೀಕ್ಷೆಯಾಗಿದೆ." --reference test_speaker_ref.wav --reference-text <test_speaker_ref.txt contents> --language kn --output outputs\validation\indicf5_kn_phase3c_real.wav
```

Final failure:

```text
IndicF5 worker failed: IndicF5 model load failed: load_model() missing 1 required positional argument: 'ckpt_path'
```

No output WAV was created:

```text
outputs\validation\indicf5_kn_phase3c_real.wav -> absent
```

## Router And Safety Checks

- Missing Kannada reference text dry-run blocks clearly:
  `IndicF5 requires the exact transcript of the reference audio`.
- French dry-run still routes to `xtts`, not IndicF5.
- No generic fallback was used.
- No runtime Indic Parler imports or requirements entries were found.

## Source Files Changed

- `requirements-indicf5.txt`
- `workers\indicf5_worker.py`
- `voice\engines\indicf5_engine.py`
- `docs\INDICF5_SETUP.md`
- `docs\TROUBLESHOOTING.md`
- `COMMAND_LOG.md`
- `docs\PHASE3C_INDICF5_INSTALL_REPORT_2026-04-29.md`

## Protected Assets

- `.venv_tts`: untouched
- `.venv_indictrans2`: untouched
- `.venv_api`, `.venv_asr`, `.venv_bgm`: no package installs
- `models\xtts_v2`: untouched
- `outputs\french_official_test`: untouched
- Full video pipeline: not run

## Next Decision

Real generation now needs a focused compatibility fix for the
`ai4bharat/IndicF5` `model.py` versus installed `f5-tts 1.1.20`. Safe options:

1. Patch the worker to call `f5_tts.infer.utils_infer.load_model` with the
   downloaded `model.safetensors` path expected by the current API.
2. Pin `f5-tts` to an older version matching the model repo's `model.py`, if
   available and Windows-compatible.

Do not run another real generation attempt until one of these approaches is
approved.
