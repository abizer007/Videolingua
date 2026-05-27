"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Clapperboard, Cloud, ExternalLink, FileAudio, FileJson, FileVideo, GitBranch, Languages, PackageCheck, PlaySquare, RadioTower, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";
import { API_BASE_URL, createMultilingualExport, getMultilingualExport } from "@/lib/api";
import type { MultilingualExportResponse } from "@/lib/types";

const proofPayload = {
  exportId: "official_fr_kn_test",
  sourceVideo: "Vidiolingua_Test_Official.mp4",
  createHls: true,
  createMp4: true,
  tracks: [
    {
      language: "fr",
      audioPath: "outputs\\french_official_test\\tts\\output\\Vidiolingua_Test_Official_transcription_fr.wav",
    },
    {
      language: "kn",
      audioPath: "outputs\\kannada_sarvam_practical_test_clipfix\\tts\\output\\Vidiolingua_Test_Official_transcription_kn.wav",
    },
  ],
};

const trackConcept = [
  { language: "French", route: "XTTS speaker-reference", tone: "Reference-conditioned global route" },
  { language: "Kannada", route: "IndicTrans2 + Sarvam", tone: "Managed Indian-language TTS" },
  { language: "Hindi", route: "IndicTrans2 + Sarvam", tone: "Roadmap track for batch packaging" },
];

const roadmap = [
  "hls.js preview player",
  "subtitles and captions",
  "CDN/object storage packaging",
  "multi-language batch generation",
  "provenance per language track",
];

function fullUrl(path?: string | null) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE_URL}${path}`;
}

function statusLabel(value?: string | null) {
  return value ? value.replaceAll("_", " ") : "pending";
}

export default function MultilingualExportPage() {
  const [exportData, setExportData] = useState<MultilingualExportResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "creating" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMultilingualExport(proofPayload.exportId)
      .then((data) => {
        setExportData(data);
        setStatus("ready");
      })
      .catch(() => {
        setStatus("idle");
      });
  }, []);

  const artifactLinks = useMemo(() => {
    const links = exportData?.links ?? {};
    return [
      { title: "HLS master playlist", href: fullUrl(links.hlsMaster), icon: RadioTower, detail: exportData?.manifest.exports?.hls_master },
      { title: "Multi-audio MP4", href: fullUrl(links.multiAudioMp4), icon: FileVideo, detail: exportData?.manifest.exports?.multi_audio_mp4 },
      { title: "multilingual_manifest.json", href: fullUrl(links.manifest), icon: FileJson, detail: "metadata\\multilingual_manifest.json" },
      { title: "validation_report.json", href: fullUrl(links.validationReport), icon: CheckCircle2, detail: "metadata\\validation_report.json" },
    ];
  }, [exportData]);

  async function createProofExport() {
    setStatus("creating");
    setError(null);
    try {
      const data = await createMultilingualExport(proofPayload);
      setExportData(data);
      setStatus("ready");
    } catch (createError) {
      setStatus("error");
      setError(createError instanceof Error ? createError.message : "Could not create the proof export.");
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="grid gap-10 lg:grid-cols-[0.84fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              OTT-style multilingual delivery
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">One source video. Multiple localized voice tracks.</h1>
          </div>
          <div className="max-w-2xl">
            <p className="text-lg leading-relaxed text-muted-foreground">
              Package existing French, Kannada, Hindi, and other localized voices as selectable audio tracks for HLS delivery, multi-audio MP4s, and manifest-backed backend evidence.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button onClick={createProofExport} disabled={status === "creating"} className="rounded-full">
                <PackageCheck className="size-4" />
                {status === "creating" ? "Creating export" : exportData ? "Refresh proof export" : "Create proof export"}
              </Button>
              <Button asChild variant="outline" className="rounded-full border-foreground/20">
                <Link href="/architecture">
                  View architecture
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="border border-foreground/10 bg-card p-6">
            <div className="mb-6 flex items-center gap-3">
              <Clapperboard className="size-6 text-muted-foreground" />
              <h2 className="font-display text-4xl">Selectable audio concept</h2>
            </div>
            <div className="grid gap-4">
              <div className="border border-foreground/10 p-4">
                <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">Source video</div>
                <div className="mt-2 flex items-center gap-3 text-lg">
                  <PlaySquare className="size-5 text-muted-foreground" />
                  Vidiolingua_Test_Official.mp4
                </div>
              </div>
              {trackConcept.map((track) => (
                <div key={track.language} className="grid gap-3 border border-foreground/10 p-4 sm:grid-cols-[0.35fr_1fr] sm:items-center">
                  <div className="flex items-center gap-3">
                    <FileAudio className="size-5 text-muted-foreground" />
                    <span className="font-display text-2xl">{track.language}</span>
                  </div>
                  <div>
                    <div className="text-sm">{track.route}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{track.tone}</div>
                  </div>
                </div>
              ))}
              <div className="grid gap-3 border border-foreground/10 bg-foreground p-4 text-background sm:grid-cols-3">
                <div>HLS master playlist</div>
                <div>Multi-audio MP4</div>
                <div>Export manifest</div>
              </div>
            </div>
          </div>

          <div className="border border-foreground/10 bg-card p-6">
            <div className="mb-6 flex items-center gap-3">
              <ShieldCheck className="size-6 text-muted-foreground" />
              <h2 className="font-display text-4xl">Proof export</h2>
            </div>
            <div className="grid gap-3 text-sm">
              <div className="border border-foreground/10 p-3">Status: {status === "ready" ? "Generated" : status === "idle" ? "Ready to create from existing artifacts" : statusLabel(status)}</div>
              <div className="border border-foreground/10 p-3">Source: {proofPayload.sourceVideo}</div>
              <div className="border border-foreground/10 p-3">French WAV: protected XTTS proof output</div>
              <div className="border border-foreground/10 p-3">Kannada WAV: protected IndicTrans2 + Sarvam proof output</div>
            </div>
            {error && <div className="mt-4 border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>}
            <p className="mt-4 text-sm text-muted-foreground">
              This export packages existing artifacts only. It does not rerun ASR, translation, TTS, lip-sync, or model loading.
            </p>
          </div>
        </div>

        <div className="mt-12">
          <div className="mb-6 flex items-end justify-between gap-6">
            <div>
              <h2 className="font-display text-4xl">Export artifacts</h2>
              <p className="mt-2 text-muted-foreground">Use a compatible HLS player or media player that supports alternate audio tracks.</p>
            </div>
          </div>
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {artifactLinks.map((artifact) => (
              <div key={artifact.title} className="border border-foreground/10 bg-card p-5">
                <artifact.icon className="mb-6 size-7 text-muted-foreground" />
                <h3 className="mb-2 font-display text-2xl">{artifact.title}</h3>
                <p className="mb-4 break-all text-xs text-muted-foreground">{artifact.detail ?? "Generated after proof export runs."}</p>
                {artifact.href ? (
                  <Button asChild variant="outline" size="sm" className="rounded-full border-foreground/20">
                    <a href={artifact.href}>
                      Open
                      <ExternalLink className="size-4" />
                    </a>
                  </Button>
                ) : (
                  <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">Not generated yet</div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 border border-foreground/10 bg-card p-6">
          <div className="mb-6 flex items-center gap-3">
            <GitBranch className="size-6 text-muted-foreground" />
            <h2 className="font-display text-4xl">Backend evidence per track</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-foreground/10 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">
                  <th className="py-3 pr-4">Language</th>
                  <th className="py-3 pr-4">Translation</th>
                  <th className="py-3 pr-4">Voice backend</th>
                  <th className="py-3 pr-4">Voice mode</th>
                  <th className="py-3 pr-4">Exact clone</th>
                  <th className="py-3">Validation</th>
                </tr>
              </thead>
              <tbody>
                {(exportData?.manifest.languages ?? [
                  { language: "fr", display_name: "French", translation_backend: "google", voice_backend: "xtts", voice_mode: "speaker-reference voice", is_exact_clone: false, validation_status: "proof artifact available" },
                  { language: "kn", display_name: "Kannada", translation_backend: "indictrans2", voice_backend: "sarvam", voice_mode: "managed-indian-tts", is_exact_clone: false, validation_status: "proof artifact available" },
                ]).map((track) => (
                  <tr key={track.language} className="border-b border-foreground/10">
                    <td className="py-4 pr-4">{track.display_name}</td>
                    <td className="py-4 pr-4">{track.translation_backend}</td>
                    <td className="py-4 pr-4">{track.voice_backend}</td>
                    <td className="py-4 pr-4">{track.voice_mode}</td>
                    <td className="py-4 pr-4">{track.is_exact_clone ? "true" : "false"}</td>
                    <td className="py-4">{statusLabel(track.validation_status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-[0.8fr_1fr]">
          <div className="border border-foreground/10 bg-foreground p-7 text-background">
            <Cloud className="mb-6 size-8 text-background/65" />
            <h2 className="mb-3 font-display text-4xl">Delivery layer, not generation batch.</h2>
            <p className="text-background/65">
              This phase packages completed language runs first. Generating many languages in one request remains a separate orchestration roadmap item.
            </p>
          </div>
          <div className="border border-foreground/10 bg-card p-6">
            <div className="mb-5 flex items-center gap-3">
              <Languages className="size-6 text-muted-foreground" />
              <h2 className="font-display text-4xl">Roadmap</h2>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {roadmap.map((item) => (
                <div key={item} className="border border-foreground/10 p-3 text-sm">{item}</div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
