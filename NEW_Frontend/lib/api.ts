import type { JobStatus, MultilingualExportResponse, ProcessingResult, UploadPayload } from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type MetricsInput = Partial<ProcessingResult["metrics"]> & Record<string, number | string | boolean | null | undefined>;

export function normalizeProcessingResult(result: ProcessingResult): ProcessingResult {
  const localizedVideos = Array.isArray(result.localizedVideos) ? result.localizedVideos : [];
  const metrics: MetricsInput = result.metrics && typeof result.metrics === "object" ? result.metrics : {};
  return {
    ...result,
    originalVideo: result.originalVideo ?? "",
    localizedVideos,
    metrics: {
      ...metrics,
      totalTime: typeof metrics.totalTime === "number" ? metrics.totalTime : 0,
      languagesProcessed: typeof metrics.languagesProcessed === "number" ? metrics.languagesProcessed : localizedVideos.length,
    },
  };
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    let message = raw;
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as { detail?: unknown; message?: unknown; error?: unknown };
        const detail = parsed.detail ?? parsed.message ?? parsed.error;
        if (Array.isArray(detail)) {
          message = detail.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join("; ");
        } else if (typeof detail === "string") {
          message = detail;
        } else if (detail) {
          message = JSON.stringify(detail);
        }
      } catch {
        message = raw;
      }
    }
    if (response.status === 202) {
      throw new Error(message || "The backend job is still running.");
    }
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function noStoreUrl(path: string) {
  const joiner = path.includes("?") ? "&" : "?";
  return `${API_BASE_URL}${path}${joiner}t=${Date.now()}`;
}

const NO_STORE_HEADERS = {
  "Cache-Control": "no-cache",
};

export async function uploadVideo(payload: UploadPayload): Promise<{ jobId: string }> {
  const formData = new FormData();
  const referenceMode = payload.referenceMode ?? (payload.voiceSample ? "uploaded" : payload.autoReference ? "auto_extract" : "none");
  formData.append("video", payload.video);
  formData.append("languages", JSON.stringify([payload.targetLanguage]));
  formData.append("targetLanguage", payload.targetLanguage);
  formData.append("includeCaptions", payload.includeCaptions ? "true" : "false");
  formData.append(
    "voiceOptions",
    JSON.stringify({
      cloned: payload.cloningRequired,
      mode: payload.cloningRequired ? "speaker-reference" : "managed",
      backendHint: payload.cloningRequired ? "xtts" : "sarvam",
      includeCaptions: !!payload.includeCaptions,
      captionsRequested: !!payload.includeCaptions,
      autoReference: referenceMode === "auto_extract",
      auto_reference: referenceMode === "auto_extract",
      referenceMode,
      reference_mode: referenceMode,
    }),
  );
  formData.append("autoReference", referenceMode === "auto_extract" ? "true" : "false");
  formData.append("referenceMode", referenceMode);
  formData.append("responsibleAIConsent", JSON.stringify(payload.responsibleAIConsent ?? {}));

  if (payload.sourceLanguage && payload.sourceLanguage !== "auto") {
    formData.append("sourceLanguage", payload.sourceLanguage);
  }

  if (payload.voiceSample) {
    formData.append("voiceSample", payload.voiceSample);
  }
  if (payload.groundTruthTranscriptFile) {
    formData.append("ground_truth_transcript_file", payload.groundTruthTranscriptFile);
  }
  if (payload.groundTruthTranscriptText?.trim()) {
    formData.append("ground_truth_transcript_text", payload.groundTruthTranscriptText.trim());
  }
  if (payload.referenceTranslationFile) {
    formData.append("reference_translation_file", payload.referenceTranslationFile);
  }
  if (payload.referenceTranslationText?.trim()) {
    formData.append("reference_translation_text", payload.referenceTranslationText.trim());
  }
  if (payload.humanMosRating?.trim()) {
    formData.append("human_mos_rating", payload.humanMosRating.trim());
  }
  if (payload.humanQualityNotes?.trim()) {
    formData.append("human_quality_notes", payload.humanQualityNotes.trim());
  }

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    cache: "no-store",
    headers: NO_STORE_HEADERS,
    body: formData,
  });

  return parseJson<{ jobId: string }>(response);
}

export async function getJobStatus(jobId: string, options?: { signal?: AbortSignal }): Promise<JobStatus> {
  const response = await fetch(noStoreUrl(`/api/job-status/${encodeURIComponent(jobId)}`), {
    cache: "no-store",
    headers: NO_STORE_HEADERS,
    signal: options?.signal,
  });
  return parseJson<JobStatus>(response);
}

export async function getResult(jobId: string, options?: { signal?: AbortSignal }): Promise<ProcessingResult> {
  const response = await fetch(noStoreUrl(`/api/result/${encodeURIComponent(jobId)}`), {
    cache: "no-store",
    headers: NO_STORE_HEADERS,
    signal: options?.signal,
  });
  return normalizeProcessingResult(await parseJson<ProcessingResult>(response));
}

export async function createMultilingualExport(payload: {
  sourceVideo: string;
  exportId?: string;
  tracks: Array<{ language: string; audioPath: string }>;
  createHls?: boolean;
  createMp4?: boolean;
}): Promise<MultilingualExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/multilingual-export`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...NO_STORE_HEADERS },
    body: JSON.stringify({
      createHls: true,
      createMp4: true,
      ...payload,
    }),
  });
  return parseJson<MultilingualExportResponse>(response);
}

export async function getMultilingualExport(exportId: string): Promise<MultilingualExportResponse> {
  const response = await fetch(noStoreUrl(`/api/multilingual-export/${encodeURIComponent(exportId)}`), {
    cache: "no-store",
    headers: NO_STORE_HEADERS,
  });
  return parseJson<MultilingualExportResponse>(response);
}

export async function healthCheck(): Promise<{ status: string }> {
  try {
    const response = await fetch(noStoreUrl("/api/health"), { cache: "no-store", headers: NO_STORE_HEADERS });
    return parseJson<{ status: string }>(response);
  } catch {
    return { status: "unavailable" };
  }
}

export async function healthDeps(): Promise<Record<string, unknown>> {
  const response = await fetch(noStoreUrl("/api/health/deps"), { cache: "no-store", headers: NO_STORE_HEADERS });
  return parseJson<Record<string, unknown>>(response);
}

export async function ttsHealth(): Promise<Record<string, unknown>> {
  const response = await fetch(noStoreUrl("/api/tts-health"), { cache: "no-store", headers: NO_STORE_HEADERS });
  return parseJson<Record<string, unknown>>(response);
}
