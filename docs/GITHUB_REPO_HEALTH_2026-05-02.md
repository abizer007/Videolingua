# GitHub Repo Health - 2026-05-02

## Branch State

- Current branch: `backend-frontend-stable-v1`
- Clean publish HEAD before push retry: `cc0893ccfc560903c73f5fa0b42a1015123e00e6`
- Remote: `https://github.com/abizer007/Vidiolingua_Techgium.git`
- Push status: blocked by local Git/Windows credentials (`SEC_E_NO_CREDENTIALS`).

## What Was Recovered

- `docs/` had disappeared from the working folder and was restored from local commit `3dad9a2`.
- Other tracked source files were also missing from the working copy and were restored from the clean branch commit.
- The current branch now contains the recovered docs, backend, frontend, routing, validation, evaluation, and source utility files.

## Clean Publish Decisions

- Removed the tracked large demo media file from the publish branch:
  - `demo_inputs/WIN_20250426_17_20_22_Pro.mp4`
- Restored small source/support folders that teammates need:
  - `assets/`
  - `lipsync/run_lipsync.py`
  - `lipsync/run_uvr5.py`
  - `lipsync/run_uvr5_subprocess.py`
  - `shared/contracts.json`

## Excluded From Git

- `.env`, `.env.*`, `backend/.env`, `backend/.env.*`
- `models/`
- `outputs/`
- `jobs/`
- `.venv*/`, `.uv_python/`
- `node_modules/`, `.next/`
- `_snapshots/`, `_legacy/`
- generated audio/video files such as `.mp4`, `.wav`, `.mp3`
- local command logs and caches

## Validation Results

- Backend compile check: passed
- Pipeline config inspect: passed, with provider key masked by the tool
- Kannada voice router dry-run: passed, selected `sarvam`
- French voice router dry-run: passed, selected `xtts`
- Frontend lint/build: blocked by sandbox approval for Corepack AppData access

## Security Audit

- No real Sarvam key committed.
- No env files committed, only safe `.env.example` templates.
- No model weights committed.
- No generated outputs committed.
- No virtual environments committed.
- No `node_modules` or `.next` committed.
- No local IndicF5 load or full video pipeline was run during this rescue.

## Remaining Local Warnings

- Working tree still has untracked local notes and demo artifacts that are not part of the publish branch.
- Nested `ml/Wav2Lip` reports modified submodule content locally; it was not committed.
- Git push requires local credential repair or sign-in before the branch can be uploaded.
