"use client";

import { useEffect, useRef, useState } from "react";
import { FileVideo, Languages, Mic2, ShieldCheck, Wand2 } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Read the source",
    description: "The backend extracts audio, runs ASR, and keeps the transcript artifacts inside the job workspace.",
    icon: FileVideo,
  },
  {
    number: "02",
    title: "Route the words",
    description: "IndicTrans2 is selected for supported Indic pairs such as English to Kannada; unsupported paths do not get quietly guessed.",
    icon: Languages,
  },
  {
    number: "03",
    title: "Choose the voice path",
    description: "XTTS uses speaker reference audio where it is supported. Sarvam handles Indian-language managed speech without pretending to clone.",
    icon: Mic2,
  },
  {
    number: "04",
    title: "Check before mux",
    description: "Generated audio is validated before lipsync or FFmpeg muxing creates the localized MP4.",
    icon: ShieldCheck,
  },
];

export function WorkflowSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setIsVisible(true);
    }, { threshold: 0.1 });
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="workflow" ref={sectionRef} className="relative bg-foreground py-24 text-background lg:py-32">
      <div className="pointer-events-none absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "repeating-linear-gradient(-45deg, transparent, transparent 38px, currentColor 38px, currentColor 39px)" }} />
      <div className="relative z-10 mx-auto max-w-[1400px] px-6 lg:px-12">
        <div className="mb-16 lg:mb-24">
          <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-background/55">
            <span className="h-px w-8 bg-background/30" />
            From source video to localized MP4
          </span>
          <h2 className={`font-display text-4xl tracking-normal transition-all duration-700 lg:text-6xl ${isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}>
            A pipeline with receipts.
            <br />
            <span className="text-background/50">Each route is visible before the MP4 ships.</span>
          </h2>
        </div>

        <div className="grid gap-6 lg:grid-cols-4">
          {steps.map((step, index) => (
            <div key={step.number} className={`border border-background/10 p-6 transition-all duration-700 ${isVisible ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"}`} style={{ transitionDelay: `${index * 100}ms` }}>
              <div className="mb-10 flex items-center justify-between">
                <span className="font-mono text-sm text-background/45">{step.number}</span>
                <step.icon className="size-7 text-background/70" />
              </div>
              <h3 className="mb-4 font-display text-3xl">{step.title}</h3>
              <p className="leading-relaxed text-background/62">{step.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 border border-background/10 p-6">
          <div className="mb-4 flex items-center gap-3 font-mono text-sm text-background/50">
            <Wand2 className="size-4" />
            Pipeline stages
          </div>
          <div className="grid gap-3 text-sm text-background/70 md:grid-cols-7">
            {["Audio extraction", "ASR", "Translation", "Voice generation", "Audio validation", "Lipsync / mux", "Final MP4"].map((stage) => (
              <div key={stage} className="border border-background/10 px-3 py-4 text-center">{stage}</div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
