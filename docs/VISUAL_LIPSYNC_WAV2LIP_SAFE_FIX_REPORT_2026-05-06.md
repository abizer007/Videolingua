# Visual Lip-sync / Wav2Lip Safe Fix Report - 2026-05-06

## Root Cause

The previous successful-looking run did not apply real visual lip-sync. Wav2Lip was attempted from the API virtual environment, which is intentionally lightweight and does not provide the required media/ML modules. The failure was then hidden by the legacy audio-only ffmpeg mux fallback.

The result was operationally misleading:

- `lipsync_method=ffmpeg`
- `lipsync_visual_sync_applied=false`
- final MP4 existed
- no mouth animation model had been applied

## Why `.venv_api` Is Wrong For Wav2Lip

`.venv_api` is the lightweight FastAPI/runtime orchestration environment. Wav2Lip needs heavier runtime modules such as `numpy`, `torch`, `cv2`, and `scipy`. The new preflight never selects `.venv_api` by default for Wav2Lip.

## Selected Python Environment

Validation selected:

```text
D:\Vidiolingua\.venv_tts\Scripts\python.exe
```

The environment was read-only during validation. No dependencies were installed and no venv files were mutated.

## Wav2Lip Preflight Result

Command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_wav2lip_runtime --output outputs\validation\wav2lip_runtime_preflight.json
```

Result:

- `ok=true`
- `selected_python=D:\Vidiolingua\.venv_tts\Scripts\python.exe`
- `checkpoint_exists=true`
- `numpy_available=true`
- `torch_available=true`
- `torch_version=2.5.1+cpu`
- `cuda_available=false`
- `cv2_available=true`
- `scipy_available=true`

The first probe timed out at 30 seconds while importing the heavier `.venv_tts` stack. The preflight timeout was raised to 120 seconds; the same command then passed.

## New Lip-sync Modes

`VIDIOLINGUA_LIPSYNC_MODE` now supports:

- `ffmpeg_mux`: never attempts Wav2Lip; audio replacement only.
- `wav2lip_optional`: attempts Wav2Lip only after preflight; falls back to ffmpeg with explicit fallback/error metrics if Wav2Lip fails.
- `wav2lip_required`: fails clearly on preflight or generation failure; no ffmpeg fallback is allowed.

Directory existence alone no longer triggers Wav2Lip.

## Duration Preservation

The ffmpeg mux path now prepares generated audio before mux:

- if generated audio is shorter than source video, silence is padded to source duration
- if generated audio is longer, audio is trimmed to source duration
- `lipsync/run_lipsync.py` no longer uses `-shortest`
- optional BGM remix also prepares mixed audio before final mux

Recorded fields include source video duration, generated audio duration, prepared audio duration, final MP4 duration, delta, padded seconds, and trimmed seconds.

Lightweight validation used synthetic 3.0s video with 1.0s audio:

- mode `ffmpeg_mux`
- generated audio `1.0s`
- prepared audio `3.0s`
- padded `2.0s`
- final MP4 `3.0s`
- duration delta `0.0s`

## Per-segment Timing

`tts/run_tts.py` still uses existing per-segment `atempo`. A conservative final correction now probes each stretched segment and pads/trims it to the target segment slot when `VIDIOLINGUA_EXACT_SEGMENT_TIMING` is not disabled.

The timing report is written next to the generated WAV:

```text
<tts_output>.timing_report.json
```

It records target duration, raw duration, atempo ratio, post-atempo duration, final duration, padding, trimming, and aggressive-ratio warnings.

## Alignment Honesty

The pipeline now checks whether ASR evidence has word-level timestamps. If timed words are missing, it reports:

```text
alignment_level=segment
```

and warns that visual mouth alignment may be approximate. This pass does not claim phoneme/viseme alignment.

## Metrics Added

New/expanded lipsync evidence includes:

- method
- visual sync requested/applied
- fallback used
- Wav2Lip preflight status
- selected Wav2Lip Python
- checkpoint status
- alignment level
- LSE-C/LSE-D status
- duration integrity fields
- Wav2Lip warnings/errors

LSE-C/LSE-D are marked `not_installed` or `unavailable`; no score is invented.

## Frontend Display

The existing pipeline/results evidence panels now show:

- Wav2Lip visual sync vs ffmpeg audio mux
- whether visual sync was actually applied
- whether Wav2Lip was requested and failed
- whether fallback was used
- selected Wav2Lip Python
- checkpoint/preflight status
- alignment level
- duration integrity values
- ffmpeg-only message: `Audio replacement only - no mouth animation model applied.`

## Validation Results

Commands run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend lipsync tts tools evaluation
.\.venv_api\Scripts\python.exe -m tools.validate_wav2lip_runtime --output outputs\validation\wav2lip_runtime_preflight.json
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference outputs\validation\test_speaker_ref.wav --cloning-required true --output outputs\validation\wav2lip_safe_router_fr.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference outputs\validation\test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\wav2lip_safe_router_kn.wav --dry-run
corepack pnpm run lint
corepack pnpm run build
```

Results:

- Backend/tools/evaluation compile passed.
- Wav2Lip preflight passed.
- French router dry-run selected `xtts`.
- Kannada router dry-run selected `sarvam`.
- IndicF5 was not selected.
- Generic fallback was not selected.
- Frontend lint passed.
- Frontend build passed.
- Lightweight ffmpeg mux validation passed.

## Real Wav2Lip Run

No real Wav2Lip generation run was performed in this pass. The next step requires explicit user approval for one run into a new output folder with:

```text
VIDIOLINGUA_LIPSYNC_MODE=wav2lip_required
```

## Remaining Limitations

- Wav2Lip preflight proves runtime readiness, not visual quality.
- Current selected torch is CPU-only (`cuda_available=false`), so real Wav2Lip may be slow.
- ASR alignment is segment-level unless word timestamps are present.
- LSE-C/LSE-D are still not computed because the evaluator is not wired for this lightweight validation path.

## Rollback

All changes are additive and can be reverted by removing:

- `tools/validate_wav2lip_runtime.py`
- `docs/VISUAL_LIPSYNC_WAV2LIP_SAFE_FIX_PLAN_2026-05-06.md`
- `docs/VISUAL_LIPSYNC_WAV2LIP_SAFE_FIX_REPORT_2026-05-06.md`

and reverting the touched runtime/frontend/docs files in git.
