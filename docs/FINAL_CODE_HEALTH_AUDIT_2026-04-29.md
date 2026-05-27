# Final Code Health Audit - 2026-04-29

## Compile

Command:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
```

Result:

```text
passed
```

## XTTS Health

BeamSearchScorer import:

```text
BeamSearchScorer import OK
```

Torch:

```text
torch: 2.5.1+cpu
cuda: False
cuda version: None
gpu: none
```

XTTS model files:

```text
models\xtts_v2\config.json          4,368 bytes
models\xtts_v2\model.pth            1,867,929,118 bytes
models\xtts_v2\vocab.json           361,219 bytes
models\xtts_v2\speakers_xtts.pth    7,754,818 bytes
```

## IndicTrans2 Health

Lightweight import check:

```text
indictrans2 env ok: 2.5.1+cu121 True
```

## IndicF5

No IndicF5 model load or generation was run. Current status remains
disabled/local_disabled.

## Result

Backend Python code compiles, XTTS known-good runtime remains healthy, and
IndicTrans2 runtime imports successfully.
