# Validate Working XTTS Pipeline

Workspace: `D:\Vidiolingua`

Use these commands to validate the current practical XTTS setup without reinstalling dependencies or deleting artifacts.

## 1. Syntax Check

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app
```

## 2. Transformers Compatibility Check

```powershell
.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"
```

Expected:

```text
BeamSearchScorer import OK
```

## 3. Torch And CUDA Report

```powershell
.\.venv_tts\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('cuda version:', torch.version.cuda); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Current known-good baseline:

```text
torch: 2.5.1+cpu
cuda: False
cuda version: None
gpu: none
```

CUDA is not enabled in the current working `.venv_tts` baseline. Treat any CUDA enablement as a dependency change requiring explicit approval.

## 4. XTTS Model File Check

```powershell
Get-Item -LiteralPath models\xtts_v2\config.json, models\xtts_v2\model.pth, models\xtts_v2\vocab.json, models\xtts_v2\speakers_xtts.pth | Select-Object FullName, Length, LastWriteTime
```

All four files must exist. The `model_path` passed to the pipeline must be the directory:

```text
models\xtts_v2
```

It must not be:

```text
models\xtts_v2\model.pth
```

## 5. Known-Good Output Artifact Check

```powershell
Get-Item -LiteralPath outputs\french_official_test\pipeline_result.json, outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4 | Select-Object FullName, Length, LastWriteTime
```

## 6. Practical Pipeline Smoke Run

Run this only after runtime changes, or when explicitly confirming end-to-end behavior. It writes to a separate output directory and does not overwrite the known-good `outputs\french_official_test` directory.

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language fr --reference test_speaker_ref.wav --model-path models\xtts_v2 --mode practical --output-dir outputs\french_official_test_after_cleanup
```

Expected final output:

```text
outputs\french_official_test_after_cleanup\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

## 7. Optional MP4 Stream Probe

```powershell
ffprobe -hide_banner -show_streams -show_format outputs\french_official_test_after_cleanup\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

Sanity checks:

- Video stream exists.
- Audio stream exists.
- Duration is close to the input duration.
- Audio is AAC at a normal sample rate and bitrate.
- Video resolution and frame rate are expected for the source.

## Stop Conditions

Stop and investigate before changing dependencies if any of these fail:

- `BeamSearchScorer` cannot be imported in `.venv_tts`.
- Any required `models\xtts_v2` file is missing.
- The resolved XTTS model path is a checkpoint file instead of the model directory.
- The practical smoke run fails after a runtime code change.
