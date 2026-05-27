import Link from "next/link";
import { BrainCircuit, Cpu, Languages, Mic2, ShieldCheck, ShieldOff, Video, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BackendCard } from "@/components/vidiolingua/backend-card";
import { LanguageSupportSection } from "@/components/vidiolingua/language-support-section";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";

const cards = [
  {
    title: "XTTS",
    subtitle: "Global speaker-reference voice",
    body: "Primary voice backend for supported global languages. The UI requires reference audio for these jobs and labels the result as speaker-reference output.",
    icon: Mic2,
    accent: "from-cyan-500 to-blue-500",
    details: ["Supports French", "Uses reference audio", "Global-language route"],
  },
  {
    title: "IndicTrans2",
    subtitle: "Indian translation router",
    body: "Primary translation engine for supported Indic pairs. The validated path includes English to Kannada.",
    icon: Languages,
    accent: "from-violet-500 to-indigo-500",
    details: ["en -> kn validated", "No silent LLM fallback for supported pairs", "Frontend recommends future /api/capabilities"],
  },
  {
    title: "Translation QA",
    subtitle: "Context-preserving guardrails",
    body: "A post-translation integrity layer checks empty segments, scripts, numbers, glossary terms, entities, expansion ratios, and neighboring context.",
    icon: ShieldCheck,
    accent: "from-sky-500 to-teal-500",
    details: ["Does not train a new model", "Optional LLM post-edit is disabled by default", "Reports flow into job metadata"],
  },
  {
    title: "Sarvam AI",
    subtitle: "Managed Indian-language TTS",
    body: "Practical managed regional-language voice path for Hindi, Tamil, Bengali, Telugu, Kannada, Malayalam, Marathi, Gujarati, Punjabi, and Odia.",
    icon: Cpu,
    accent: "from-emerald-500 to-green-500",
    details: ["Not exact speaker cloning", "API key remains backend-only", "Used for Kannada practical output"],
  },
  {
    title: "HuBERT",
    subtitle: "Pretrained prosody representation",
    body: "Used as a frozen feature extractor for prosody similarity and delivery evidence. Vidiolingua trains only a lightweight adapter on top.",
    icon: BrainCircuit,
    accent: "from-sky-500 to-cyan-500",
    details: ["Not trained from scratch", "Adapter/calibrator is project-trained", "Does not replace XTTS or Sarvam"],
  },
  {
    title: "Prosody controls",
    subtitle: "Preset-guided delivery",
    body: "XTTS receives punctuation-aware chunking and safe generation controls; Sarvam receives bounded pace, temperature, and speaker controls.",
    icon: Waves,
    accent: "from-pink-500 to-rose-500",
    details: ["Rhythm and pause aware", "Duration guardrails", "No perfect emotion claim"],
  },
  {
    title: "IndicF5",
    subtitle: "Disabled / local experimental",
    body: "Scaffolding exists, but local execution is disabled because Windows load-only validation timed out and created memory risk.",
    icon: ShieldOff,
    accent: "from-amber-500 to-stone-500",
    details: ["Not active default", "Do not run local load", "Roadmap only"],
  },
  {
    title: "FFmpeg / Lipsync",
    subtitle: "Media output path",
    body: "After generated audio validation, the backend creates final localized MP4 outputs through the configured lipsync or mux path.",
    icon: Video,
    accent: "from-rose-500 to-orange-500",
    details: ["Final MP4", "Result file endpoint", "Protected known-good outputs preserved"],
  },
];

export default function BackendsPage() {
  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-12 grid gap-8 lg:grid-cols-[0.82fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Models and backends
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">The router is part of the product.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            VideoLingua shows the difference between speaker-reference voice, managed Indian-language speech, translation routing, and disabled local experiments before a user starts a run.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {cards.map((card) => (
            <BackendCard key={card.title} {...card} />
          ))}
        </div>
        <Button asChild className="mt-8 rounded-full">
          <Link href="/differentiators">Open differentiators</Link>
        </Button>
      </section>
      <LanguageSupportSection />
      <SiteFooter />
    </main>
  );
}
