# RTX 4050 Local Setup

The project should stay manageable on an i5 laptop with RTX 4050 by keeping major models isolated.

## Environment Layout

```text
.venv_api          API/orchestration
.venv_asr          WhisperX/faster-whisper
.venv_tts          known-good CPU XTTS, do not mutate
.venv_bgm          Demucs/BGM
.venv_indicf5      future IndicF5 worker
.venv_indictrans2  future IndicTrans2 worker
.venv_tts_gpu      optional future CUDA XTTS experiment
```

## Rules

- Load only one major model at a time.
- Do not load XTTS and IndicF5 together.
- Do not load IndicTrans2 while TTS or lip-sync is running.
- Prefer subprocess workers.
- Use batch size 1 by default.
- Avoid `torch.compile` initially.
- Keep intermediate files as WAV.
- Do not mutate `.venv_tts` for CUDA experiments.

## CUDA Check

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

## OOM Troubleshooting

- Lower batch size to 1.
- Use CPU for one stage if explicitly allowed.
- Close worker processes between stages.
- Prefer smaller model variants.
- Avoid running ASR, translation, TTS, and lip-sync at the same time.

