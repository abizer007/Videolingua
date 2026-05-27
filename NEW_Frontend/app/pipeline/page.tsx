"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, FileJson, Gauge, PackageCheck, RefreshCcw, ScanLine, ShieldCheck, Volume2, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { PipelineTimeline } from "@/components/vidiolingua/pipeline-timeline";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";
import { getJobStatus, getResult } from "@/lib/api";
import { manifestArtifactRows } from "@/lib/manifest-artifacts";
import { clearActiveJob, clearRunState, isTerminalStatus, markTerminalJob, readStoredJob, saveResult, updateStoredJobFromStatus } from "@/lib/pipeline-storage";
import type { JobStatus, MetricResult, MetricsReport, StoredJob } from "@/lib/types";

const metricLabels: Record<string, string> = {
  asr_segments: "ASR segments",
  speakers_detected: "Speakers detected",
  asr_output_files: "ASR files",
  translation_files: "Translation files",
  translation_backend: "Translation backend",
  translation_source_language: "Translation source",
  translation_fallback_used: "Translation fallback used",
  translation_qa_status: "Translation QA",
  translation_qa_checks_passed: "QA checks passed",
  translation_qa_warnings_count: "QA warnings",
  translation_qa_errors_count: "QA errors",
  translation_qa_empty_segments: "Empty translations",
  translation_qa_script_match: "Script match",
  translation_qa_number_issues: "Number issues",
  translation_qa_entity_issues: "Entity issues",
  translation_qa_expansion_ratio_warnings: "Expansion warnings",
  translation_qa_report_path: "QA report",
  linguistic_integrity_status: "Linguistic integrity",
  linguistic_integrity_score: "Integrity score",
  linguistic_integrity_script_status: "Script integrity",
  linguistic_integrity_number_warnings: "Number warnings",
  linguistic_integrity_name_warnings: "Name warnings",
  linguistic_integrity_expansion_warnings: "Expansion warnings",
  phonetic_resolution_status: "Phonetic resolution",
  phonetic_risk_score: "Phonetic risk score",
  phonetic_dictionary_used: "Pronunciation dictionary",
  phonetic_acronyms_detected: "Acronyms detected",
  phonetic_ambiguity_warnings: "Ambiguity warnings",
  indictrans2_supported_pair: "IndicTrans2 pair supported",
  target_language: "Target language",
  target_language_count: "Target languages",
  tts_files: "Generated audio files",
  tts_total_duration_s: "Generated audio duration",
  source_video_duration_s: "Source video duration",
  tts_duration_delta_s: "TTS duration delta",
  voice_backend: "Voice backend",
  xtts_selected: "XTTS selected",
  sarvam_selected: "Sarvam selected",
  generic_fallback_used: "Generic fallback used",
  exact_voice_clone: "Exact voice clone",
  managed_tts: "Managed TTS",
  audio_validation_passed: "Audio validation",
  sarvam_speaker: "Sarvam speaker preset",
  lipsync_method: "Lip sync method",
  lipsync_visual_sync_applied: "Visual lip sync applied",
  visual_lipsync_requested: "Visual lip sync requested",
  lipsync_mode: "Lip sync mode",
  lipsync_fallback_used: "Lip sync fallback used",
  wav2lip_preflight_ok: "Wav2Lip preflight",
  wav2lip_python: "Wav2Lip Python",
  wav2lip_checkpoint_exists: "Wav2Lip checkpoint",
  wav2lip_error: "Wav2Lip error",
  alignment_level: "Alignment level",
  prepared_audio_duration_s: "Prepared audio duration",
  audio_padded_sec: "Audio padded",
  audio_trimmed_sec: "Audio trimmed",
  lipsync_output_files: "Mux output files",
  final_mp4_count: "Final MP4 files",
  final_mp4_size_mb: "Final MP4 size",
  final_mp4_duration_s: "Final MP4 duration",
  final_duration_delta_s: "Final duration delta",
  output_validation_passed: "Output validation",
  output_has_video_stream: "Video stream",
  output_has_audio_stream: "Audio stream",
  video_codec: "Video codec",
  video_resolution: "Resolution",
  video_fps: "FPS",
  audio_codec: "Audio codec",
  audio_sample_rate: "Audio sample rate",
  audio_channels: "Audio channels",
  totalTime: "Backend runtime",
  languagesProcessed: "Languages processed",
  bgmPreserved: "BGM preserved",
  speakersDetected: "Speakers detected",
  validation_passed: "Validation passed",
  fallback_used: "Fallback used",
  reference_mode: "Reference mode",
  reference_audio_validation_passed: "Reference validation",
  speaker_analysis_status: "Speaker analysis",
  tts_wav_sample_rate: "TTS WAV sample rate",
  tts_wav_peak: "TTS WAV peak",
  tts_normalization_applied: "TTS normalization applied",
  prosody_profile_status: "Prosody profile",
  prosody_plan_status: "Prosody plan",
  prosody_preset: "Prosody preset",
  prosody_average_speech_rate_wpm: "Average speech rate",
  prosody_pause_count: "Pause count",
  prosody_duration_pressure: "Duration pressure",
  prosody_max_duration_pressure_ratio: "Duration pressure ratio",
  prosody_validation_status: "Prosody validation",
  hubert_feature_status: "HuBERT features",
  hubert_prosody_status: "HuBERT prosody",
  hubert_prosody_similarity_score: "HuBERT prosody similarity",
  hubert_adapter_status: "Adapter status",
  hubert_adapter_confidence: "Adapter confidence",
};

const hiddenMetricKeys = new Set(["indicf5_loaded", "speakersDetected", "speakers_detected"]);

function formatMetricValue(key: string, value: number | string | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") return "Waiting";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (value === 0 && /risk_score/i.test(key)) return "0 - no risk detected";
    if (value === 0 && /(warning|issue|empty|detected|ambiguity|acronym|term)/i.test(key)) return "None detected";
    const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2);
    if (key.endsWith("_s") || key === "totalTime") return `${formatted}s`;
    if (key.endsWith("_mb")) return `${formatted} MB`;
    return formatted;
  }
  return value;
}

function formatElapsed(value?: number | null) {
  if (typeof value !== "number") return "Waiting for first poll";
  if (value < 60) return `${value.toFixed(1)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}

function humanize(value?: string | null) {
  return value ? value.replaceAll("_", " ") : "pending";
}

function formatReferenceMode(value?: string | null) {
  if (value === "auto_extract") return "auto-extract";
  if (value === "none") return "none";
  return humanize(value);
}

function displayMetric(item?: MetricResult) {
  if (!item) return "Pending";
  if (item.status === "not_applicable") return "Not applicable";
  if (item.value === null || item.value === undefined || item.value === "") return humanize(item.status);
  if (typeof item.value === "number") {
    if (item.unit === "percent" || item.unit === "score_0_100") return `${item.value.toFixed(1)}%`;
    if (item.unit === "mos_1_5") return `${item.value.toFixed(2)} / 5`;
    if (item.unit === "ratio") return `${(item.value * 100).toFixed(1)}%`;
    return Number.isInteger(item.value) ? String(item.value) : item.value.toFixed(2);
  }
  return String(item.value);
}

function sourceBadge(item?: MetricResult) {
  const source = item?.reference_type ?? item?.status;
  if (source === "true_reference") return "reference-backed";
  if (source === "auto_reference") return "auto-reference";
  if (source === "proxy") return "proxy";
  if (source === "artifact") return "measured artifact";
  if (source === "not_applicable") return "not applicable";
  return humanize(source);
}

function TestingAnalysisCards({ report }: { report?: MetricsReport | null }) {
  const cards = [
    { title: "Overall quality index", item: report?.overall?.overall_quality_index },
    { title: report?.asr?.display_label ?? "ASR / Transcript score", item: report?.asr?.score },
    { title: report?.translation?.display_label ?? "Translation score", item: report?.translation?.score },
    { title: report?.voice?.display_label ?? "Voice naturalness", item: report?.voice?.mos ?? report?.voice?.score },
    { title: report?.sync?.display_label ?? "Sync quality", item: report?.sync?.score },
    { title: report?.speaker?.display_label ?? "Speaker similarity", item: report?.speaker?.voice_similarity ?? report?.speaker?.score },
    { title: "Output validation", item: report?.output_validation?.score },
  ];

  return (
    <div className="vl-panel-lg">
      <div className="mb-5 flex items-center gap-3">
        <Waves className="size-5 text-muted-foreground" />
        <div>
          <h2 className="font-display text-3xl">Testing / Analysis</h2>
          <p className="text-sm text-muted-foreground">The evaluation worker fills these cards after artifact analysis completes.</p>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {cards.map((card) => (
          <div key={card.title} className="vl-metric-row">
            <div className="vl-metric-label">{sourceBadge(card.item)}</div>
            <div className="mt-2 flex min-w-0 flex-wrap items-baseline justify-between gap-3">
              <div className="font-display text-xl leading-tight">{card.title}</div>
              <div className="font-display text-2xl leading-none">{displayMetric(card.item)}</div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">Method: {humanize(card.item?.method)} | Confidence: {humanize(card.item?.confidence)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PipelinePage() {
  const router = useRouter();
  const [storedJob, setStoredJob] = useState<StoredJob | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [terminalNotice, setTerminalNotice] = useState<string | null>(null);
  const [queryJobId, setQueryJobId] = useState("");
  const pollingTokenRef = useRef("");
  const artifactRows = manifestArtifactRows(status?.manifestSummary);

  useEffect(() => {
    setQueryJobId(new URLSearchParams(window.location.search).get("jobId") ?? "");
    setStoredJob(readStoredJob());
  }, []);

  const jobId = useMemo(() => queryJobId || storedJob?.jobId || "", [queryJobId, storedJob]);
  const lipsyncEvidence = (status?.analysis?.lipsync ?? status?.metricsReport?.lipsync ?? {}) as Record<string, number | string | boolean | null | undefined>;

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timeout: number | undefined;
    let busy = false;
    let fetchedTerminalResult = false;
    let controller: AbortController | null = null;
    const token = `${jobId}:${storedJob?.runSessionId ?? "query"}`;
    pollingTokenRef.current = token;

    function stopPolling() {
      if (timeout) window.clearTimeout(timeout);
      timeout = undefined;
      controller?.abort();
      controller = null;
    }

    function scheduleNextPoll() {
      if (cancelled || pollingTokenRef.current !== token) return;
      timeout = window.setTimeout(poll, 1500);
    }

    async function poll() {
      if (busy || cancelled || pollingTokenRef.current !== token) return;
      busy = true;
      controller = new AbortController();
      try {
        const nextStatus = await getJobStatus(jobId, { signal: controller.signal });
        if (cancelled) return;
        setStatus(nextStatus);
        updateStoredJobFromStatus(nextStatus);
        setError(null);

        if (isTerminalStatus(nextStatus)) {
          stopPolling();
          markTerminalJob({ ...nextStatus, runSessionId: storedJob?.runSessionId });
          setTerminalNotice(`Job ${jobId} ended with ${nextStatus.status ?? nextStatus.stage}.`);
          let result = null;
          if (!fetchedTerminalResult) {
            fetchedTerminalResult = true;
            result = await getResult(jobId).catch((resultError) => {
              if ((nextStatus.status ?? nextStatus.stage) !== "complete") {
                setError(resultError instanceof Error ? resultError.message : "The backend reported a pipeline error.");
              }
              return null;
            });
          }
          if (result) saveResult(result);
          if ((nextStatus.status ?? nextStatus.stage) === "complete") {
            window.setTimeout(() => router.push(`/results?jobId=${encodeURIComponent(jobId)}`), 900);
          } else {
            setError(result?.error ?? nextStatus.errorSummary ?? nextStatus.error ?? "The backend reported a pipeline error.");
          }
          return;
        }
      } catch (pollError) {
        if (!cancelled && !(pollError instanceof DOMException && pollError.name === "AbortError")) {
          const message = pollError instanceof Error ? pollError.message : "Could not fetch job status.";
          setError(message);
          if (/job not found/i.test(message) || /404/.test(message)) {
            clearActiveJob();
            setTerminalNotice("The saved job is no longer available on the backend. Old job state was cleared.");
            return;
          }
        }
      } finally {
        busy = false;
        controller = null;
      }
      scheduleNextPoll();
    }

    poll();
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [jobId, router, storedJob?.runSessionId]);

  function startFreshRun() {
    pollingTokenRef.current = "";
    clearRunState();
    router.push("/upload");
  }

  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-10 grid gap-8 lg:grid-cols-[0.8fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Pipeline status
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">Follow the run through each stage.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            The page polls the backend, keeps the active stage visible, and carries final metadata to the results page when the run completes or fails.
          </p>
        </div>

        {!jobId ? (
          <div className="border border-foreground/10 bg-card p-8">
            <h2 className="mb-3 font-display text-4xl">No active job</h2>
            <p className="mb-6 text-muted-foreground">Start with an upload so the pipeline page has a job id to poll.</p>
            <Button asChild className="rounded-full">
              <Link href="/upload">Go to upload</Link>
            </Button>
          </div>
        ) : (
          <div className="grid gap-6 xl:grid-cols-[minmax(0,0.74fr)_minmax(420px,1fr)] xl:items-start">
            <div className="space-y-6">
              <div className="vl-panel-lg">
                <div className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Job id</div>
                <div className="break-all font-mono text-sm">{jobId}</div>
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
                  <div className="min-w-0">
                    <h2 className="font-display text-4xl leading-tight">Progress</h2>
                    <p className="text-sm text-muted-foreground">{status?.stage ?? "Waiting for backend status"}</p>
                  </div>
                  <div className="font-display text-5xl leading-none">{status?.progress ?? 0}%</div>
                </div>
                <Progress value={status?.progress ?? 0} className="h-3 rounded-none" />
              </div>

              <div className="vl-panel-lg">
                <h2 className="mb-4 font-display text-3xl">Run routing</h2>
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">Translation: {status?.manifestSummary?.selected_backends?.translation ?? storedJob?.translationBackend ?? "IndicTrans2 / configured router"}</div>
                  <div className="vl-metric-row">Voice: {status?.manifestSummary?.selected_backends?.voice ?? storedJob?.voiceLabel ?? "XTTS / Sarvam according to language"}</div>
                  <div className="vl-metric-row">Reference: {formatReferenceMode(status?.analysis?.reference_audio?.mode?.toString() ?? storedJob?.referenceMode)}</div>
                  <div className="vl-metric-row">Target: {status?.languages?.join(", ") || storedJob?.targetLanguage || "Waiting"}</div>
                  <div className="vl-metric-row">Elapsed: {formatElapsed(status?.elapsedSeconds)}</div>
                </div>
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex items-center gap-3">
                  <ShieldCheck className="size-5 text-muted-foreground" />
                  <h2 className="font-display text-3xl">Responsible AI & Provenance</h2>
                </div>
                {status?.responsibleAI ? (
                  <div className="vl-metric-grid text-sm">
                    <div className="vl-metric-row">Mode: {humanize(status.responsibleAI.mode)}</div>
                    <div className="vl-metric-row">Passport: {humanize(status.responsibleAI.passportStatus)}</div>
                    <div className="vl-metric-row">SGI risk: {humanize(status.responsibleAI.sgiRiskLevel)}</div>
                    <div className="vl-metric-row">Speaker consent recorded: {formatMetricValue("speaker_consent", status.responsibleAI.speakerConsentRecorded)}</div>
                    <div className="vl-metric-row">Disclosure: {formatMetricValue("visible_disclosure", status.responsibleAI.visibleDisclosureApplied)}</div>
                    <div className="vl-metric-row">Provenance manifest: {formatMetricValue("provenance", status.responsibleAI.provenanceManifestCreated)}</div>
                    <div className="vl-metric-row">Hashes/fingerprints: {formatMetricValue("hashes", status.responsibleAI.hashesGenerated)}</div>
                    <div className="vl-metric-row">Safe for demo/export: {formatMetricValue("safe", status.responsibleAI.safeForDemoExport)}</div>
                    <div className="vl-metric-row">Warnings/errors: {formatMetricValue("warnings", status.responsibleAI.warningsCount)} / {formatMetricValue("errors", status.responsibleAI.errorsCount)}</div>
                  </div>
                ) : (
                  <div className="border border-dashed border-foreground/15 p-4 text-sm text-muted-foreground">Compliance passport will appear for new runs.</div>
                )}
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex items-center gap-3">
                  <ShieldCheck className="size-5 text-muted-foreground" />
                  <h2 className="font-display text-3xl">Translation integrity</h2>
                </div>
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">QA status: {status?.translationQA?.status ?? status?.analysis?.translationQA?.status ?? formatMetricValue("translation_qa_status", status?.metrics?.translation_qa_status)}</div>
                  <div className="vl-metric-row">Empty segments: {formatMetricValue("translation_qa_empty_segments", status?.translationQA?.emptySegments ?? status?.analysis?.translationQA?.emptySegments ?? status?.metrics?.translation_qa_empty_segments)}</div>
                  <div className="vl-metric-row">Script check: {formatMetricValue("translation_qa_script_match", status?.translationQA?.scriptMatch ?? status?.analysis?.translationQA?.scriptMatch ?? status?.metrics?.translation_qa_script_match)}</div>
                  <div className="vl-metric-row">Numbers/entities: {formatMetricValue("translation_qa_number_issues", status?.translationQA?.numberIssues ?? status?.analysis?.translationQA?.numberIssues ?? status?.metrics?.translation_qa_number_issues)} / {formatMetricValue("translation_qa_entity_issues", status?.translationQA?.entityIssues ?? status?.analysis?.translationQA?.entityIssues ?? status?.metrics?.translation_qa_entity_issues)}</div>
                  <div className="vl-metric-row">Expansion warnings: {formatMetricValue("translation_qa_expansion_ratio_warnings", status?.translationQA?.expansionRatioWarnings ?? status?.analysis?.translationQA?.expansionRatioWarnings ?? status?.metrics?.translation_qa_expansion_ratio_warnings)}</div>
                  <div className="vl-metric-row">Glossary / memory: {formatMetricValue("translation_qa_glossary", status?.translationQA?.glossaryApplied ?? status?.analysis?.translationQA?.glossaryApplied)} / {formatMetricValue("translation_qa_memory", status?.translationQA?.translationMemoryHits ?? status?.analysis?.translationQA?.translationMemoryHits)}</div>
                </div>
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex items-center gap-3">
                  <ShieldCheck className="size-5 text-muted-foreground" />
                  <h2 className="font-display text-3xl">Language integrity</h2>
                </div>
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">Status: {status?.linguisticIntegrity?.status ?? status?.analysis?.linguisticIntegrity?.status ?? formatMetricValue("linguistic_integrity_status", status?.metrics?.linguistic_integrity_status)}</div>
                  <div className="vl-metric-row">Score: {formatMetricValue("linguistic_integrity_score", status?.linguisticIntegrity?.score ?? status?.analysis?.linguisticIntegrity?.score ?? status?.metrics?.linguistic_integrity_score)}</div>
                  <div className="vl-metric-row">Script: {status?.linguisticIntegrity?.scriptStatus ?? status?.analysis?.linguisticIntegrity?.scriptStatus ?? formatMetricValue("linguistic_integrity_script_status", status?.metrics?.linguistic_integrity_script_status)}</div>
                  <div className="vl-metric-row">Names / numbers: {formatMetricValue("linguistic_integrity_name_warnings", status?.linguisticIntegrity?.nameWarnings ?? status?.analysis?.linguisticIntegrity?.nameWarnings ?? status?.metrics?.linguistic_integrity_name_warnings)} / {formatMetricValue("linguistic_integrity_number_warnings", status?.linguisticIntegrity?.numberWarnings ?? status?.analysis?.linguisticIntegrity?.numberWarnings ?? status?.metrics?.linguistic_integrity_number_warnings)}</div>
                  <div className="vl-metric-row">Expansion warnings: {formatMetricValue("linguistic_integrity_expansion_warnings", status?.linguisticIntegrity?.expansionWarnings ?? status?.analysis?.linguisticIntegrity?.expansionWarnings ?? status?.metrics?.linguistic_integrity_expansion_warnings)}</div>
                </div>
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex items-center gap-3">
                  <Volume2 className="size-5 text-muted-foreground" />
                  <h2 className="font-display text-3xl">Phonetic resolution</h2>
                </div>
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">Status: {status?.phoneticResolution?.status ?? status?.analysis?.phoneticResolution?.status ?? formatMetricValue("phonetic_resolution_status", status?.metrics?.phonetic_resolution_status)}</div>
                  <div className="vl-metric-row">Risk score: {formatMetricValue("phonetic_risk_score", status?.phoneticResolution?.phoneticRiskScore ?? status?.analysis?.phoneticResolution?.phoneticRiskScore ?? status?.metrics?.phonetic_risk_score)}</div>
                  <div className="vl-metric-row">Dictionary used: {formatMetricValue("phonetic_dictionary_used", status?.phoneticResolution?.dictionaryUsed ?? status?.analysis?.phoneticResolution?.dictionaryUsed ?? status?.metrics?.phonetic_dictionary_used)}</div>
                  <div className="vl-metric-row">Acronyms / ambiguities: {formatMetricValue("phonetic_acronyms_detected", status?.phoneticResolution?.acronymsDetected ?? status?.analysis?.phoneticResolution?.acronymsDetected ?? status?.metrics?.phonetic_acronyms_detected)} / {formatMetricValue("phonetic_ambiguity_warnings", status?.phoneticResolution?.ambiguityWarnings ?? status?.analysis?.phoneticResolution?.ambiguityWarnings ?? status?.metrics?.phonetic_ambiguity_warnings)}</div>
                </div>
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex items-center gap-3">
                  <Gauge className="size-5 text-muted-foreground" />
                  <h2 className="font-display text-3xl">Prosody profile</h2>
                </div>
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">Profile: {formatMetricValue("prosody_profile_status", status?.metrics?.prosody_profile_status ?? status?.analysis?.prosodyElocution?.status)}</div>
                  <div className="vl-metric-row">HuBERT features: {formatMetricValue("hubert_feature_status", status?.metrics?.hubert_feature_status ?? status?.analysis?.prosodyElocution?.hubertStatus)}</div>
                  <div className="vl-metric-row">Adapter: {formatMetricValue("hubert_adapter_status", status?.metrics?.hubert_adapter_status ?? status?.analysis?.prosodyElocution?.adapterStatus)}</div>
                  <div className="vl-metric-row">Preset: {formatMetricValue("prosody_preset", status?.metrics?.prosody_preset ?? status?.analysis?.prosodyElocution?.preset)}</div>
                  <div className="vl-metric-row">Average speech rate: {formatMetricValue("prosody_average_speech_rate_wpm", status?.metrics?.prosody_average_speech_rate_wpm ?? status?.analysis?.prosodyElocution?.averageSpeechRateWpm)}</div>
                  <div className="vl-metric-row">Pause count: {formatMetricValue("prosody_pause_count", status?.metrics?.prosody_pause_count ?? status?.analysis?.prosodyElocution?.pauseCount)}</div>
                  <div className="vl-metric-row">Duration pressure: {formatMetricValue("prosody_duration_pressure", status?.metrics?.prosody_duration_pressure ?? status?.analysis?.prosodyElocution?.durationPressure)}</div>
                  <div className="vl-metric-row">HuBERT similarity: {formatMetricValue("hubert_prosody_similarity_score", status?.metrics?.hubert_prosody_similarity_score ?? status?.analysis?.prosodyElocution?.hubertProsodySimilarity)}</div>
                </div>
              </div>

              <div className="vl-panel-lg">
                <div className="mb-4 flex items-center gap-3">
                  <ScanLine className="size-5 text-muted-foreground" />
                  <h2 className="font-display text-3xl">Lip-sync evidence</h2>
                </div>
                <div className="mb-3 text-sm text-muted-foreground">
                  {(lipsyncEvidence.method ?? status?.metrics?.lipsync_method) === "ffmpeg"
                    ? "Audio replacement only - no mouth animation model applied."
                    : "Visual lip-sync evidence from the backend run."}
                </div>
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">Mode: {formatMetricValue("lipsync_mode", lipsyncEvidence.mode ?? status?.metrics?.lipsync_mode)}</div>
                  <div className="vl-metric-row">Method: {formatMetricValue("lipsync_method", lipsyncEvidence.method ?? status?.metrics?.lipsync_method)}</div>
                  <div className="vl-metric-row">Visual sync applied: {formatMetricValue("lipsync_visual_sync_applied", lipsyncEvidence.visual_sync_applied ?? status?.metrics?.lipsync_visual_sync_applied)}</div>
                  <div className="vl-metric-row">Visual sync requested: {formatMetricValue("visual_lipsync_requested", lipsyncEvidence.visual_sync_requested ?? status?.metrics?.visual_lipsync_requested)}</div>
                  <div className="vl-metric-row">Fallback used: {formatMetricValue("lipsync_fallback_used", lipsyncEvidence.fallback_used ?? status?.metrics?.lipsync_fallback_used)}</div>
                  <div className="vl-metric-row">Wav2Lip preflight: {formatMetricValue("wav2lip_preflight_ok", lipsyncEvidence.wav2lip_preflight_ok ?? status?.metrics?.wav2lip_preflight_ok)}</div>
                  <div className="vl-metric-row">Wav2Lip Python: {formatMetricValue("wav2lip_python", lipsyncEvidence.wav2lip_python ?? status?.metrics?.wav2lip_python)}</div>
                  <div className="vl-metric-row">Checkpoint: {formatMetricValue("wav2lip_checkpoint_exists", lipsyncEvidence.checkpoint_exists ?? status?.metrics?.wav2lip_checkpoint_exists)}</div>
                  <div className="vl-metric-row">Alignment level: {formatMetricValue("alignment_level", lipsyncEvidence.alignment_level ?? status?.metrics?.alignment_level)}</div>
                  <div className="vl-metric-row">Source video: {formatMetricValue("source_video_duration_s", lipsyncEvidence.source_video_duration_s ?? status?.metrics?.source_video_duration_s)}</div>
                  <div className="vl-metric-row">Generated audio: {formatMetricValue("tts_total_duration_s", lipsyncEvidence.generated_audio_duration_s ?? status?.metrics?.tts_total_duration_s)}</div>
                  <div className="vl-metric-row">Prepared audio: {formatMetricValue("prepared_audio_duration_s", lipsyncEvidence.prepared_audio_duration_s ?? status?.metrics?.prepared_audio_duration_s)}</div>
                  <div className="vl-metric-row">Final MP4: {formatMetricValue("final_mp4_duration_s", lipsyncEvidence.final_mp4_duration_s ?? status?.metrics?.final_mp4_duration_s)}</div>
                  <div className="vl-metric-row">Delta: {formatMetricValue("final_duration_delta_s", lipsyncEvidence.duration_delta_s ?? status?.metrics?.final_duration_delta_s)}</div>
                  <div className="vl-metric-row">Padded / trimmed: {formatMetricValue("audio_padded_sec", lipsyncEvidence.audio_padded_sec ?? status?.metrics?.audio_padded_sec)} / {formatMetricValue("audio_trimmed_sec", lipsyncEvidence.audio_trimmed_sec ?? status?.metrics?.audio_trimmed_sec)}</div>
                  <div className="vl-metric-row">Wav2Lip error: {formatMetricValue("wav2lip_error", lipsyncEvidence.wav2lip_error ?? status?.metrics?.wav2lip_error)}</div>
                </div>
              </div>

              {status?.manifestSummary && (
                <div className="vl-panel-lg">
                  <div className="mb-4 flex items-center gap-3">
                    <FileJson className="size-5 text-muted-foreground" />
                    <h2 className="font-display text-3xl">Run manifest</h2>
                  </div>
                  <div className="vl-metric-grid text-sm">
                    <div className="vl-metric-row">Current stage: {humanize(status.manifestSummary.current_stage)}</div>
                    <div className="vl-metric-row">Last checkpoint: {humanize(status.manifestSummary.last_completed_stage)}</div>
                    <div className="vl-metric-row">Failure checkpoint: {humanize(status.manifestSummary.failed_stage)}</div>
                    <div className="vl-metric-row">Recovery readiness: {status.manifestSummary.resume_supported ? "resume execution available" : "metadata only"}</div>
                  </div>
                  {(status.manifestSummary.resume_command_hint || status.manifestSummary.retry_failed_stage_hint) && (
                    <p className="mt-4 text-sm text-muted-foreground">
                      {status.manifestSummary.retry_failed_stage_hint ?? status.manifestSummary.resume_command_hint}
                    </p>
                  )}
                </div>
              )}

              {artifactRows.length > 0 && (
                <div className="vl-panel-lg">
                  <div className="mb-4 flex items-center gap-3">
                    <PackageCheck className="size-5 text-muted-foreground" />
                    <h2 className="font-display text-3xl">Stage evidence</h2>
                  </div>
                  <div className="grid gap-3 text-sm">
                    {artifactRows.map((artifact) => (
                      <div key={artifact.key} className="vl-metric-row">
                        <div className="vl-metric-label">{artifact.label}</div>
                        <div className="vl-metric-value">{artifact.value}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{artifact.meta}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="vl-panel-lg">
                <h2 className="mb-4 font-display text-3xl">Analysis status</h2>
                {(() => {
                  const speaker = status?.analysis?.speaker_analysis;
                  const speakerStatus = speaker?.status?.replaceAll("_", " ") ?? "Pending";
                  const speakerCount = ["computed", "defaulted"].includes(speaker?.status ?? "") ? speaker?.speakers_detected ?? speaker?.speaker_count : null;
                  const voiceStatus = speaker?.voice_assignment_status?.replaceAll("_", " ");
                  const visualStatus = speaker?.visual_analysis_status?.replaceAll("_", " ");
                  const warnings = speaker?.warnings?.join(" ");
                  const errors = speaker?.errors?.join(" ");
                  const voicePlan = speaker?.sarvam_voice_plan_speakers?.[0];
                  return (
                    <div className="mb-4 border border-foreground/10 p-4 text-sm">
                      <div className="font-medium">Speaker analysis: {speakerStatus}{speakerCount != null ? ` (${speakerCount})` : ""}</div>
                      {speaker?.status === "failed" && (
                        <div className="mt-2 text-destructive">{errors || speaker.reason || "Speaker analysis failed."}</div>
                      )}
                      {speaker?.status === "unavailable" && (
                        <div className="mt-2 text-muted-foreground">{speaker.reason || "Speaker analysis unavailable."}</div>
                      )}
                      {speaker?.recommended_fix && <div className="mt-2 text-muted-foreground">{speaker.recommended_fix}</div>}
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        <div>Transcript segments: {formatMetricValue("segment_count", speaker?.segment_count)}</div>
                        <div>Unknown / ambiguous: {formatMetricValue("unknown_segment_count", speaker?.unknown_segment_count)} / {formatMetricValue("ambiguous_segment_count", speaker?.ambiguous_segment_count)}</div>
                        <div>Voice assignment: {voiceStatus ?? "Waiting"}</div>
                        <div>Visual analysis: {visualStatus ?? "Waiting"}</div>
                        <div>Reference candidates: {formatMetricValue("speaker_reference_count", speaker?.speaker_reference_count)}</div>
                        <div>Labels: {speaker?.speaker_labels?.length ? speaker.speaker_labels.join(", ") : "Waiting"}</div>
                        <div>Voice profile hint: {voicePlan?.voice_profile_hint?.toString().replaceAll("_", " ") ?? "Waiting"}</div>
                        <div>Sarvam voice: {voicePlan?.selected_tts_voice ?? "Waiting"}</div>
                      </div>
                      {voicePlan?.selection_reason && <div className="mt-3 text-xs text-muted-foreground">{voicePlan.selection_reason}</div>}
                      {warnings && <div className="mt-3 text-xs text-muted-foreground">{warnings}</div>}
                      <div className="mt-3 text-xs text-muted-foreground">
                        Sarvam uses managed TTS voice selection per detected speaker profile where available. Not exact voice cloning. Voice profile hints are suggestions, not identity detection.
                      </div>
                    </div>
                  );
                })()}
                <div className="vl-metric-grid text-sm">
                  <div className="vl-metric-row">
                    Reference audio: {status?.analysis?.reference_audio?.validation_passed === true ? "validated" : status?.analysis?.reference_audio?.mode === "none" ? "none" : status?.analysis?.reference_audio?.mode === "auto_extract" ? formatMetricValue("auto_extract", status?.analysis?.reference_audio?.status) : "pending"}
                  </div>
                  <div className="vl-metric-row">
                    Output validation: {status?.analysis?.output_inspection?.validation_passed === true ? "passed" : status?.analysis?.output_inspection?.validation_passed === false ? "failed" : "pending"}
                  </div>
                </div>
              </div>

              <TestingAnalysisCards report={status?.metricsReport} />

              <div className="vl-panel-lg">
                <h2 className="mb-2 font-display text-3xl">Live run evidence</h2>
                <p className="mb-4 text-sm text-muted-foreground">
                  These values are reported by the current backend job as stages finish. Empty fields stay empty instead of being filled with guesses.
                </p>
                {status?.metrics && Object.keys(status.metrics).length > 0 ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {Object.entries(status.metrics).filter(([key]) => !hiddenMetricKeys.has(key)).map(([key, value]) => (
                      <div key={key} className="vl-metric-row">
                        <div className="vl-metric-label">{metricLabels[key] ?? key.replaceAll("_", " ")}</div>
                        <div className="vl-metric-value text-base">{formatMetricValue(key, value)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="border border-dashed border-foreground/15 p-4 text-sm text-muted-foreground">
                    Waiting for the backend to finish the first measurable stage.
                  </div>
                )}
              </div>

              {error && (
                <div className="border border-destructive/40 bg-destructive/5 p-5 text-sm text-destructive">
                  <div className="font-medium">{status?.stage ? `Stage: ${humanize(status.stage)}` : "Pipeline issue"}</div>
                  <p className="mt-1">{error}</p>
                </div>
              )}

              {terminalNotice && (
                <div className="border border-foreground/10 bg-card p-5 text-sm text-muted-foreground">
                  {terminalNotice} You can inspect the result payload or start with a clean browser/backend job state.
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <Button type="button" variant="outline" className="rounded-full border-foreground/20" onClick={startFreshRun}>
                    <RefreshCcw className="size-4" />
                    Start fresh run
                </Button>
                <Button type="button" variant="outline" className="rounded-full border-foreground/20" onClick={startFreshRun}>
                  Clear old job state
                </Button>
                <Button asChild className="rounded-full">
                  <Link href={`/results?jobId=${encodeURIComponent(jobId)}`}>
                    Open results
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </div>

            <PipelineTimeline status={status} storedJob={storedJob} />
          </div>
        )}
      </section>
      <SiteFooter />
    </main>
  );
}
