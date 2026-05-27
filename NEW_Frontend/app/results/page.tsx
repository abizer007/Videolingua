"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowRight, CheckCircle2, FileAudio, FileJson, FileVideo, GitBranch, Info, Mic2, ScanLine, ShieldCheck, Volume2, Waves } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ResultVideoCard } from "@/components/vidiolingua/result-video-card";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";
import { getResult } from "@/lib/api";
import { resultManifestArtifactRows } from "@/lib/manifest-artifacts";
import { clearRunState, markTerminalJob, readResult, readStoredJob, saveResult } from "@/lib/pipeline-storage";
import type { MetricResult, MetricsReport, ProcessingResult, StoredJob } from "@/lib/types";

const proofOutputs = [
  {
    title: "French official test",
    backend: "XTTS speaker-reference voice",
    path: "outputs\\french_official_test\\results\\Vidiolingua_Test_Official_dubbed_fr.mp4",
    note: "Protected known-good MP4 with H.264 video and AAC audio.",
  },
  {
    title: "Kannada Sarvam practical test",
    backend: "IndicTrans2 + Sarvam managed Indian-language TTS",
    path: "outputs\\kannada_sarvam_practical_test_clipfix\\results\\Vidiolingua_Test_Official_dubbed_kn.mp4",
    note: "Protected known-good MP4. Sarvam is managed TTS, not exact voice cloning.",
  },
];

type MetricValue = number | string | boolean | null | undefined;

function formatValue(value: MetricValue, unit = "") {
  if (value === null || value === undefined || value === "") return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return `${Number.isInteger(value) ? value : value.toFixed(2)}${unit}`;
  return String(value);
}

function metric(result: ProcessingResult | null, key: string): MetricValue {
  return result?.metrics?.[key];
}

function analysisValue(result: ProcessingResult | null, section: keyof NonNullable<ProcessingResult["analysis"]>, key: string): MetricValue {
  const value = result?.analysis?.[section];
  if (!value || Array.isArray(value) || typeof value !== "object") return undefined;
  return (value as Record<string, MetricValue>)[key];
}

function statusText(value: MetricValue) {
  if (typeof value !== "string") return value;
  return value.replaceAll("_", " ");
}

function reportValue(result: ProcessingResult | null, section: keyof NonNullable<ProcessingResult["metricsReport"]>, key: string): MetricValue {
  const value = result?.metricsReport?.[section];
  if (!value || Array.isArray(value) || typeof value !== "object") return undefined;
  return (value as Record<string, MetricValue>)[key];
}

function metricResultText(item: { status?: string; value?: MetricValue; label?: string; reason?: string | null } | undefined) {
  if (!item) return "Not available";
  if (item.status === "computed") {
    const prefix = item.label ? `${item.label}: ` : "";
    return `${prefix}${formatValue(item.value)}`;
  }
  if (item.reason) return `${String(item.status ?? "unavailable").replaceAll("_", " ")} - ${item.reason}`;
  return String(item.status ?? "Not available").replaceAll("_", " ");
}

function humanize(value?: string | null) {
  return value ? value.replaceAll("_", " ") : "waiting";
}

function displayMetric(item?: MetricResult) {
  if (!item) return "Waiting";
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

function methodLabel(item?: MetricResult) {
  return humanize(item?.method ?? item?.status);
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

function isZeroIssueMetric(label: string, value: MetricValue) {
  if (value !== 0) return false;
  return /(warning|issue|empty|detected|ambiguity|acronym|term)/i.test(label);
}

function formatEvidenceValue(label: string, value: MetricValue, unit = "") {
  if (isZeroIssueMetric(label, value)) return "None detected";
  if (/risk score/i.test(label) && value === 0) return "0 - no phonetic risk detected";
  return formatValue(statusText(value), unit);
}

function TestingAnalysisCards({ report }: { report?: MetricsReport | null }) {
  const cards = [
    {
      title: "Overall quality index",
      item: report?.overall?.overall_quality_index,
      fallback: report?.overall?.score_0_100 != null ? `${report.overall.score_0_100.toFixed(1)}%` : "Waiting",
      explanation: report?.overall?.explanation,
    },
    { title: report?.asr?.display_label ?? "ASR / Transcript score", item: report?.asr?.score },
    { title: report?.translation?.display_label ?? "Translation score", item: report?.translation?.score },
    { title: report?.voice?.display_label ?? "Voice naturalness", item: report?.voice?.mos ?? report?.voice?.score },
    { title: report?.sync?.display_label ?? "Sync quality", item: report?.sync?.score },
    { title: report?.speaker?.display_label ?? "Speaker similarity", item: report?.speaker?.voice_similarity ?? report?.speaker?.score },
    { title: "Output validation", item: report?.output_validation?.score },
  ];

  return (
    <div className="vl-panel-lg">
      <div className="mb-6 flex items-center gap-3">
        <Waves className="size-5 text-muted-foreground" />
        <div>
          <h2 className="font-display text-4xl">Testing / Analysis</h2>
          <p className="text-sm text-muted-foreground">Automatic backend evaluation. Each card says whether it is reference-backed, auto-reference, proxy, or not applicable.</p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {cards.map((card) => (
          <div key={card.title} className="vl-metric-row">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">{sourceBadge(card.item)}</div>
                <h3 className="mt-1 font-display text-2xl">{card.title}</h3>
              </div>
              <div className="font-display text-3xl">{card.item ? displayMetric(card.item) : card.fallback ?? "Waiting"}</div>
            </div>
            <div className="grid gap-2 text-xs text-muted-foreground">
              <div>Method: {methodLabel(card.item)}</div>
              <div>Confidence: {humanize(card.item?.confidence ?? report?.overall?.confidence)}</div>
              <p>{card.item?.explanation ?? card.explanation ?? "Evaluation worker has not produced this card yet."}</p>
            </div>
          </div>
        ))}
      </div>
      {(report?.warnings?.length ?? 0) > 0 && (
        <div className="mt-4 border border-amber-500/25 bg-amber-500/5 p-3 text-xs text-muted-foreground">
          {report?.warnings?.join(" ")}
        </div>
      )}
    </div>
  );
}

function EvidencePanel({
  title,
  icon: Icon,
  items,
}: {
  title: string;
  icon: LucideIcon;
  items: Array<{ label: string; value: MetricValue; unit?: string }>;
}) {
  return (
    <div className="vl-panel">
      <div className="mb-5 flex items-center gap-3">
        <Icon className="size-5 shrink-0 text-muted-foreground" />
        <h3 className="font-display text-3xl leading-tight">{title}</h3>
      </div>
      <div className="vl-metric-grid">
        {items.filter((item) => item.value !== null && item.value !== undefined && item.value !== "").map((item) => (
          <div key={item.label} className="vl-metric-row">
            <div className="vl-metric-label">{item.label}</div>
            <div className="vl-metric-value">{formatEvidenceValue(item.label, item.value, item.unit)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const [activeJobId, setActiveJobId] = useState("");
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [storedJob, setStoredJob] = useState<StoredJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const queryJobId = new URLSearchParams(window.location.search).get("jobId") ?? "";
    const job = readStoredJob();
    const cachedResult = readResult();
    const activeJobId = queryJobId || job?.jobId || "";
    setActiveJobId(activeJobId);
    setStoredJob(job);
    if (cachedResult && (!activeJobId || cachedResult.jobId === activeJobId)) {
      setResult(cachedResult);
    }

    if (!activeJobId) return;
    const controller = new AbortController();
    getResult(activeJobId, { signal: controller.signal })
      .then((nextResult) => {
        setResult(nextResult);
        saveResult(nextResult);
        if (nextResult.status && nextResult.status !== "running") {
          markTerminalJob({
            jobId: nextResult.jobId,
            status: nextResult.status,
            stage: nextResult.stage ?? nextResult.status,
            terminalAt: new Date().toISOString(),
            errorSummary: nextResult.errorSummary ?? nextResult.error,
          });
        }
      })
      .catch((resultError) => {
        if (!(resultError instanceof DOMException && resultError.name === "AbortError")) {
          setError(resultError instanceof Error ? resultError.message : "No completed result is available yet.");
        }
      });
    return () => controller.abort();
  }, []);

  const translationQA = result?.translationQA ?? result?.analysis?.translationQA ?? null;
  const linguisticIntegrity = result?.linguisticIntegrity ?? result?.analysis?.linguisticIntegrity ?? null;
  const phoneticResolution = result?.phoneticResolution ?? result?.analysis?.phoneticResolution ?? null;
  const prosodyElocution = result?.analysis?.prosodyElocution ?? result?.metricsReport?.prosody ?? null;
  const hubertAdapterConfidence = prosodyElocution?.adapterConfidence ?? reportValue(result, "prosody", "adapter_confidence") ?? metric(result, "hubert_adapter_confidence");
  const manifestArtifacts = resultManifestArtifactRows(result);
  const resultMetrics = result?.metrics ?? { totalTime: 0, languagesProcessed: result?.localizedVideos?.length ?? 0 };
  const localizedVideos = result?.localizedVideos ?? [];
  const firstLocalizedLanguage = localizedVideos[0]?.language;
  const lipsyncEvidence = (result?.analysis?.lipsync ?? result?.metricsReport?.lipsync ?? {}) as Record<string, MetricValue>;

  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-10 grid gap-8 lg:grid-cols-[0.8fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Results and proof outputs
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">Final localized video, ready to inspect.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Completed runs return result metadata and video URLs from the backend. Protected French and Kannada artifacts remain listed as known-good references.
          </p>
        </div>

        {error && (
          <div className="mb-8 flex gap-3 border border-amber-500/30 bg-amber-500/5 p-5 text-sm">
            <AlertCircle className="mt-0.5 size-5 text-amber-600" />
            <div>
              <div className="font-medium">No fresh result loaded</div>
              <p className="text-muted-foreground">{error}</p>
            </div>
          </div>
        )}

        {result ? (
          <div className="mb-14 grid gap-6 lg:grid-cols-[0.72fr_1fr]">
            <div className="space-y-6">
              <div className="vl-panel-lg">
                <div className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Job metadata</div>
                <h2 className="mb-4 font-display text-4xl">{result.error ? "Backend reported an issue" : "Processing complete"}</h2>
                <div className="grid gap-3 text-sm">
                  <div className="vl-metric-row">Job: <span className="break-all font-mono">{result.jobId}</span></div>
                  <div className="vl-metric-row">Target: {formatValue(analysisValue(result, "run_evidence", "target_language") ?? metric(result, "target_language") ?? storedJob?.targetLanguage ?? firstLocalizedLanguage)}</div>
                  <div className="vl-metric-row">Processed: {formatValue(resultMetrics.languagesProcessed)}</div>
                  <div className="vl-metric-row">Total time: {formatValue(analysisValue(result, "run_evidence", "total_elapsed_sec") ?? resultMetrics.totalTime, "s")}</div>
                  {result.error && <div className="border border-destructive/30 bg-destructive/5 p-3 text-destructive">Error: {result.error}</div>}
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    className="rounded-full border-foreground/20"
                    onClick={() => {
                      clearRunState();
                      window.location.href = "/upload";
                    }}
                  >
                    Start fresh run
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="rounded-full border-foreground/20"
                    onClick={() => {
                      clearRunState();
                      setStoredJob(null);
                      setError(null);
                    }}
                  >
                    Clear old job state
                  </Button>
                </div>
              </div>

              <EvidencePanel
                title="Run evidence"
                icon={GitBranch}
                items={[
                  { label: "Elapsed time", value: reportValue(result, "operational", "total_elapsed_sec") ?? analysisValue(result, "run_evidence", "total_elapsed_sec") ?? resultMetrics.totalTime, unit: "s" },
                  { label: "Current stage", value: reportValue(result, "operational", "current_stage") },
                  { label: "Terminal stage", value: reportValue(result, "operational", "terminal_stage") },
                  { label: "Source language", value: analysisValue(result, "run_evidence", "source_language") ?? metric(result, "translation_source_language") },
                  { label: "Target language", value: reportValue(result, "operational", "target_language") ?? analysisValue(result, "run_evidence", "target_language") ?? metric(result, "target_language") ?? storedJob?.targetLanguage ?? firstLocalizedLanguage },
                  { label: "Translation route", value: reportValue(result, "operational", "translation_backend") ?? analysisValue(result, "run_evidence", "translation_backend") ?? metric(result, "translation_backend") ?? storedJob?.translationBackend },
                  { label: "Voice route", value: reportValue(result, "operational", "voice_backend") ?? analysisValue(result, "run_evidence", "voice_backend") ?? metric(result, "voice_backend") ?? storedJob?.voiceLabel },
                  { label: "Sarvam speaker preset", value: metric(result, "sarvam_speaker") ?? result.analysis?.speaker_analysis?.sarvam_voice_plan_speakers?.[0]?.selected_tts_voice },
                  { label: "Lip sync method", value: metric(result, "lipsync_method") },
                  { label: "Visual lip sync applied", value: metric(result, "lipsync_visual_sync_applied") },
                  { label: "Fallback used", value: analysisValue(result, "run_evidence", "fallback_used") ?? metric(result, "fallback_used") },
                  { label: "Generic fallback", value: analysisValue(result, "run_evidence", "generic_fallback_used") ?? metric(result, "generic_fallback_used") },
                ]}
              />

              <EvidencePanel
                title="Lip-sync evidence"
                icon={ScanLine}
                items={[
                  { label: "Status", value: (lipsyncEvidence.method ?? metric(result, "lipsync_method")) === "ffmpeg" ? "Audio replacement only - no mouth animation model applied." : "Visual lip-sync evidence from backend metrics." },
                  { label: "Mode", value: lipsyncEvidence.mode ?? metric(result, "lipsync_mode") },
                  { label: "Method", value: lipsyncEvidence.method ?? metric(result, "lipsync_method") },
                  { label: "Visual sync applied", value: lipsyncEvidence.visual_sync_applied ?? metric(result, "lipsync_visual_sync_applied") },
                  { label: "Visual sync requested", value: lipsyncEvidence.visual_sync_requested ?? metric(result, "visual_lipsync_requested") },
                  { label: "Fallback used", value: lipsyncEvidence.fallback_used ?? metric(result, "lipsync_fallback_used") },
                  { label: "Wav2Lip preflight", value: lipsyncEvidence.wav2lip_preflight_ok ?? metric(result, "wav2lip_preflight_ok") },
                  { label: "Wav2Lip Python", value: lipsyncEvidence.wav2lip_python ?? metric(result, "wav2lip_python") },
                  { label: "Checkpoint", value: lipsyncEvidence.checkpoint_exists ?? metric(result, "wav2lip_checkpoint_exists") },
                  { label: "Alignment level", value: lipsyncEvidence.alignment_level ?? metric(result, "alignment_level") },
                  { label: "LSE-C status", value: lipsyncEvidence.lse_c_status },
                  { label: "LSE-D status", value: lipsyncEvidence.lse_d_status },
                  { label: "Source video duration", value: lipsyncEvidence.source_video_duration_s ?? metric(result, "source_video_duration_s"), unit: "s" },
                  { label: "Generated audio duration", value: lipsyncEvidence.generated_audio_duration_s ?? metric(result, "tts_total_duration_s"), unit: "s" },
                  { label: "Prepared audio duration", value: lipsyncEvidence.prepared_audio_duration_s ?? metric(result, "prepared_audio_duration_s"), unit: "s" },
                  { label: "Final MP4 duration", value: lipsyncEvidence.final_mp4_duration_s ?? metric(result, "final_mp4_duration_s"), unit: "s" },
                  { label: "Duration delta", value: lipsyncEvidence.duration_delta_s ?? metric(result, "final_duration_delta_s"), unit: "s" },
                  { label: "Audio padded", value: lipsyncEvidence.audio_padded_sec ?? metric(result, "audio_padded_sec"), unit: "s" },
                  { label: "Audio trimmed", value: lipsyncEvidence.audio_trimmed_sec ?? metric(result, "audio_trimmed_sec"), unit: "s" },
                  { label: "Wav2Lip error", value: lipsyncEvidence.wav2lip_error ?? metric(result, "wav2lip_error") },
                ]}
              />

              <EvidencePanel
                title="Responsible AI & Provenance"
                icon={ShieldCheck}
                items={[
                  { label: "Mode", value: result.responsibleAI?.mode ?? "Compliance passport will appear for new runs." },
                  { label: "Passport status", value: result.responsibleAI?.passportStatus },
                  { label: "SGI risk level", value: result.responsibleAI?.sgiRiskLevel },
                  { label: "Synthetic voice used", value: result.responsibleAI?.syntheticVoiceUsed },
                  { label: "Speaker consent recorded", value: result.responsibleAI?.speakerConsentRecorded },
                  { label: "Visible disclosure", value: result.responsibleAI?.visibleDisclosureApplied },
                  { label: "Audio disclosure", value: result.responsibleAI?.audioDisclosureApplied },
                  { label: "Provenance manifest", value: result.responsibleAI?.provenanceManifestCreated },
                  { label: "Hashes generated", value: result.responsibleAI?.hashesGenerated },
                  { label: "Audit ledger", value: result.responsibleAI?.auditLedgerCreated },
                  { label: "Safe for demo/export", value: result.responsibleAI?.safeForDemoExport },
                  { label: "Warnings", value: result.responsibleAI?.warningsCount },
                  { label: "Errors", value: result.responsibleAI?.errorsCount },
                  { label: "Passport path", value: result.responsibleAI?.passportPath },
                  { label: "Provenance path", value: result.responsibleAI?.provenancePath },
                ]}
              />

              <EvidencePanel
                title="Translation integrity"
                icon={ShieldCheck}
                items={[
                  { label: "QA status", value: translationQA?.status ?? reportValue(result, "translation", "translation_qa_status") ?? metric(result, "translation_qa_status") },
                  { label: "Segment count match", value: reportValue(result, "translation", "segment_count_matches_source") },
                  { label: "Script check", value: translationQA?.scriptMatch ?? reportValue(result, "translation", "translation_qa_script_match") ?? metric(result, "translation_qa_script_match") },
                  { label: "Empty translations", value: translationQA?.emptySegments ?? reportValue(result, "translation", "translation_qa_empty_segments") ?? metric(result, "translation_qa_empty_segments") },
                  { label: "Number warnings", value: translationQA?.numberIssues ?? reportValue(result, "translation", "translation_qa_number_issues") ?? metric(result, "translation_qa_number_issues") },
                  { label: "Entity warnings", value: translationQA?.entityIssues ?? reportValue(result, "translation", "translation_qa_entity_issues") ?? metric(result, "translation_qa_entity_issues") },
                  { label: "Expansion warnings", value: translationQA?.expansionRatioWarnings ?? reportValue(result, "translation", "translation_qa_expansion_ratio_warnings") ?? metric(result, "translation_qa_expansion_ratio_warnings") },
                  { label: "Glossary applied", value: translationQA?.glossaryApplied },
                  { label: "Memory hits", value: translationQA?.translationMemoryHits },
                  { label: "Post-edit used", value: translationQA?.postEditUsed },
                  { label: "QA report", value: translationQA?.reportPath ?? reportValue(result, "translation", "translation_qa_report") ?? metric(result, "translation_qa_report_path") },
                ]}
              />

              <EvidencePanel
                title="Language integrity"
                icon={ScanLine}
                items={[
                  { label: "Status", value: linguisticIntegrity?.status ?? metric(result, "linguistic_integrity_status") },
                  { label: "Score", value: linguisticIntegrity?.score ?? metric(result, "linguistic_integrity_score") },
                  { label: "Severity", value: linguisticIntegrity?.severity },
                  { label: "Script status", value: linguisticIntegrity?.scriptStatus ?? metric(result, "linguistic_integrity_script_status") },
                  { label: "Empty segments", value: linguisticIntegrity?.emptySegments ?? metric(result, "linguistic_integrity_empty_segments") },
                  { label: "Number warnings", value: linguisticIntegrity?.numberWarnings ?? metric(result, "linguistic_integrity_number_warnings") },
                  { label: "Name warnings", value: linguisticIntegrity?.nameWarnings ?? metric(result, "linguistic_integrity_name_warnings") },
                  { label: "Expansion warnings", value: linguisticIntegrity?.expansionWarnings ?? metric(result, "linguistic_integrity_expansion_warnings") },
                  { label: "Report", value: linguisticIntegrity?.reportPath },
                ]}
              />

              <EvidencePanel
                title="Phonetic resolution"
                icon={Volume2}
                items={[
                  { label: "Status", value: phoneticResolution?.status ?? metric(result, "phonetic_resolution_status") },
                  { label: "Risk score", value: phoneticResolution?.phoneticRiskScore ?? metric(result, "phonetic_risk_score") },
                  { label: "Dictionary used", value: phoneticResolution?.dictionaryUsed ?? metric(result, "phonetic_dictionary_used") },
                  { label: "Terms detected", value: phoneticResolution?.termsDetected ?? metric(result, "phonetic_terms_detected") },
                  { label: "Acronyms detected", value: phoneticResolution?.acronymsDetected ?? metric(result, "phonetic_acronyms_detected") },
                  { label: "Ambiguity warnings", value: phoneticResolution?.ambiguityWarnings ?? metric(result, "phonetic_ambiguity_warnings") },
                  { label: "Report", value: phoneticResolution?.reportPath },
                ]}
              />

              <EvidencePanel
                title="Prosody & elocution summary"
                icon={Waves}
                items={[
                  { label: "Preset", value: prosodyElocution?.preset ?? metric(result, "prosody_preset") },
                  { label: "Speech rate class", value: prosodyElocution?.speechRateClass ?? reportValue(result, "prosody", "speech_rate_class") },
                  { label: "Average speech rate", value: prosodyElocution?.averageSpeechRateWpm ?? reportValue(result, "prosody", "average_speech_rate_wpm") ?? metric(result, "prosody_average_speech_rate_wpm") },
                  { label: "Pause count", value: prosodyElocution?.pauseCount ?? reportValue(result, "prosody", "pause_count") ?? metric(result, "prosody_pause_count") },
                  { label: "Pause preservation", value: reportValue(result, "prosody", "pause_preservation_proxy"), unit: "%" },
                  { label: "Duration drift", value: reportValue(result, "prosody", "duration_drift_sec") ?? metric(result, "tts_duration_delta_s"), unit: "s" },
                  { label: "Duration pressure", value: prosodyElocution?.durationPressure ?? reportValue(result, "prosody", "duration_pressure") ?? metric(result, "prosody_duration_pressure") },
                  { label: "HuBERT features computed", value: reportValue(result, "prosody", "hubert_features_computed") ?? metric(result, "hubert_features_computed") },
                  { label: "HuBERT status", value: prosodyElocution?.hubertStatus ?? reportValue(result, "prosody", "hubert_prosody_status") ?? metric(result, "hubert_prosody_status") ?? metric(result, "hubert_feature_status") },
                  { label: "HuBERT model", value: prosodyElocution?.hubertModel ?? reportValue(result, "prosody", "hubert_model") ?? metric(result, "hubert_model") },
                  { label: "HuBERT prosody similarity", value: prosodyElocution?.hubertProsodySimilarity ?? reportValue(result, "prosody", "hubert_prosody_similarity_score") ?? metric(result, "hubert_prosody_similarity_score") },
                  { label: "HuBERT embedding cosine", value: reportValue(result, "prosody", "hubert_embedding_cosine_similarity") ?? metric(result, "hubert_embedding_cosine_similarity") },
                  { label: "Adapter status", value: prosodyElocution?.adapterStatus ?? reportValue(result, "prosody", "hubert_adapter_status") ?? metric(result, "hubert_adapter_status") },
                  { label: "Adapter confidence", value: hubertAdapterConfidence },
                  { label: "Confusion matrix", value: reportValue(result, "prosody", "hubert_confusion_matrix_status") ?? metric(result, "hubert_confusion_matrix_status") ?? "Static artifact: TP 2, FP 2, TN 0, FN 0 from tiny project-pair matrix" },
                  { label: "Confidence note", value: hubertAdapterConfidence === "low" ? "Low confidence because the paired project dataset is small." : undefined },
                  { label: "Backend controls", value: "XTTS chunking/preset controls; Sarvam pace/temperature/speaker controls when selected" },
                ]}
              />

              {result.manifestSummary && (
                <EvidencePanel
                  title="Run manifest"
                  icon={FileJson}
                  items={[
                    { label: "Manifest status", value: result.manifestSummary.final_status },
                    { label: "Current stage", value: result.manifestSummary.current_stage },
                    { label: "Last checkpoint", value: result.manifestSummary.last_completed_stage },
                    { label: "Failure checkpoint", value: result.manifestSummary.failed_stage },
                    { label: "Translation backend", value: result.manifestSummary.selected_backends?.translation },
                    { label: "Voice backend", value: result.manifestSummary.selected_backends?.voice },
                    { label: "Recovery readiness", value: result.manifestSummary.resume_supported ? "resume execution available" : "metadata only" },
                    { label: "Recovery note", value: result.manifestSummary.retry_failed_stage_hint ?? result.manifestSummary.resume_command_hint },
                  ]}
                />
              )}

              <EvidencePanel
                title="Speaker analysis"
                icon={Mic2}
                items={[
                  { label: "Status", value: statusText(result.analysis?.speaker_analysis?.status) },
                  { label: "Speakers detected", value: ["computed", "defaulted"].includes(result.analysis?.speaker_analysis?.status ?? "") ? result.analysis?.speaker_analysis?.speakers_detected ?? result.analysis?.speaker_analysis?.speaker_count : undefined },
                  { label: "Labels available", value: result.analysis?.speaker_analysis?.speaker_labels?.length ? result.analysis.speaker_analysis.speaker_labels.join(", ") : undefined },
                  { label: "Unknown segments", value: result.analysis?.speaker_analysis?.unknown_segment_count },
                  { label: "Ambiguous segments", value: result.analysis?.speaker_analysis?.ambiguous_segment_count },
                  { label: "Reference candidates", value: result.analysis?.speaker_analysis?.speaker_reference_count },
                  { label: "Voice assignment", value: statusText(result.analysis?.speaker_analysis?.voice_assignment_status) },
                  { label: "Visual analysis", value: statusText(result.analysis?.speaker_analysis?.visual_analysis_status) },
                  { label: "Voice profile hint", value: result.analysis?.speaker_analysis?.sarvam_voice_plan_speakers?.[0]?.voice_profile_hint },
                  { label: "Sarvam selected voice", value: result.analysis?.speaker_analysis?.sarvam_voice_plan_speakers?.[0]?.selected_tts_voice },
                  { label: "Voice selection reason", value: result.analysis?.speaker_analysis?.sarvam_voice_plan_speakers?.[0]?.selection_reason },
                  { label: "Source", value: result.analysis?.speaker_analysis?.source },
                  { label: "Reason", value: result.analysis?.speaker_analysis?.reason },
                  { label: "Fix", value: result.analysis?.speaker_analysis?.recommended_fix },
                  { label: "Errors", value: result.analysis?.speaker_analysis?.errors?.join(" ") },
                  { label: "Warnings", value: result.analysis?.speaker_analysis?.warnings?.join(" ") },
                  { label: "Transcript segments", value: result.analysis?.speaker_analysis?.segment_count ?? metric(result, "asr_segments") },
                  { label: "Sarvam note", value: "Managed TTS voice selected per detected speaker profile when available. Not exact voice cloning." },
                  { label: "Profile labels", value: "Voice profile hint only: masculine voice fit, feminine voice fit, neutral, or unknown." },
                ]}
              />

              <EvidencePanel
                title="Reference audio"
                icon={FileAudio}
                items={[
                  { label: "Mode", value: analysisValue(result, "reference_audio", "mode") ?? storedJob?.referenceMode },
                  { label: "Auto-extract status", value: analysisValue(result, "reference_audio", "status") },
                  { label: "Validation", value: analysisValue(result, "reference_audio", "validation_passed") },
                  { label: "Duration", value: analysisValue(result, "reference_audio", "duration_sec"), unit: "s" },
                  { label: "Sample rate", value: analysisValue(result, "reference_audio", "sample_rate") },
                  { label: "Channels", value: analysisValue(result, "reference_audio", "channels") },
                  { label: "Peak", value: analysisValue(result, "reference_audio", "peak") },
                  { label: "Reason", value: analysisValue(result, "reference_audio", "reason") },
                ]}
              />

              <EvidencePanel
                title="Voice/audio analysis"
                icon={CheckCircle2}
                items={[
                  { label: "TTS WAV exists", value: reportValue(result, "voice_audio", "tts_wav_exists") ?? analysisValue(result, "audio_validation", "tts_wav_exists") },
                  { label: "TTS duration", value: reportValue(result, "voice_audio", "tts_duration_sec") ?? reportValue(result, "audio", "duration_sec") ?? metric(result, "tts_total_duration_s"), unit: "s" },
                  { label: "Sample rate", value: reportValue(result, "voice_audio", "sample_rate") ?? reportValue(result, "audio", "sample_rate") ?? metric(result, "tts_wav_sample_rate") },
                  { label: "Channels", value: reportValue(result, "voice_audio", "channels") ?? reportValue(result, "audio", "channels") },
                  { label: "Peak", value: reportValue(result, "voice_audio", "peak") ?? reportValue(result, "audio", "peak") ?? analysisValue(result, "audio_validation", "peak") },
                  { label: "RMS", value: reportValue(result, "voice_audio", "rms") ?? reportValue(result, "audio", "rms") },
                  { label: "Clipping ratio", value: reportValue(result, "voice_audio", "clipping_ratio") ?? reportValue(result, "audio", "clipping_ratio") },
                  { label: "Silence ratio", value: reportValue(result, "voice_audio", "silence_ratio") ?? reportValue(result, "audio", "silence_ratio") },
                  { label: "Normalization applied", value: reportValue(result, "voice_audio", "normalization_applied") ?? reportValue(result, "audio", "normalization_applied") ?? analysisValue(result, "audio_validation", "normalization_applied") },
                  { label: "Duration drift", value: reportValue(result, "voice_audio", "duration_drift_sec") ?? reportValue(result, "audio", "duration_drift_sec") ?? metric(result, "tts_duration_delta_s"), unit: "s" },
                ]}
              />

              <div className="border border-foreground/10 bg-foreground p-6 text-background">
                <ShieldCheck className="mb-5 size-7 text-background/65" />
                <h2 className="mb-3 font-display text-3xl">Voice backend note</h2>
                <p className="text-background/65">
                  XTTS is the speaker-reference route for supported global languages. Sarvam is managed Indian-language speech and should not be described as exact speaker cloning.
                </p>
              </div>
            </div>

            <div className="grid gap-6">
              <TestingAnalysisCards report={result.metricsReport} />

              {manifestArtifacts.length > 0 && (
                <div className="vl-panel">
                  <div className="mb-5 flex items-center gap-3">
                    <FileJson className="size-5 text-muted-foreground" />
                    <h3 className="font-display text-3xl">Artifacts written</h3>
                  </div>
                  <div className="grid gap-3">
                    {manifestArtifacts.map((artifact) => (
                      <div key={artifact.key} className="vl-metric-row">
                        <div>
                          <div className="vl-metric-label">{artifact.label}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{artifact.meta}</div>
                        </div>
                        <div className="vl-metric-value">{artifact.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.originalVideo && (
                <ResultVideoCard title="Original video" url={result.originalVideo} backend="Source upload" note="The original input is served from the job results folder when available." />
              )}
              {localizedVideos.map((video) => (
                <ResultVideoCard
                  key={`${video.language}-${video.url}`}
                  title={`${video.language} localized video`}
                  url={video.url}
                  backend={formatValue(metric(result, "voice_backend") ?? storedJob?.voiceLabel)}
                  note="Download and preview use the backend result file endpoint. No perceptual confidence score is currently measured."
                  captions={video.captions ?? result.captions ?? []}
                />
              ))}

              <EvidencePanel
                title="Output inspection"
                icon={FileVideo}
                items={[
                  { label: "Final MP4 count", value: metric(result, "final_mp4_count") },
                  { label: "Final MP4 exists", value: reportValue(result, "media_output", "final_mp4_exists") ?? reportValue(result, "media", "mp4_exists") ?? analysisValue(result, "output_inspection", "final_mp4_exists") },
                  { label: "Final MP4 size", value: metric(result, "final_mp4_size_mb"), unit: " MB" },
                  { label: "File size bytes", value: reportValue(result, "media_output", "file_size_bytes") ?? reportValue(result, "media", "size_bytes") ?? analysisValue(result, "output_inspection", "file_size_bytes") },
                  { label: "Final MP4 duration", value: reportValue(result, "media_output", "final_mp4_duration_sec") ?? reportValue(result, "media", "duration_sec") ?? analysisValue(result, "output_inspection", "duration_sec") ?? metric(result, "final_mp4_duration_s"), unit: "s" },
                  { label: "Video codec", value: reportValue(result, "media_output", "video_codec") ?? reportValue(result, "media", "video_codec") ?? analysisValue(result, "output_inspection", "video_codec") ?? metric(result, "video_codec") },
                  { label: "Resolution", value: reportValue(result, "media_output", "resolution") ?? reportValue(result, "media", "resolution") ?? analysisValue(result, "output_inspection", "resolution") ?? metric(result, "video_resolution") },
                  { label: "FPS", value: reportValue(result, "media_output", "fps") ?? reportValue(result, "media", "fps") ?? analysisValue(result, "output_inspection", "fps") ?? metric(result, "video_fps") },
                  { label: "Audio codec", value: reportValue(result, "media_output", "audio_codec") ?? reportValue(result, "media", "audio_codec") ?? analysisValue(result, "output_inspection", "audio_codec") ?? metric(result, "audio_codec") },
                  { label: "Audio sample rate", value: reportValue(result, "media_output", "audio_sample_rate") ?? reportValue(result, "media", "audio_sample_rate") ?? analysisValue(result, "output_inspection", "audio_sample_rate") ?? metric(result, "audio_sample_rate") },
                  { label: "Audio channels", value: reportValue(result, "media_output", "audio_channels") ?? reportValue(result, "media", "audio_channels") ?? analysisValue(result, "output_inspection", "audio_channels") ?? metric(result, "audio_channels") },
                  { label: "Video stream", value: reportValue(result, "media_output", "video_stream_present") ?? metric(result, "output_has_video_stream") },
                  { label: "Audio stream", value: reportValue(result, "media_output", "audio_stream_present") ?? metric(result, "output_has_audio_stream") },
                ]}
              />

              <EvidencePanel
                title="Transcript & translation analysis"
                icon={Info}
                items={[
                  { label: "ASR segments", value: reportValue(result, "transcript", "asr_segment_count") ?? metric(result, "asr_segments") },
                  { label: "Transcript words", value: reportValue(result, "transcript", "total_transcript_words") },
                  { label: "Transcript characters", value: reportValue(result, "transcript", "total_transcript_characters") },
                  { label: "Average segment duration", value: reportValue(result, "transcript", "average_segment_duration_sec"), unit: "s" },
                  { label: "Average words per segment", value: reportValue(result, "transcript", "average_words_per_segment") },
                  { label: "Detected source language", value: reportValue(result, "transcript", "detected_source_language") },
                  { label: "Speaker analysis", value: reportValue(result, "transcript", "speaker_analysis_status") ?? result.analysis?.speaker_analysis?.status },
                  { label: "Translated segments", value: reportValue(result, "translation", "translated_segment_count") },
                  { label: "Translated words", value: reportValue(result, "translation", "total_translated_words") },
                  { label: "Expansion ratio", value: reportValue(result, "translation", "expansion_ratio") },
                  { label: "Empty translated segments", value: reportValue(result, "translation", "empty_translation_segment_count") },
                  { label: "Suspiciously long segments", value: reportValue(result, "translation", "suspiciously_long_segment_count") },
                  { label: "Backend selected", value: reportValue(result, "translation", "backend_selected") },
                ]}
              />

              <details className="vl-panel">
                <summary className="cursor-pointer font-display text-3xl">Expert reference metrics</summary>
                <div className="mt-5 grid gap-3 text-sm">
                  {[
                    ["WER", result.metricsReport?.asr?.wer],
                    ["CER", result.metricsReport?.asr?.cer],
                    ["BLEU", result.metricsReport?.translation?.bleu],
                    ["chrF", result.metricsReport?.translation?.chrf],
                    ["LSE-C", result.metricsReport?.sync?.lse_c],
                    ["LSE-D", result.metricsReport?.sync?.lse_d],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="vl-metric-row">
                      <div className="vl-metric-label">{label as string}</div>
                      <div className="vl-metric-value text-muted-foreground">{metricResultText(value as { status?: string; value?: MetricValue; label?: string; reason?: string | null } | undefined)}</div>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          </div>
        ) : (
          <div className="mb-14 border border-foreground/10 bg-card p-8">
            <FileVideo className="mb-6 size-8 text-muted-foreground" />
            <h2 className="mb-3 font-display text-4xl">No completed backend job loaded yet</h2>
            <p className="mb-6 text-muted-foreground">Start a new upload, open a result link with a job id, or use the known-good proof output references below.</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild className="rounded-full">
                <Link href="/upload">
                  New localization run
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
              {activeJobId && (
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-full border-foreground/20"
                  onClick={() => {
                    clearRunState();
                    setError(null);
                    setStoredJob(null);
                  }}
                >
                  Clear old job state
                </Button>
              )}
            </div>
          </div>
        )}

        <div>
          <div className="mb-6">
            <h2 className="font-display text-4xl">Known-good proof artifacts</h2>
            <p className="mt-2 text-muted-foreground">These paths are protected and were not overwritten by the frontend revamp.</p>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            {proofOutputs.map((output) => (
              <div key={output.path} className="vl-panel-lg">
                <h3 className="mb-2 font-display text-3xl">{output.title}</h3>
                <div className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">{output.backend}</div>
                <p className="mb-4 text-muted-foreground">{output.note}</p>
                <p className="break-all font-mono text-xs text-muted-foreground">{output.path}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
