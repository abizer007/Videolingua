# Runtime Environment Matrix - 2026-05-06

Safe capture policy: no installs, no venv mutation, no pipeline run, no model
load, no local IndicF5 execution. Package versions were read with
`importlib.metadata`. CUDA checks imported `torch` only; no model code was
loaded.

## Environment Inventory

Detected top-level runtime directories:

```text
.venv
.venv311
.uv_python
.venv_asr
.venv_tts
.venv_bgm
.venv_api
.venv_indictrans2
.venv_indicf5
.venv_prosody
```

## Matrix

| Runtime | Python executable | Python | Available | Key packages verified | CUDA / device | Why it exists | Must not import / mutate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `.venv_api` | `D:\Vidiolingua\.venv_api\Scripts\python.exe` | 3.11.11 | yes | fastapi 0.136.1; uvicorn 0.46.0; requests 2.33.1; torch/TTS/transformers/numpy not detected | Not applicable; torch absent | FastAPI backend, job store, orchestration, lightweight validation tools. Keeps API startup free of heavy ML imports. | Must not eagerly import XTTS, IndicTrans2, IndicF5, HuBERT, or model weights. No dependency installs in this task. |
| `.venv_tts` | `D:\Vidiolingua\.venv_tts\Scripts\python.exe` | 3.11.11 | yes | TTS 0.22.0; torch 2.5.1+cpu; torchaudio 2.5.1+cpu; transformers 4.46.3; numpy 1.26.4; requests 2.33.1 | CUDA false; GPU none | Known-good XTTS/Coqui runtime for speaker-reference global language routes, including protected French path. | Must not import or install IndicTrans2/IndicF5 stacks; must not mutate because XTTS dependency drift can break the working path. |
| `.venv_indictrans2` | `D:\Vidiolingua\.venv_indictrans2\Scripts\python.exe` | 3.11.11 | yes | torch 2.5.1+cu121; torchvision 0.20.1+cu121; torchaudio 2.5.1+cu121; transformers 4.51.3; IndicTransToolkit 1.1.1; indictranstoolkit 1.1.1; numpy 2.2.6; requests 2.33.1 | CUDA true; CUDA 12.1; NVIDIA GeForce RTX 4050 Laptop GPU | Isolated IndicTrans2 translation worker runtime for supported Indic pairs. Uses model-specific dependencies, workspace caches, CUDA/fp16, batch size 1. | Must not import Coqui XTTS or IndicF5. Must not be used as FastAPI runtime. |
| `.venv_indicf5` | `D:\Vidiolingua\.venv_indicf5\Scripts\python.exe` | 3.11.11 | yes, quarantined | torch 2.5.1+cu121; torchvision 0.20.1+cu121; torchaudio 2.5.1+cu121; transformers 4.57.6; f5-tts 1.1.20; numpy 2.4.3; fastapi 0.136.1; uvicorn 0.46.0; requests 2.33.1 | CUDA true; CUDA 12.1; NVIDIA GeForce RTX 4050 Laptop GPU | Disabled/local experimental IndicF5 sandbox retained for future approved work. | Must not be loaded locally in current production path; must not be enabled without explicit approval; must not disturb `.venv_tts` or `.venv_indictrans2`. |
| `.venv_prosody` | `D:\Vidiolingua\.venv_prosody\Scripts\python.exe` | 3.11.11 | yes | torch metadata 2.11.0 and import 2.11.0+cpu; transformers 5.8.0; numpy 2.4.4; soundfile 0.13.1 | CUDA false; GPU none | HuBERT/prosody feature extraction and adapter validation runtime. Keeps transformers/torch prosody stack away from XTTS/IndicTrans2. | Must not be used for TTS/translation execution. HuBERT failures should report unavailable/failed evidence, not break XTTS/Sarvam routing. |
| `.venv_asr` | `D:\Vidiolingua\.venv_asr\Scripts\python.exe` | 3.11.11 | yes | whisperx 3.8.5; faster-whisper 1.2.1; torch 2.8.0+cpu; torchaudio 2.8.0; pyannote.audio 4.0.4; transformers 4.57.6; numpy 2.4.4 | CUDA false; GPU none | ASR and PyAnnote diarization runtime. Included because ASR is a first-class pipeline stage. | Must not expose HF/PyAnnote token values. |
| `.uv_python` | `D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe` | 3.11.11 | yes | Local CPython runtime, package list not probed as app runtime | Not applicable | Used by setup scripts to create Python 3.11 venvs, avoiding system Python 3.13 conflicts. | Must not be treated as a pipeline stage environment. |

## Config / Secret Presence Check

Safe env-file check, values not printed:

| File | Exists | `SARVAM_API_KEY` key present | `NEXT_PUBLIC_API_URL` key present | `NEXT_PUBLIC*SARVAM*` keys |
| --- | --- | --- | --- | --- |
| `backend\.env` | yes | yes | no | 0 |
| `NEW_Frontend\.env.local` | yes | no | yes | 0 |
| `.env` | no | no | no | 0 |

Conclusion: Sarvam is configured backend-side only in this workspace. No Sarvam
frontend public key was observed.

## Per-Runtime Notes

### `.venv_api`

Verified: API package versions are lightweight. This matches
`backend\main.py`, `backend\pipeline_runner.py`, and setup docs: FastAPI creates
jobs and launches subprocesses rather than importing every ML model at startup.

Status: protected from heavy dependency drift.

### `.venv_tts`

Verified: this is the XTTS runtime used by TTS stage subprocesses. It is
CPU-only in the current known-good state. Docs repeatedly treat CUDA enablement
in this runtime as a dependency change requiring approval.

Status: protected; do not mutate.

### `.venv_indictrans2`

Verified: this runtime has CUDA torch and IndicTransToolkit. It is called by
`translation\engines\indictrans2_engine.py`, which serializes requests to JSON
and invokes `workers.indictrans2_worker`.

Status: active for supported Indic translation pairs.

### `.venv_indicf5`

Verified: runtime exists and CUDA torch is available, but docs and router policy
keep it disabled. Historical reports show real generation did not complete
because of API mismatch and load/runtime issues.

Status: quarantined/local experimental.

### `.venv_prosody`

Verified: `voice\hubert_prosody.py` detects this Python and invokes
`workers\hubert_prosody_worker.py`. If absent, the wrapper writes
`status=unavailable` evidence instead of blocking the main route.

Status: evidence layer, not required for core XTTS/Sarvam path.

## Isolation Conflicts Captured

| Conflict / failure | Isolated by |
| --- | --- |
| XTTS depends on a known-good Coqui/Torch/Transformers combination. | `.venv_tts` |
| IndicTrans2 needs CUDA torch, IndicTransToolkit, remote-code HF model cache, and batch-size/device policy. | `.venv_indictrans2` + `workers\indictrans2_worker.py` |
| IndicF5 local Windows execution hit timeout/API/device issues and should not load in production. | `.venv_indicf5` quarantine + router disabled policy |
| HuBERT/transformers feature extraction should not alter the TTS or translation stacks. | `.venv_prosody` + optional/unavailable reporting |
| API startup must avoid importing torch/TTS/numpy. | `.venv_api` plus subprocess boundaries |

