# VidioLingua Repair Status - 2026-04-28

## Active Runtime Architecture

The pipeline now uses isolated Python runtimes for each stack:

| Stage | Environment | Python |
| --- | --- | --- |
| API/backend | `.venv_api` | `VIDIOLINGUA_API_PYTHON` |
| ASR/diarization | `.venv_asr` | `VIDIOLINGUA_ASR_PYTHON` |
| TTS/translation | `.venv_tts` | `VIDIOLINGUA_TTS_PYTHON` |
| BGM/Demucs | `.venv_bgm` | `VIDIOLINGUA_BGM_PYTHON` |
| MuseTalk | `.venv_musetalk` | `VIDIOLINGUA_MUSETALK_PYTHON` |
| GFPGAN | `.venv_gfpgan` | `VIDIOLINGUA_GFP_GAN_PYTHON` |

The active frontend is `frontend-next`. The old Vite frontend was quarantined
under `_legacy/frontend_legacy_20260428`.

## Modes

`practical` is the local default. It requires XTTS cloned voice but treats
MuseTalk, GFPGAN, PyAnnote diarization, and Demucs as optional/fallback stages.

`strict` requires XTTS cloned voice and Demucs/BGM separation.

`debug` explicitly disables cloned voice and uses legacy/generic TTS plus ffmpeg
mux fallback. This mode is only for pipeline plumbing validation.

## XTTS v2 Model

The local XTTS v2 directory is expected at:

```text
models/xtts_v2
```

It must contain:

```text
config.json
model.pth
vocab.json or tokenizer.json
```

Download helper:

```powershell
.\scripts\download_xtts_v2_model.ps1 -AgreeToCoquiTerms
```

Only run that command after accepting the Coqui XTTS v2 CPML/commercial terms.

## Validation Commands

Environment preflight:

```powershell
.\.venv_api\Scripts\python.exe -m tools.preflight_environment --all
```

Video/XTTS preflight:

```powershell
.\.venv_tts\Scripts\python.exe -m tools.preflight_video_translation_pipeline --video Vidiolingua_Test_Official.mp4 --target-language fr --reference test_speaker_ref.wav --output outputs\preflight_french.wav --model-path models\xtts_v2
```

Full practical run:

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language fr --reference test_speaker_ref.wav --model-path models\xtts_v2 --mode practical --output-dir outputs\french_official_test
```

