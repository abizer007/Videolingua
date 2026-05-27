# Job Lifecycle Cache And Cleanup Fix Plan - 2026-05-06

## 1. Current frontend job-state flow

- `NEW_Frontend/app/upload/page.tsx` posts `/api/upload`, receives a backend-generated `jobId`, stores job metadata with `saveStoredJob`, then navigates to `/pipeline?jobId=<jobId>`.
- `NEW_Frontend/app/pipeline/page.tsx` chooses `jobId` from the query parameter first, then `readStoredJob()`. It polls `/api/job-status/{jobId}` every 1500 ms and fetches `/api/result/{jobId}` when `stage` is `complete` or `error`.
- `NEW_Frontend/app/results/page.tsx` chooses `jobId` from the query parameter first, then stored job metadata. It displays cached result metadata if the cached result matches the active job, then fetches `/api/result/{jobId}`.

## 2. Current localStorage/sessionStorage usage

- `NEW_Frontend/lib/pipeline-storage.ts` uses unversioned localStorage keys:
  - `videolingua.currentJob`
  - `videolingua.lastResult`
- There is no current `sessionStorage` run identity, no terminal job record, and no automatic migration/clearing of stale unversioned keys.

## 3. Current polling stop conditions

- Polling stops only when the pipeline page observes `stage === "complete"` or `stage === "error"`.
- The in-flight fetch is not abortable on unmount.
- The result fetch can run after terminal status, but failed jobs can remain in localStorage and be resumed by a future page load.
- There is no shared polling token, so multiple page instances or long-lived tabs can stack intervals.

## 4. Current backend job terminal-state behavior

- `backend/job_store.py` stores jobs in memory only and treats `stage: "error"` and `stage: "complete"` as terminal-like states.
- There is no explicit `status` field with `queued`, `running`, `complete`, `failed`, `cancelled`, or `timeout`.
- Jobs have `startedAt` and `updatedAt`, but no durable `createdAt`, `terminalAt`, `completedAt`, `failedAt`, `errorSummary`, `resultPath`, or `terminal` boolean in the status payload.
- `backend/pipeline_runner.py` catches pipeline exceptions, writes manifest failure metadata, sets `stage="error"`, and then attaches a result payload. This prevents a permanently running job in the common exception path, but terminal state is not explicit or protected against later mutation.

## 5. Current worker temp directory behavior

- `translation/engines/indictrans2_engine.py` runs the IndicTrans2 worker in `outputs/validation/indictrans2_worker_tmp` via `tempfile.TemporaryDirectory`.
- The timeout default is `VIDIOLINGUA_INDICTRANS2_TIMEOUT_SECONDS`, defaulting to 180 seconds.
- `subprocess.run(..., timeout=timeout_s)` kills the immediate process on timeout, but the error message lacks command/request/response/debug cleanup detail.
- Production jobs do not use a per-job worker temp directory.

## 6. Current manifest write behavior

- `backend/job_manifest.py` writes `job_manifest.json` through a same-directory temp file and `os.replace`.
- Save failures are logged and return `False`; they do not intentionally crash the pipeline.
- There is no retry/backoff for Windows `PermissionError` / WinError 5.
- There is no recovery copy such as `job_manifest.recovery.<timestamp>.json`.
- There is no per-job in-process manifest lock, so concurrent manifest writes can race.

## 7. Root causes of stale job/cache failures

- Old unversioned frontend cache keys can keep an obsolete job/result active after a backend restart or a failed run.
- Failed jobs are not recorded as terminal frontend state, so page reloads can resume polling a dead job.
- Polling intervals and in-flight requests are page-local and not guarded by a run token.
- Backend responses do not send no-store headers, so browser/proxy cache behavior is not fully constrained.
- Backend job status lacks a clear terminal contract for `failed`, `timeout`, and `cancelled`.
- IndicTrans2 worker timeout errors are too generic and temp files are not job-scoped for production debugging.
- Manifest writes can lose the primary replace step on Windows when another process briefly locks the file.

## 8. Exact fixes to implement

- Add versioned frontend storage keys:
  - `vidiolingua:v1:activeJob`
  - `vidiolingua:v1:lastResult`
  - `vidiolingua:v1:runSession`
  - `vidiolingua:v1:terminalJob`
- Clear old unversioned keys and stale active/result/terminal state before every new upload. Generate a fresh `runSessionId` for each upload attempt and store it with safe metadata.
- Add frontend helpers for terminal status detection, stale TTL checks, start-fresh clearing, and one active polling token per job/run session.
- Update `getJobStatus`, `getResult`, and related API calls to use `cache: "no-store"`, `Cache-Control: no-cache`, and timestamp query params.
- Update pipeline/results pages so terminal states `complete`, `failed`, `cancelled`, `error`, and `timeout` stop polling permanently, abort in-flight fetches on unmount, fetch result once, mark terminal job state, and show `Start fresh run` / `Clear old job state`.
- Add no-store headers to job status/result/file/artifact endpoints.
- Extend `job_store` with explicit `status`, `terminal`, timestamps, error summary, result path, and helpers for terminal finalization that do not mutate finished jobs except safe result/metadata finalization.
- Update pipeline failure handling to mark failed/timeout exactly once, write result payload, write manifest best-effort, and keep terminal status durable.
- Improve `IndicTrans2Engine` timeout handling with `VIDIOLINGUA_INDICTRANS2_TIMEOUT_SEC` defaulting to 300, explicit process terminate/kill cleanup, stdout/stderr tail, request/response path details, and job-scoped temp dirs when `VIDIOLINGUA_JOB_ID` is available.
- Add `VIDIOLINGUA_KEEP_WORKER_TMP_ON_FAILURE=false` behavior: clean temp files on success; on failure either keep for debugging or copy useful debug files to a job error directory before cleanup.
- Harden `job_manifest.save_manifest` with per-manifest locks, retry/backoff on replace PermissionError, recovery JSON fallback, and warning logging.
- Add `tools/validate_job_lifecycle_cleanup.py` to validate job status terminal behavior, no-store helpers, manifest recovery behavior, and stale metadata without running the video pipeline.
- Add `tools/cleanup_stale_job_state.py` as dry-run-by-default cleanup for worker tmp and validation temp dirs, excluding protected outputs.

## 9. Validation plan

- Compile backend and tooling:
  - `.\.venv_api\Scripts\python.exe -m compileall backend translation workers tools`
- Run lifecycle validation:
  - `.\.venv_api\Scripts\python.exe -m tools.validate_job_lifecycle_cleanup --output outputs\validation\job_lifecycle_cleanup_report.json`
- Run IndicTrans2 smoke test:
  - `.\.venv_api\Scripts\python.exe -m tools.validate_indictrans2_translation --source-language en --target-language kn --text "This is a test of the translation system." --output outputs\validation\indictrans2_after_lifecycle_fix.json`
- Run translation router smoke test:
  - `.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test of the translation system." --output outputs\validation\router_translation_after_lifecycle_fix.json`
- Run frontend checks:
  - `cd D:\Vidiolingua\NEW_Frontend`
  - `corepack pnpm run lint`
  - `corepack pnpm run build`
- Do not run the full video pipeline, local IndicF5, dependency installation, or virtual environment mutation.
