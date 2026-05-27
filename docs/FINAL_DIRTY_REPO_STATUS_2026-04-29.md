# Final Dirty Repo Status - 2026-04-29

## Commands

```powershell
git status --short
git diff --stat
```

No commit, reset, clean, checkout, or stash was run.

## SHOULD_KEEP

- `backend\pipeline_runner.py`
- `translation\run_translate.py`
- `tts\run_tts.py`
- `voice\**`
- `translation\base.py`, `translation\router.py`, `translation\engines\**`
- `tools\**`
- `workers\indictrans2_worker.py`
- `app\services\xtts_tts_service.py`
- `app\services\indicf5_tts_service.py`
- `requirements-*.txt`
- `docs\*.md` audit/setup/report files
- `COMMAND_LOG.md`

## REVIEW_BEFORE_COMMIT

- `.gitignore`
- `README.md`
- `app\routers\tts_router.py`
- `backend\main.py`
- `backend\job_store.py`
- `asr\run_asr.py`
- `lipsync\run_lipsync.py`
- `requirements.txt`
- `frontend-next\README.md`
- `frontend-next\src\app\architecture\page.tsx`

## GENERATED_OUTPUTS

- `outputs\**` are ignored/generated.
- `asr\output\input_video_transcription.json`
- `translation\input\input_video_transcription.json`
- `jobs\**`
- `_snapshots\**`
- `.pip_cache\**`

## SECRET_DO_NOT_COMMIT

- `backend\.env`
- root `.env` if created
- any future local env file with API keys/tokens

Current check: `backend\.env` and `.env` are ignored and untracked.

## SAFE_TO_IGNORE

- protected output folders for local validation:
  - `outputs\french_official_test`
  - `outputs\kannada_sarvam_practical_test_clipfix`
- local media inputs:
  - `Vidiolingua_Test_Official.mp4`
  - `test_speaker_ref.wav`

## UNKNOWN_REVIEW_REQUIRED

- Deleted legacy `frontend\**` Vite app files shown in git status.
- `ml\Wav2Lip` submodule/worktree marker.
- `.claude\**`
- broad pre-existing frontend edits outside the backend audit scope.

## Diff Stat Summary

The tracked diff is large and includes backend, pipeline, TTS, translation,
lipsync, requirements, docs/readmes, frontend-next docs/page edits, and deletion
of the old `frontend` app. Review before committing; do not stage everything
blindly.
