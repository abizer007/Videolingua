# Phase 3C IndicF5 Fresh Setup Plan

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

This began as a plan-only document. The approved quarantine/fresh-scaffold step
has now been completed without installing dependencies or downloading models.

## Goals

- Use a clean `.venv_indicf5`.
- Use Python 3.11.11 from the same `.uv_python` base that worked for IndicTrans2.
- Keep IndicF5 fully isolated from `.venv_tts`, `.venv_api`, `.venv_asr`, `.venv_bgm`, and `.venv_indictrans2`.
- Store model/cache artifacts under `models\indicf5` and workspace-local caches.
- Keep failure loud and debuggable.
- Do not use Indic Parler.

## Recommended Fresh Paths

```text
D:\Vidiolingua\.venv_indicf5
D:\Vidiolingua\models\indicf5
D:\Vidiolingua\.hf_cache\indicf5
D:\Vidiolingua\outputs\validation\indicf5_worker_tmp
```

Python:

```text
D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe
```

## Fresh Files Prepared

- `requirements-indicf5.txt`: clean minimal IndicF5-only dependency set.
- `scripts\setup_indicf5_env.ps1`: dry-run-first setup script.
- `workers\indicf5_worker.py`: clean isolated worker scaffold.
- `voice\engines\indicf5_engine.py`: worker-subprocess adapter.
- `app\services\indicf5_tts_service.py`: thin wrapper around the worker-backed engine.
- `docs\INDICF5_SETUP.md`: fresh setup guide.

Old failed files are archived under `_legacy\failed_indicf5_attempt_20260429`.

## Proposed Setup Commands For Next Approval

Do not run until the install step is approved.

```powershell
cd D:\Vidiolingua

D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe -m venv .venv_indicf5

.\.venv_indicf5\Scripts\python.exe -m ensurepip --upgrade --default-pip
.\.venv_indicf5\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

.\.venv_indicf5\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121

.\.venv_indicf5\Scripts\python.exe -m pip install -r requirements-indicf5.txt
```

If CUDA wheels fail, stop and report. Do not fall back to CPU silently.

## Proposed Environment Variables

```powershell
$env:VIDIOLINGUA_INDICF5_PYTHON="D:/Vidiolingua/.venv_indicf5/Scripts/python.exe"
$env:VIDIOLINGUA_INDICF5_MODEL="ai4bharat/IndicF5"
$env:VIDIOLINGUA_INDICF5_MODEL_DIR="D:/Vidiolingua/models/indicf5"
$env:VIDIOLINGUA_INDICF5_DEVICE="cuda"
$env:VIDIOLINGUA_INDICF5_BATCH_SIZE="1"
$env:VIDIOLINGUA_INDICF5_TIMEOUT_SECONDS="300"
$env:VIDIOLINGUA_REFERENCE_TEXT="Exact transcript of the reference audio."
```

## Fresh Worker Contract

Request JSON:

```json
{
  "text": "Kannada target text",
  "target_language": "kn",
  "output_path": "outputs/validation/indicf5_kn.wav",
  "reference_audio_path": "test_speaker_ref.wav",
  "reference_text": "Exact transcript of the reference audio.",
  "model_name": "ai4bharat/IndicF5",
  "model_dir": "models/indicf5",
  "device": "cuda",
  "batch_size": 1
}
```

Response JSON:

```json
{
  "ok": true,
  "engine": "indicf5",
  "output_path": "outputs/validation/indicf5_kn.wav",
  "model_name": "ai4bharat/IndicF5",
  "device": "cuda",
  "used_reference_audio": true,
  "used_reference_text": true,
  "fallback_used": false
}
```

Error JSON:

```json
{
  "ok": false,
  "engine": "indicf5",
  "error": "clear failure message",
  "model_name": "ai4bharat/IndicF5",
  "device": "cuda"
}
```

## Implementation Rules

- Worker must run in `.venv_indicf5`.
- Parent process writes request JSON and reads response JSON.
- Parent process uses a workspace-local temp directory.
- Worker sets `HF_HOME`, `HF_MODULES_CACHE`, `TMP`, `TEMP`, and `NUMBA_CACHE_DIR` to workspace-local paths.
- Worker validates reference audio path and reference text before model loading.
- Worker must not import XTTS, Coqui TTS, IndicTrans2, Llama, deep-translator, gTTS, ElevenLabs, Hume, or Indic Parler.
- Worker uses CUDA first on RTX 4050 and fails loudly if CUDA was explicitly requested but unavailable.
- Use `batch_size=1`.
- Clean up GPU memory on exit with process isolation and `torch.cuda.empty_cache()` in failure paths.

## Validation Plan After Approval

Light checks first:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Exact transcript of the reference audio." --cloning-required true --output outputs\validation\router_kn_phase3c_plan.wav --dry-run
```

After install/model access:

```powershell
.\.venv_indicf5\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"

.\.venv_api\Scripts\python.exe -m tools.validate_indicf5_voice --text "ಇದು ಪರೀಕ್ಷೆ." --reference test_speaker_ref.wav --reference-text "Exact transcript of the reference audio." --language kn --output outputs\validation\indicf5_kn_phase3c.wav
```

Do not run the full video pipeline until small worker-level validation passes.

## Risks

- Existing `.venv_indicf5` is Python 3.12.13 and should not be trusted.
- IndicF5 model access may be gated on Hugging Face.
- Windows compatibility may require careful cache/temp path handling.
- CUDA OOM is possible on RTX 4050 if the model is heavier than expected.
- Reference text quality matters; do not substitute target text for reference transcript.

## Decision Point

Quarantine and fresh scaffold are complete. Awaiting user approval before
installing `.venv_indicf5`, downloading IndicF5 models, or enabling real model
invocation.
