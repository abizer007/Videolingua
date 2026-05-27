"use client";

import { useMemo, useState } from "react";
import { Ban, CheckCircle2, Cloud, FileAudio, FileVideo, GitBranch, Languages, LockKeyhole, Mic2, Server, ShieldCheck, Video, Wand2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

type NodeId =
  | "frontend"
  | "api"
  | "media"
  | "asr"
  | "translation"
  | "indictrans2"
  | "voice"
  | "xtts"
  | "sarvam"
  | "indicf5"
  | "validation"
  | "mux"
  | "result";

type DiagramNode = {
  id: NodeId;
  label: string;
  kicker: string;
  body: string;
  icon: LucideIcon;
  x: number;
  y: number;
  stats: string[];
  disabled?: boolean;
};

const nodes: DiagramNode[] = [
  {
    id: "frontend",
    label: "Next.js UI",
    kicker: "Upload and review",
    body: "Users choose a source video, target language, and optional XTTS reference audio. The browser never receives backend secrets.",
    icon: FileVideo,
    x: 10,
    y: 12,
    stats: ["Multipart upload", "Polling", "Result preview"],
  },
  {
    id: "api",
    label: "FastAPI",
    kicker: "Job orchestration",
    body: "The backend creates an isolated workspace, starts subprocess stages, and exposes status, files, measured metrics, and errors.",
    icon: Server,
    x: 32,
    y: 12,
    stats: ["Job id", "Stage history", "Result URLs"],
  },
  {
    id: "media",
    label: "Media prep",
    kicker: "Audio extraction",
    body: "The source video is copied into the job workspace and prepared for ASR, optional BGM handling, TTS, and muxing.",
    icon: FileAudio,
    x: 54,
    y: 12,
    stats: ["Source MP4", "Audio prep", "Job folders"],
  },
  {
    id: "asr",
    label: "ASR transcription",
    kicker: "Transcript evidence",
    body: "Speech is transcribed before translation or voice generation starts. Segment count, speaker count, and source-language hints are reported when available.",
    icon: ShieldCheck,
    x: 76,
    y: 12,
    stats: ["Segments", "Speakers", "Source language"],
  },
  {
    id: "translation",
    label: "Translation router",
    kicker: "Policy route",
    body: "The translation stage chooses an allowed backend for the language pair and writes translated segment JSON.",
    icon: GitBranch,
    x: 32,
    y: 36,
    stats: ["Route decision", "Target JSON", "Fallback visible"],
  },
  {
    id: "indictrans2",
    label: "IndicTrans2",
    kicker: "Indic pairs",
    body: "Supported Indic translation pairs, including English to Kannada, route through IndicTrans2 and fail clearly if the route is unavailable.",
    icon: Languages,
    x: 54,
    y: 36,
    stats: ["EN to KN", "Policy JSON", "No silent fallback"],
  },
  {
    id: "voice",
    label: "Voice router",
    kicker: "Backend split",
    body: "The voice router sends supported global speaker-reference jobs to XTTS and Indian regional managed speech to Sarvam.",
    icon: GitBranch,
    x: 76,
    y: 36,
    stats: ["XTTS", "Sarvam", "IndicF5 disabled"],
  },
  {
    id: "xtts",
    label: "XTTS",
    kicker: "Speaker-reference",
    body: "XTTS is the primary speaker-reference backend for supported global languages such as French. It requires usable reference audio for cloning-style jobs.",
    icon: Mic2,
    x: 31,
    y: 62,
    stats: ["Supported globals", "Reference audio", "Local model"],
  },
  {
    id: "sarvam",
    label: "Sarvam",
    kicker: "Managed Indian voice",
    body: "Sarvam is used for regional Indian-language speech such as Kannada. It is managed TTS and is not presented as exact voice cloning.",
    icon: Cloud,
    x: 54,
    y: 62,
    stats: ["Backend key only", "Managed TTS", "Not exact cloning"],
  },
  {
    id: "indicf5",
    label: "IndicF5",
    kicker: "Disabled experiment",
    body: "IndicF5 remains disabled/local experimental and must not be loaded or presented as active in the practical pipeline.",
    icon: Ban,
    x: 77,
    y: 62,
    stats: ["Disabled", "Local experimental", "No runtime load"],
    disabled: true,
  },
  {
    id: "validation",
    label: "Audio validation",
    kicker: "Cleanup and checks",
    body: "Generated audio is inspected and cleaned where the current backend supports it before it reaches the mux stage.",
    icon: CheckCircle2,
    x: 31,
    y: 84,
    stats: ["WAV duration", "Stream checks", "Failure visible"],
  },
  {
    id: "mux",
    label: "FFmpeg / mux",
    kicker: "Assembly",
    body: "The validated audio and source media path are assembled through the configured lipsync or FFmpeg mux path.",
    icon: Wand2,
    x: 54,
    y: 84,
    stats: ["Mux output", "Codec metadata", "Duration check"],
  },
  {
    id: "result",
    label: "Final MP4",
    kicker: "Delivery",
    body: "The localized MP4 is served from the backend result endpoint for browser preview and download.",
    icon: Video,
    x: 77,
    y: 84,
    stats: ["Preview", "Download", "Measured metadata"],
  },
];

const edges: Array<[NodeId, NodeId]> = [
  ["frontend", "api"],
  ["api", "media"],
  ["media", "asr"],
  ["asr", "translation"],
  ["translation", "indictrans2"],
  ["indictrans2", "voice"],
  ["voice", "xtts"],
  ["voice", "sarvam"],
  ["voice", "indicf5"],
  ["xtts", "validation"],
  ["sarvam", "validation"],
  ["validation", "mux"],
  ["mux", "result"],
];

function pathFor(from: DiagramNode, to: DiagramNode) {
  const dx = Math.abs(to.x - from.x);
  if (dx < 8) {
    const bend = from.y < to.y ? from.y + 8 : from.y - 8;
    return `M ${from.x} ${from.y} C ${from.x + 10} ${bend}, ${to.x - 10} ${to.y - 8}, ${to.x} ${to.y}`;
  }
  return `M ${from.x} ${from.y} C ${(from.x + to.x) / 2} ${from.y}, ${(from.x + to.x) / 2} ${to.y}, ${to.x} ${to.y}`;
}

export function InteractiveArchitectureDiagram() {
  const [activeId, setActiveId] = useState<NodeId>("voice");
  const activeNode = useMemo(() => nodes.find((node) => node.id === activeId) ?? nodes[0], [activeId]);
  const ActiveIcon = activeNode.icon;

  return (
    <section className="border border-foreground/10 bg-card">
      <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="relative overflow-auto border-b border-foreground/10 bg-background xl:border-b-0 xl:border-r">
          <div className="relative min-h-[720px] min-w-[980px]">
            <div
              className="absolute inset-0 opacity-[0.36]"
              style={{
                backgroundImage: "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
                backgroundSize: "72px 72px",
              }}
            />
            <svg className="pointer-events-none absolute inset-0 size-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <marker id="architecture-arrow" markerHeight="5" markerWidth="5" orient="auto" refX="4.2" refY="2.5">
                  <path d="M0,0 L5,2.5 L0,5 Z" fill="currentColor" />
                </marker>
              </defs>
              {edges.map(([from, to]) => {
                const fromNode = nodes.find((node) => node.id === from)!;
                const toNode = nodes.find((node) => node.id === to)!;
                const isActive = from === activeId || to === activeId;
                const disabledEdge = toNode.disabled;
                return (
                  <path
                    key={`${from}-${to}`}
                    d={pathFor(fromNode, toNode)}
                    fill="none"
                    markerEnd="url(#architecture-arrow)"
                    stroke="currentColor"
                    strokeWidth={isActive ? "0.34" : "0.18"}
                    className={disabledEdge ? "text-foreground/18" : isActive ? "text-foreground signal-route" : "text-foreground/26"}
                  />
                );
              })}
            </svg>

            {nodes.map((node) => {
              const Icon = node.icon;
              const selected = node.id === activeId;
              return (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => setActiveId(node.id)}
                  className={`absolute w-[172px] -translate-x-1/2 -translate-y-1/2 border bg-card p-4 text-left transition-all duration-300 hover:-translate-y-[54%] ${selected ? "border-foreground shadow-[0_18px_50px_rgba(2,6,23,0.12)]" : node.disabled ? "border-foreground/10 opacity-70 hover:border-foreground/25" : "border-foreground/10 hover:border-foreground/30"}`}
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                >
                  <div className="mb-4 flex items-center justify-between">
                    <Icon className={`size-5 ${selected ? "text-foreground" : "text-muted-foreground"}`} />
                    {selected ? <CheckCircle2 className="size-4 text-emerald-600" /> : <span className={`size-2 rounded-full ${node.disabled ? "bg-amber-500/50" : "bg-foreground/20"}`} />}
                  </div>
                  <div className="font-medium leading-tight">{node.label}</div>
                  <div className="mt-1 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-muted-foreground">{node.kicker}</div>
                </button>
              );
            })}
          </div>
        </div>

        <aside className="p-6 lg:p-8">
          <div className="mb-8 flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">Inspect node</span>
            <LockKeyhole className="size-5 text-muted-foreground" />
          </div>
          <ActiveIcon className="mb-8 size-9 text-muted-foreground" />
          <h2 className="font-display text-4xl leading-none">{activeNode.label}</h2>
          <p className="mt-5 leading-relaxed text-muted-foreground">{activeNode.body}</p>
          <div className="mt-8 grid gap-3">
            {activeNode.stats.map((stat) => (
              <div key={stat} className="border border-foreground/10 p-3 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {stat}
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
