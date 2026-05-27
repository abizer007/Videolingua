# Visual Lip-Sync / Wav2Lip Safe Fix Plan - 2026-05-06

Workspace: `D:\Vidiolingua`

This plan must exist before runtime code changes. The changes below are scoped
to source, docs, and validation artifacts only. They do not mutate virtual
environments, protected model folders, protected outputs, or secrets.

## 1. Current Failure Root Cause

The latest successful run did not apply real visual lip-sync. Wav2Lip was
attempted from `lipsync/run_lipsync.py`, but it used the API Python environment.
The API environment is intentionally lightweight and does not contain Wav2Lip
runtime dependencies such as `numpy`, `torch`, and `cv2`.

Observed failure:

```text
ModuleNotFoundError: No module named 'numpy'
```

After that failure, `lipsync/run_lipsync.py` fell back to ffmpeg audio
replacement and the job completed. The final metrics were honest at the raw
field level (`lipsync_method=ffmpeg`,
`lipsync_visual_sync_applied=false`), but the successful result could still be
misread as visually lip-synced.

## 2. Current Wav2Lip Detection And Fallback Behavior

Current behavior is too implicit:

- `backend/pipeline_runner.py` detects `ml/Wav2Lip` and its checkpoint.
- `backend/pipeline_runner.py` only sets `VIDIOLINGUA_WAV2LIP_PYTHON` when
  visual lip-sync is explicitly requested.
- `lipsync/run_lipsync.py` may attempt Wav2Lip merely because
  `VIDIOLINGUA_WAV2LIP_DIR` is set.
- If Wav2Lip fails and visual sync is not required, the code falls back to
  ffmpeg audio mux.

The bug is the combination of directory-driven auto-attempt and missing
preflight. Directory existence is not enough to prove Wav2Lip can run.

## 3. Current Env Selection Behavior

The current backend helper `_wav2lip_python()` defaults to `.venv_tts`, but it
is only used when visual lip-sync is explicitly requested. In ordinary runs,
the lipsync subprocess itself runs under `_lipsync_python()`, which resolves to
the API Python unless MuseTalk is configured.

Inside `lipsync/run_lipsync.py`, Wav2Lip chooses:

```text
VIDIOLINGUA_WAV2LIP_PYTHON
or PYTHON
or sys.executable
```

So if the backend does not set `VIDIOLINGUA_WAV2LIP_PYTHON`, Wav2Lip inherits
the API Python and fails.

## 4. Current ffmpeg Mux Behavior

The ffmpeg fallback path replaces the audio stream and uses `-shortest`. If the
generated audio is shorter than the source video, the final MP4 can be cut
shorter than the original video. Existing diagnostics report the difference,
but the mux behavior still allows truncation.

## 5. Current Duration / Timing Behavior

`tts/run_tts.py` generates one WAV per translated segment, applies ffmpeg
`atempo` to fit the source segment duration, and concatenates silence plus
segments. This preserves the broad segment timeline. It does not currently
perform a final exact pad/trim correction after `atempo`, so small encoder or
filter drift can accumulate.

ASR artifacts can contain `words: []`. In that case, the system has
segment-level timing only. It should report that honestly rather than implying
word, phoneme, or viseme-level alignment.

## 6. Exact Changes To Make

1. Add `tools/validate_wav2lip_runtime.py`.
   - Check Wav2Lip directory and checkpoint.
   - Resolve a safe Wav2Lip Python from:
     `VIDIOLINGUA_WAV2LIP_PYTHON`, `.venv_lipsync`, `.venv_tts`.
   - Do not default to `.venv_api`.
   - Probe imports in the selected Python via subprocess.
   - Write JSON preflight output to `outputs/validation`.
   - Do not run Wav2Lip generation.

2. Add backend Wav2Lip routing helper.
   - Use the preflight resolver before visual sync is attempted.
   - Set `VIDIOLINGUA_WAV2LIP_PYTHON` only to a Python that passes preflight.
   - Record selected Python and preflight status in metrics/analysis.

3. Add explicit lip-sync modes:
   - `ffmpeg_mux`: never attempts Wav2Lip.
   - `wav2lip_optional`: attempts Wav2Lip only after preflight; may fall back.
   - `wav2lip_required`: preflight and Wav2Lip failures fail the job.

4. Stop directory-existence auto-attempt.
   - Wav2Lip is attempted only for `wav2lip_optional` or
     `wav2lip_required`, with usable directory, checkpoint, and Python.

5. Preserve full video duration in ffmpeg mux.
   - Prepare a temporary audio track that is explicitly padded or trimmed to
     source video duration.
   - Mux without early video truncation.
   - Record source audio/video/prepared/final duration evidence.

6. Add sample-accurate post-stretch TTS correction.
   - Preserve existing `atempo`.
   - After each stretch, probe duration.
   - Pad or trim to target segment duration within a small tolerance.
   - Gate with `VIDIOLINGUA_EXACT_SEGMENT_TIMING`, defaulting to true.

7. Add alignment-level evidence.
   - Detect whether word timestamps are available.
   - Report `alignment_level=word` or `segment`.
   - Warn when only segment timestamps exist.

8. Add honest visual sync metrics/report fields.
   - Include method, requested/applied/fallback, Wav2Lip preflight status,
     selected Python, checkpoint status, alignment level, and LSE status.
   - Do not invent LSE-C/LSE-D.

9. Update existing frontend evidence panels only.
   - Show Wav2Lip vs ffmpeg mux.
   - Show when visual sync was requested but fell back.
   - Show segment/word alignment level and duration integrity.

## 7. Exact Files To Modify

Runtime/source:

- `tools/validate_wav2lip_runtime.py`
- `backend/pipeline_runner.py`
- `lipsync/run_lipsync.py`
- `tts/run_tts.py`
- `evaluation/report_builder.py`
- `backend/main.py`
- `NEW_Frontend/app/pipeline/page.tsx`
- `NEW_Frontend/app/results/page.tsx`
- `NEW_Frontend/lib/types.ts`

Documentation:

- `docs/VISUAL_LIPSYNC_WAV2LIP_SAFE_FIX_PLAN_2026-05-06.md`
- `docs/VISUAL_LIPSYNC_WAV2LIP_SAFE_FIX_REPORT_2026-05-06.md`
- `docs/PROJECT_PIPELINE.md`
- `docs/FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md`
- `docs/AUTOMATIC_BACKEND_EVALUATION_PROCESS_2026-05-05.md`
- `COMMAND_LOG.md`

Validation output:

- `outputs/validation/wav2lip_runtime_preflight.json`

## 8. Validation Plan

Run safe checks first:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend lipsync tts tools evaluation
.\.venv_api\Scripts\python.exe -m tools.validate_wav2lip_runtime --output outputs\validation\wav2lip_runtime_preflight.json
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\wav2lip_safe_router_fr.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\wav2lip_safe_router_kn.wav --dry-run
```

Then run a lightweight ffmpeg mux validation in a new validation folder only.

Frontend checks:

```powershell
cd D:\Vidiolingua\NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

Do not run a full pipeline loop in this pass. A single real Wav2Lip generation
test may be run only after explicit user approval.

## 9. Rollback Instructions

All changes are additive/source-level and can be reverted with normal git
operations.

Rollback options:

1. Revert only this feature:

```powershell
git diff -- docs/VISUAL_LIPSYNC_WAV2LIP_SAFE_FIX_PLAN_2026-05-06.md tools/validate_wav2lip_runtime.py backend/pipeline_runner.py lipsync/run_lipsync.py tts/run_tts.py evaluation/report_builder.py backend/main.py NEW_Frontend/app/pipeline/page.tsx NEW_Frontend/app/results/page.tsx NEW_Frontend/lib/types.ts docs/PROJECT_PIPELINE.md docs/FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md docs/AUTOMATIC_BACKEND_EVALUATION_PROCESS_2026-05-05.md COMMAND_LOG.md
```

Then restore or revert those paths.

2. Runtime behavior fallback:

Set:

```text
VIDIOLINGUA_LIPSYNC_MODE=ffmpeg_mux
```

This forces the existing audio-replacement path and prevents Wav2Lip attempts.

3. Segment timing fallback:

Set:

```text
VIDIOLINGUA_EXACT_SEGMENT_TIMING=false
```

This keeps the previous atempo-only behavior.

