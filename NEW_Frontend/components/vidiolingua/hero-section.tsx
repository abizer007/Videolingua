"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LocalizationSignalVisual } from "@/components/vidiolingua/localization-signal-visual";

const marqueeItems = [
  { value: "Speaker-reference dubbing", label: "XTTS for supported global languages" },
  { value: "IndicTrans2 routing", label: "validated Indic translation paths" },
  { value: "Sarvam managed voice", label: "Indian-language speech, honestly labeled" },
  { value: "Validated audio", label: "checked before muxing" },
  { value: "Source video to MP4", label: "upload, route, synthesize, validate, mux" },
  { value: "No silent fallback", label: "routing failures stay visible" },
];

export function VideoLinguaHeroSection() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => setIsVisible(true), []);

  return (
    <section className="relative flex min-h-[94vh] flex-col justify-center overflow-hidden">
      <div className="pointer-events-none absolute bottom-0 -right-8 top-0 hidden w-[34%] opacity-45 lg:block xl:-right-14">
        <LocalizationSignalVisual />
      </div>
      <div className="pointer-events-none absolute inset-0 opacity-30">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={`h-${index}`} className="absolute left-0 right-0 h-px bg-foreground/10" style={{ top: `${12.5 * (index + 1)}%` }} />
        ))}
        {Array.from({ length: 12 }).map((_, index) => (
          <div key={`v-${index}`} className="absolute bottom-0 top-0 w-px bg-foreground/10" style={{ left: `${8.33 * (index + 1)}%` }} />
        ))}
      </div>

      <div className="relative z-10 mx-auto max-w-[1400px] px-6 py-32 lg:px-12 lg:py-40">
        <div className={`mb-8 transition-all duration-700 ${isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}>
          <span className="inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
            <span className="h-px w-8 bg-foreground/30" />
            Translation, voice, validation, delivery
          </span>
        </div>

        <h1 className={`max-w-5xl text-[clamp(3rem,7.4vw,6.8rem)] font-display leading-[0.96] tracking-normal transition-all duration-1000 ${isVisible ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"}`}>
          Video localization built for real dubbing workflows.
        </h1>

        <div className="mt-12 grid gap-10 lg:grid-cols-[minmax(0,0.95fr)_auto] lg:items-end">
          <p className={`max-w-2xl text-xl leading-relaxed text-muted-foreground lg:text-2xl transition-all duration-700 delay-200 ${isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}>
            VideoLingua takes a source video through ASR, translation routing, voice generation, validation, and muxing. XTTS handles supported speaker-reference dubbing; Sarvam handles managed Indian-language speech without pretending to clone.
          </p>
          <div className={`flex flex-col gap-4 sm:flex-row transition-all duration-700 delay-300 ${isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}>
            <Button asChild size="lg" className="h-14 rounded-full bg-foreground px-8 text-base text-background hover:bg-foreground/90">
              <Link href="/upload">
                Start a localization run
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="h-14 rounded-full border-foreground/20 bg-background/50 px-8 text-base">
              <Link href="/architecture">View architecture</Link>
            </Button>
            <Button asChild size="lg" variant="ghost" className="h-14 rounded-full px-6 text-base">
              <Link href="/results">
                <PlayCircle className="size-4" />
                Review proof outputs
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <div className={`pointer-events-none absolute bottom-16 left-0 right-0 overflow-hidden transition-all duration-700 delay-500 ${isVisible ? "opacity-100" : "opacity-0"}`}>
        <div className="marquee flex w-max min-w-max gap-14 whitespace-nowrap will-change-transform">
          {Array.from({ length: 2 }).map((_, index) => (
            <div key={index} className="flex min-w-max flex-none gap-14">
              {marqueeItems.map((stat) => (
                <div key={`${stat.value}-${index}`} className="flex min-w-max flex-none items-baseline gap-4">
                  <span className="font-display text-3xl leading-none lg:text-5xl">{stat.value}</span>
                  <span className="text-sm leading-none text-muted-foreground">{stat.label}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
