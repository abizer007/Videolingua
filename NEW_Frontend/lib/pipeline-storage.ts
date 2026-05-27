import type { JobStatus, ProcessingResult, StoredJob } from "@/lib/types";
import { normalizeProcessingResult } from "@/lib/api";

export const JOB_STORAGE_VERSION = 1;
export const ACTIVE_JOB_KEY = "vidiolingua:v1:activeJob";
export const RESULT_KEY = "vidiolingua:v1:lastResult";
export const RUN_SESSION_KEY = "vidiolingua:v1:runSession";
export const TERMINAL_JOB_KEY = "vidiolingua:v1:terminalJob";

const LEGACY_KEYS = ["videolingua.currentJob", "videolingua.lastResult"];
const ACTIVE_JOB_TTL_MS = 24 * 60 * 60 * 1000;
const TERMINAL_STATUSES = new Set(["complete", "failed", "cancelled", "error", "timeout"]);

type RunSession = {
  runSessionId: string;
  createdAt: string;
};

type TerminalJob = {
  jobId: string;
  runSessionId?: string;
  status: string;
  stage?: string | null;
  terminal: true;
  terminalAt: string;
  errorSummary?: string | null;
};

function canUseStorage() {
  return typeof window !== "undefined";
}

function readJson<T>(key: string): T | null {
  if (!canUseStorage()) return null;
  const raw = window.localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function writeJson(key: string, value: unknown) {
  if (!canUseStorage()) return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

function removeKey(key: string) {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(key);
}

export function clearLegacyJobStorage() {
  if (!canUseStorage()) return;
  for (const key of LEGACY_KEYS) {
    window.localStorage.removeItem(key);
  }
}

export function createRunSession(): RunSession {
  const runSession = {
    runSessionId: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    createdAt: new Date().toISOString(),
  };
  writeJson(RUN_SESSION_KEY, runSession);
  return runSession;
}

export function readRunSession(): RunSession | null {
  return readJson<RunSession>(RUN_SESSION_KEY);
}

export function clearRunState(options: { keepLanguage?: boolean } = {}) {
  clearLegacyJobStorage();
  const previousJob = options.keepLanguage ? readStoredJob() : null;
  removeKey(ACTIVE_JOB_KEY);
  removeKey(RESULT_KEY);
  removeKey(TERMINAL_JOB_KEY);
  removeKey(RUN_SESSION_KEY);
  if (options.keepLanguage && previousJob?.targetLanguage) {
    const runSession = createRunSession();
    writeJson(ACTIVE_JOB_KEY, {
      storageVersion: JOB_STORAGE_VERSION,
      runSessionId: runSession.runSessionId,
      createdAt: runSession.createdAt,
      targetLanguage: previousJob.targetLanguage,
      status: "draft",
      terminal: false,
    });
  }
}

export function prepareFreshRunSession() {
  clearRunState();
  return createRunSession();
}

export function saveStoredJob(job: StoredJob) {
  clearLegacyJobStorage();
  writeJson(ACTIVE_JOB_KEY, {
    ...job,
    storageVersion: JOB_STORAGE_VERSION,
    status: job.status ?? "queued",
    terminal: Boolean(job.terminal),
  });
}

export function updateStoredJobFromStatus(status: JobStatus) {
  const current = readStoredJob();
  if (!current || current.jobId !== status.jobId) return;
  saveStoredJob({
    ...current,
    status: status.status ?? status.stage,
    terminal: isTerminalStatus(status),
    updatedAt: status.updatedAt ?? new Date().toISOString(),
  });
}

export function readStoredJob(): StoredJob | null {
  clearLegacyJobStorage();
  const job = readJson<StoredJob>(ACTIVE_JOB_KEY);
  if (!job?.jobId) return null;
  if (job.terminal) return null;
  if (job.createdAt && Date.now() - Date.parse(job.createdAt) > ACTIVE_JOB_TTL_MS) {
    removeKey(ACTIVE_JOB_KEY);
    return null;
  }
  return job;
}

export function readAnyStoredJob(): StoredJob | null {
  clearLegacyJobStorage();
  return readJson<StoredJob>(ACTIVE_JOB_KEY);
}

export function saveResult(result: ProcessingResult) {
  const normalized = normalizeProcessingResult(result);
  writeJson(RESULT_KEY, {
    ...normalized,
    cachedAt: new Date().toISOString(),
  });
}

export function readResult(): ProcessingResult | null {
  const result = readJson<ProcessingResult>(RESULT_KEY);
  return result ? normalizeProcessingResult(result) : null;
}

export function markTerminalJob(status: {
  jobId: string;
  status?: string;
  stage?: string | null;
  terminalAt?: string | null;
  errorSummary?: string | null;
  error?: string | null;
  runSessionId?: string;
}) {
  const terminal: TerminalJob = {
    jobId: status.jobId,
    runSessionId: status.runSessionId,
    status: status.status ?? status.stage ?? "unknown",
    stage: status.stage,
    terminal: true,
    terminalAt: status.terminalAt ?? new Date().toISOString(),
    errorSummary: status.errorSummary ?? status.error ?? null,
  };
  writeJson(TERMINAL_JOB_KEY, terminal);
  const current = readAnyStoredJob();
  if (current?.jobId === status.jobId) {
    saveStoredJob({
      ...current,
      status: terminal.status,
      terminal: true,
      updatedAt: terminal.terminalAt,
    });
    removeKey(ACTIVE_JOB_KEY);
  }
}

export function readTerminalJob(): TerminalJob | null {
  return readJson<TerminalJob>(TERMINAL_JOB_KEY);
}

export function clearActiveJob() {
  removeKey(ACTIVE_JOB_KEY);
}

export function isTerminalStatus(status?: Pick<JobStatus, "status" | "stage" | "terminal"> | null) {
  if (!status) return false;
  return Boolean(status.terminal) || TERMINAL_STATUSES.has(String(status.status ?? status.stage).toLowerCase()) || TERMINAL_STATUSES.has(String(status.stage).toLowerCase());
}

export function isStoredJobStale(job: StoredJob | null) {
  if (!job?.createdAt) return true;
  return Date.now() - Date.parse(job.createdAt) > ACTIVE_JOB_TTL_MS;
}
