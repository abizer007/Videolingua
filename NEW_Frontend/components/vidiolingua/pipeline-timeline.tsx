import { CheckCircle2, CircleDashed, Loader2, Timer, XCircle } from "lucide-react";
import type { JobStatus, PipelineStage, StoredJob } from "@/lib/types";

const stages: Array<{
  key: PipelineStage;
  title: string;
  summary: string;
}> = [
  { key: "uploading", title: "Receive upload", summary: "Backend job workspace and source file" },
  { key: "bgm_separation", title: "Prepare audio", summary: "Optional BGM separation when enabled" },
  { key: "asr", title: "Transcribe speech", summary: "ASR transcript and speaker evidence" },
  { key: "translation", title: "Route translation", summary: "Target-language translation files" },
  { key: "tts", title: "Generate voice", summary: "XTTS or Sarvam output audio" },
  { key: "lipsync", title: "Mux media", summary: "Final video assembly and file validation" },
  { key: "complete", title: "Serve result", summary: "Result metadata and downloadable MP4" },
];

const order = stages.map((stage) => stage.key);

const manifestStageByPipelineStage: Partial<Record<PipelineStage, string>> = {
  uploading: "receive_upload",
  bgm_separation: "prepare_audio",
  asr: "asr",
  translation: "translation",
  tts: "voice_generation",
  lipsync: "lipsync_mux",
  complete: "complete",
};

function stateFor(stage: PipelineStage, key: PipelineStage, history: JobStatus["stageHistory"], status: JobStatus | null) {
  const manifestStage = manifestStageByPipelineStage[key];
  const manifestState = manifestStage ? status?.manifestSummary?.stage_statuses?.[manifestStage]?.status : null;
  if (manifestState === "completed") return "done";
  if (manifestState === "running") return "active";
  if (manifestState === "failed") return "error";
  if (manifestState === "skipped") return "not-run";
  if (stage === "error") return "error";
  if (stage === "complete" && key === "complete") return "active";
  const activeIndex = order.indexOf(stage);
  const itemIndex = order.indexOf(key);
  const event = history?.find((historyItem) => historyItem.stage === key);
  if (itemIndex < activeIndex) return event ? "done" : "not-run";
  if (itemIndex === activeIndex) return "active";
  return "pending";
}

function formatSeconds(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "Waiting";
  if (value < 60) return `${value.toFixed(1)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}

function formatValue(value: unknown) {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined || value === "") return "Not reported yet";
  return String(value);
}

function formatReferenceMode(value: unknown) {
  if (value === "auto_extract") return "auto-extract";
  if (value === "none") return "none";
  if (typeof value === "string") return value.replaceAll("_", " ");
  return formatValue(value);
}

function metric(metrics: JobStatus["metrics"], key: string) {
  return metrics?.[key];
}

function metricWithUnit(metrics: JobStatus["metrics"], key: string, unit: string) {
  const value = metric(metrics, key);
  if (typeof value !== "number") return formatValue(value);
  return `${formatValue(value)}${unit}`;
}

function detailsFor(stage: PipelineStage, status: JobStatus | null, storedJob: StoredJob | null) {
  const metrics = status?.metrics ?? {};
  const languages = status?.languages?.join(", ") || storedJob?.targetLanguage || "Waiting";
  const manifestStage = manifestStageByPipelineStage[stage];
  const manifestStatus = manifestStage ? status?.manifestSummary?.stage_statuses?.[manifestStage] : null;
  const manifestDetails = manifestStatus
    ? [
        `Manifest stage: ${manifestStage}`,
        `Attempts: ${formatValue(manifestStatus.attempt_count)}`,
        `Checkpoint: ${manifestStatus.can_resume_from_here ? "ready metadata" : "not ready"}`,
      ]
    : [];

  if (stage === "uploading") {
    return [
      `Source file: ${storedJob?.videoName ?? "Waiting for backend upload"}`,
      `Reference mode: ${formatReferenceMode(storedJob?.referenceMode)}`,
      ...manifestDetails,
    ];
  }
  if (stage === "bgm_separation") {
    return [`BGM preserved: ${formatValue(metric(metrics, "bgmPreserved"))}`, ...manifestDetails];
  }
  if (stage === "asr") {
    const speakerStatus = status?.analysis?.speaker_analysis?.status?.replaceAll("_", " ") ?? formatValue(metric(metrics, "speaker_analysis_status"));
    const speakerCount = status?.analysis?.speaker_analysis?.speakers_detected;
    return [
      `Segments: ${formatValue(metric(metrics, "asr_segments"))}`,
      speakerCount == null ? `Speaker analysis: ${speakerStatus}` : `Speakers detected: ${speakerCount}`,
      `ASR files: ${formatValue(metric(metrics, "asr_output_files"))}`,
      `Source language: ${status?.sourceLanguage ?? "Detecting"}`,
      `Language detection confidence: ${formatValue(status?.sourceLanguageConfidence)}`,
      ...manifestDetails,
    ];
  }
  if (stage === "translation") {
    const qa = status?.translationQA ?? status?.analysis?.translationQA ?? null;
    return [
      `Router: ${status?.manifestSummary?.selected_backends?.translation ?? storedJob?.translationBackend ?? "Backend router"}`,
      `Translation files: ${formatValue(metric(metrics, "translation_files"))}`,
      `Translation QA: ${formatValue(qa?.status ?? metric(metrics, "translation_qa_status"))}`,
      `Script check: ${formatValue(qa?.scriptMatch ?? metric(metrics, "translation_qa_script_match"))}`,
      `Numbers/entities: ${formatValue(qa?.numberIssues ?? metric(metrics, "translation_qa_number_issues"))} / ${formatValue(qa?.entityIssues ?? metric(metrics, "translation_qa_entity_issues"))}`,
      `Target count: ${formatValue(metric(metrics, "target_language_count"))}`,
      `Target: ${languages}`,
      ...manifestDetails,
    ];
  }
  if (stage === "tts") {
    return [
      `Voice route: ${status?.manifestSummary?.selected_backends?.voice ?? storedJob?.voiceLabel ?? "Backend-selected voice route"}`,
      `Reference mode: ${formatReferenceMode(status?.analysis?.reference_audio?.mode ?? storedJob?.referenceMode)}`,
      `XTTS selected: ${formatValue(metric(metrics, "xtts_selected"))}`,
      `Sarvam selected: ${formatValue(metric(metrics, "sarvam_selected"))}`,
      `Generated audio files: ${formatValue(metric(metrics, "tts_files"))}`,
      `Generated audio duration: ${metricWithUnit(metrics, "tts_total_duration_s", "s")}`,
      `Source video duration: ${metricWithUnit(metrics, "source_video_duration_s", "s")}`,
      `Duration delta: ${metricWithUnit(metrics, "tts_duration_delta_s", "s")}`,
      ...manifestDetails,
    ];
  }
  if (stage === "lipsync") {
    return [
      `Output files: ${formatValue(metric(metrics, "lipsync_output_files"))}`,
      `Final MP4 count: ${formatValue(metric(metrics, "final_mp4_count"))}`,
      `Final MP4 size: ${metricWithUnit(metrics, "final_mp4_size_mb", " MB")}`,
      `Final MP4 duration: ${metricWithUnit(metrics, "final_mp4_duration_s", "s")}`,
      `Duration delta: ${metricWithUnit(metrics, "final_duration_delta_s", "s")}`,
      ...manifestDetails,
    ];
  }
  if (stage === "complete") {
    const speakerCount = status?.analysis?.speaker_analysis?.speakers_detected;
    const speakerStatus = status?.analysis?.speaker_analysis?.status?.replaceAll("_", " ") ?? "not determined";
    return [
      `Languages processed: ${formatValue(metric(metrics, "languagesProcessed"))}`,
      `Total backend time: ${metricWithUnit(metrics, "totalTime", "s")}`,
      speakerCount == null ? `Speaker analysis: ${speakerStatus}` : `Speakers detected: ${speakerCount}`,
      ...manifestDetails,
    ];
  }
  return [`Target: ${languages}`, ...manifestDetails];
}

export function PipelineTimeline({ status, storedJob }: { status: JobStatus | null; storedJob: StoredJob | null }) {
  const currentStage = status?.stage ?? "uploading";
  const history = status?.stageHistory ?? [];

  return (
    <aside className="grid gap-3 xl:sticky xl:top-28">
      {stages.map((item) => {
        const state = stateFor(currentStage, item.key, history, status);
        const event = history.find((historyItem) => historyItem.stage === item.key);
        const details = detailsFor(item.key, status, storedJob);
        return (
          <div key={item.key} className={`grid gap-4 rounded-md border p-5 shadow-sm ${state === "done" ? "border-emerald-500/30 bg-emerald-500/5" : state === "active" ? "border-foreground/30 bg-foreground/[0.04]" : state === "error" ? "border-destructive/40 bg-destructive/5" : "border-foreground/10 bg-card"}`}>
            <div className="grid gap-4 md:grid-cols-[32px_1fr_auto] md:items-start">
              <div>
                {state === "done" && <CheckCircle2 className="size-5 text-emerald-600" />}
                {state === "active" && <Loader2 className="size-5 animate-spin" />}
                {(state === "pending" || state === "not-run") && <CircleDashed className="size-5 text-muted-foreground" />}
                {state === "error" && <XCircle className="size-5 text-destructive" />}
              </div>
              <div className="min-w-0">
                <div className="font-medium">{item.title}</div>
                <div className="text-sm text-muted-foreground">{item.summary}</div>
              </div>
              <div className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">{state}</div>
            </div>
            <div className="grid gap-2 border-t border-foreground/10 pt-4 sm:grid-cols-2 xl:grid-cols-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Timer className="size-4" />
                {formatSeconds(event?.durationSeconds)}
              </div>
              {details.map((detail) => (
                <div key={detail} className="break-words text-sm text-muted-foreground">{detail}</div>
              ))}
            </div>
          </div>
        );
      })}
    </aside>
  );
}
