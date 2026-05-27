import { Ban, CheckCircle2, Cloud, FileVideo, Gauge, Languages, Mic2, PauseCircle, Server, ShieldCheck, SlidersHorizontal, Video, Waves } from "lucide-react";

const nodes = [
  { title: "Next.js frontend", body: "Upload, polling, results, and capability-aware language UX.", icon: FileVideo },
  { title: "FastAPI backend", body: "Creates per-job workspace and serves status/result files.", icon: Server },
  { title: "ASR stage", body: "Audio extraction and transcription before translation routing.", icon: ShieldCheck },
  { title: "Source prosody analysis", body: "Rhythm, pauses, speech rate, and energy are measured from source speech.", icon: Waves },
  { title: "HuBERT features", body: "A frozen pretrained HuBERT worker extracts speech representations when enabled.", icon: PauseCircle },
  { title: "Translation router", body: "IndicTrans2 for supported Indic pairs; unsupported routes stay explicit.", icon: Languages },
  { title: "Prosody adapter", body: "A lightweight project-trained adapter calibrates source-vs-dub delivery similarity.", icon: Gauge },
  { title: "Prosody guidance plan", body: "Translated segments receive pacing, pause, and punctuation-aware TTS hints.", icon: SlidersHorizontal },
  { title: "Translation QA", body: "Names, numbers, target script, glossary terms, expansion, and segment context are checked.", icon: CheckCircle2 },
  { title: "Voice router", body: "XTTS for supported global speaker-reference voice; Sarvam for managed Indian TTS.", icon: Mic2 },
  { title: "TTS controls", body: "XTTS chunking and Sarvam pace/temperature controls stay guarded by preset limits.", icon: SlidersHorizontal },
  { title: "Sarvam split", body: "Regional voice uses backend-only Sarvam managed speech, not exact cloning.", icon: Cloud },
  { title: "IndicF5 disabled", body: "Local IndicF5 remains experimental and is not loaded by the practical route.", icon: Ban },
  { title: "Validation", body: "Generated audio and final streams are inspected before result delivery.", icon: CheckCircle2 },
  { title: "Mux and results", body: "Validated audio becomes final localized MP4 through lipsync or FFmpeg.", icon: Video },
];

export function ArchitectureFlow() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
      {nodes.map((node, index) => (
        <div key={node.title} className="relative border border-foreground/10 bg-card p-5">
          <div className="mb-8 flex items-center justify-between">
            <node.icon className="size-6 text-muted-foreground" />
            <span className="font-mono text-xs text-muted-foreground">{String(index + 1).padStart(2, "0")}</span>
          </div>
          <h3 className="mb-3 font-display text-2xl">{node.title}</h3>
          <p className="text-sm leading-relaxed text-muted-foreground">{node.body}</p>
        </div>
      ))}
    </div>
  );
}
