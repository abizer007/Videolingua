# Working State: XTTS Practical Pipeline

Captured: 2026-04-28
Workspace: `D:\Vidiolingua`

This document records the known-good practical XTTS cloned dubbing state. Do not use it as permission to reinstall, upgrade, delete, or regenerate environments, models, logs, outputs, or dependency files.

## Known Good Command

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language fr --reference test_speaker_ref.wav --model-path models\xtts_v2 --mode practical --output-dir outputs\french_official_test
```

Known-good final result:

```text
D:\Vidiolingua\outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

Known-good metadata:

```text
D:\Vidiolingua\outputs\french_official_test\pipeline_result.json
```

## Critical XTTS Model Path Rule

The practical pipeline must pass the XTTS model directory to Coqui:

```text
models\xtts_v2
```

Do not pass the checkpoint file as `model_path`:

```text
models\xtts_v2\model.pth
```

Passing `model.pth` as the model path causes Coqui to resolve a nested invalid path like:

```text
models\xtts_v2\model.pth\model.pth
```

## Python Environments

All four virtual environments currently report Python 3.11.11.

| Environment | Python executable | Version |
| --- | --- | --- |
| API | `D:\Vidiolingua\.venv_api\Scripts\python.exe` | Python 3.11.11 |
| ASR | `D:\Vidiolingua\.venv_asr\Scripts\python.exe` | Python 3.11.11 |
| TTS | `D:\Vidiolingua\.venv_tts\Scripts\python.exe` | Python 3.11.11 |
| BGM | `D:\Vidiolingua\.venv_bgm\Scripts\python.exe` | Python 3.11.11 |

## Key Package Versions

Captured with:

```powershell
.\.venv_*\Scripts\python.exe -m pip show TTS torch torchaudio transformers tokenizers whisperx faster-whisper pyannote.audio demucs fastapi uvicorn
```

### `.venv_api`

| Package | Version |
| --- | --- |
| fastapi | 0.136.1 |
| uvicorn | 0.46.0 |
| TTS | not installed |
| torch | not installed |
| torchaudio | not installed |
| transformers | not installed |
| tokenizers | not installed |
| whisperx | not installed |
| faster-whisper | not installed |
| pyannote.audio | not installed |
| demucs | not installed |

### `.venv_asr`

| Package | Version |
| --- | --- |
| torch | 2.8.0 |
| torchaudio | 2.8.0 |
| transformers | 4.57.6 |
| tokenizers | 0.22.2 |
| whisperx | 3.8.5 |
| faster-whisper | 1.2.1 |
| pyannote.audio | 4.0.4 |
| TTS | not installed |
| demucs | not installed |
| fastapi | not installed |
| uvicorn | not installed |

### `.venv_tts`

| Package | Version |
| --- | --- |
| TTS | 0.22.0 |
| torch | 2.5.1+cpu |
| torchaudio | 2.5.1+cpu |
| transformers | 4.46.3 |
| tokenizers | 0.20.3 |
| whisperx | not installed |
| faster-whisper | not installed |
| pyannote.audio | not installed |
| demucs | not installed |
| fastapi | not installed |
| uvicorn | not installed |

### `.venv_bgm`

| Package | Version |
| --- | --- |
| torch | 2.11.0 |
| torchaudio | 2.11.0 |
| demucs | 4.0.1 |
| TTS | not installed |
| transformers | not installed |
| tokenizers | not installed |
| whisperx | not installed |
| faster-whisper | not installed |
| pyannote.audio | not installed |
| fastapi | not installed |
| uvicorn | not installed |

## XTTS Import And Device Baseline

Captured from `.venv_tts`.

```powershell
.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"
```

Result:

```text
BeamSearchScorer import OK
```

```powershell
.\.venv_tts\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('cuda version:', torch.version.cuda); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Result:

```text
torch: 2.5.1+cpu
cuda: False
cuda version: None
gpu: none
```

Note: this confirms the current working TTS environment is CPU-only at capture time. Enabling RTX 4050 CUDA would require dependency changes and is not a SAFE cleanup task.

## Required Files Present

| Path | Exists | Size bytes | Last write time |
| --- | --- | ---: | --- |
| `D:\Vidiolingua\models\xtts_v2\config.json` | yes | 4368 | 2026-04-28 13:53:00 |
| `D:\Vidiolingua\models\xtts_v2\model.pth` | yes | 1867929118 | 2026-04-28 13:52:58 |
| `D:\Vidiolingua\models\xtts_v2\vocab.json` | yes | 361219 | 2026-04-28 13:53:00 |
| `D:\Vidiolingua\models\xtts_v2\speakers_xtts.pth` | yes | 7754818 | 2026-04-28 13:53:02 |
| `D:\Vidiolingua\outputs\french_official_test\pipeline_result.json` | yes | 482 | 2026-04-28 18:55:28 |
| `D:\Vidiolingua\outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4` | yes | 78499361 | 2026-04-28 18:55:26 |

## Known-Good Pipeline Metadata

```json
{
  "jobId": "french_official_test",
  "originalVideo": "http://localhost:8000/api/result/french_official_test/file/input_video.mp4",
  "localizedVideos": [
    {
      "language": "French",
      "url": "http://localhost:8000/api/result/french_official_test/file/Vidiolingua_Test_Official_dubbed_fr.mp4",
      "confidence": 0.88
    }
  ],
  "metrics": {
    "totalTime": 305,
    "languagesProcessed": 1,
    "bgmPreserved": false,
    "speakersDetected": 0
  }
}
```

## Known-Good MP4 Probe Summary

Captured with `ffprobe -hide_banner -show_streams -show_format`.

| Stream | Codec | Details |
| --- | --- | --- |
| Video | H.264 / AVC | 1920x1080, 30 fps, 30.566667 seconds, about 20.38 Mbps |
| Audio | AAC LC | 44100 Hz stereo, 30.573991 seconds, about 152 kbps |
| Container | MP4/MOV | duration 30.573991 seconds, size 78499361 bytes, about 20.54 Mbps |

## Git Status At Capture

The repository was already dirty at capture time. Existing tracked modifications, deletions, and untracked files should be treated as current working state unless separately reviewed.

Notable status categories:

- Modified tracked files include pipeline, ASR, translation, TTS, lipsync, backend, API/router, README, requirements, and frontend-next files.
- Deleted tracked files under `frontend/` were already present in the working tree.
- Untracked working files include XTTS docs/plans, test media/reference files, model/setup scripts, `tools/`, `voice/`, `tests/`, and local ML folders.

## Safety Notes

- Do not delete or recreate `.venv_api`, `.venv_asr`, `.venv_tts`, or `.venv_bgm`.
- Do not delete or replace `models\xtts_v2`.
- Do not delete `outputs\french_official_test`.
- Do not upgrade core dependencies without explicit approval.
- Before editing any existing working source file, create a timestamped backup copy.
- Keep debug, practical, and strict fallback modes intact.
