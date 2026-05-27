# Job Lifecycle Cache And Cleanup Fix Report - 2026-05-06

## 1. Root cause

The stale-job failure was a lifecycle issue, not only an IndicTrans2 issue. The frontend kept unversioned localStorage job/result state, polling stopped only for `complete`/`error`, in-flight requests were not abortable, and old failed jobs could be resumed after long browser sessions. The backend also exposed terminal state indirectly through `stage`, and job API responses did not carry no-store headers.

## 2. What failed in the provided log

Job `04d211c5-81cc-4324-b2b8-eb18df0eac63` selected IndicTrans2 correctly, then the worker timed out after 180 seconds. The frontend repeatedly polled the same failed job. Later, manifest finalization hit Windows `Access Denied` while replacing `job_manifest.json`, leaving stale browser/backend state able to poison a new run.

## 3. Frontend stale-cache fix

Frontend job storage now uses versioned keys:

- `vidiolingua:v1:activeJob`
- `vidiolingua:v1:lastResult`
- `vidiolingua:v1:runSession`
- `vidiolingua:v1:terminalJob`

The old `videolingua.currentJob` and `videolingua.lastResult` keys are cleared and no longer treated as active state. Every upload creates a fresh `runSessionId` and stores safe run metadata.

## 4. Polling cleanup fix

The pipeline page now uses one scheduled polling loop per job/run token, aborts in-flight requests on unmount, avoids interval stacking, stops on terminal statuses, fetches `/api/result` once after terminal state, and records terminal job metadata.

## 5. no-store API header fix

Job status, result, upload response, and result file responses now send:

```text
Cache-Control: no-store, no-cache, must-revalidate, max-age=0
Pragma: no-cache
Expires: 0
```

Frontend job API calls also use `cache: "no-store"`, `Cache-Control: no-cache`, and a timestamp query param.

## 6. Worker timeout cleanup fix

IndicTrans2 timeout default is now `VIDIOLINGUA_INDICTRANS2_TIMEOUT_SEC=300`, with legacy `VIDIOLINGUA_INDICTRANS2_TIMEOUT_SECONDS` still honored. Timeout errors include stage, engine, timeout, command, request/response paths, process kill state, response JSON existence, stdout/stderr tails, and a suggested next action.

## 7. Manifest Windows file-lock fix

Manifest writes now use a per-manifest in-process lock, same-directory temp file, flush/fsync, `os.replace` retry backoff, and recovery copy fallback (`job_manifest.recovery.<timestamp>.json`) if Windows locks prevent replacing the primary manifest. Manifest failure remains best-effort and does not crash job finalization.

## 8. Start fresh run behavior

Upload, pipeline, and results flows now expose fresh-run cleanup actions. They clear active job state, last result state, terminal state, and run session state before navigating to `/upload`, so the user does not need a hard refresh.

## 9. Validation results

- Backend compile: passed.
- Lifecycle validation: passed, report at `outputs\validation\job_lifecycle_cleanup_report.json`.
- IndicTrans2 smoke: passed, `engine=indictrans2`, `used_indictrans2=true`, no Llama/deep-translator fallback.
- Translation router smoke: passed, `selected_engine=indictrans2`, `fallback_blocked=true`.
- Frontend lint: passed after rerunning with permission to read Corepack pnpm cache.
- Frontend build: passed.

## 10. Remaining limitations

- Jobs are still in-memory at the FastAPI process level; after backend restart, old browser state is cleared by missing-job recovery rather than resumed from durable backend storage.
- Cross-tab polling coordination is best-effort per page/run token. Separate browser tabs can still make independent requests, but terminal state no longer loops forever and stale state is cleared.
- IndicTrans2 timeout handling kills the worker process it launches; deeply orphaned child processes from third-party libraries are best-effort cleanup.
