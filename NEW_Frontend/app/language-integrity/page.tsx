import Link from "next/link";
import { AlertTriangle, ArrowRight, BadgeCheck, BookOpenCheck, Braces, FileJson, GitBranch, Mic2, ScanLine, ShieldCheck, SpellCheck2, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";

const linguisticChecks = [
  "Script ratio and English leakage",
  "Empty translated segment detection",
  "Repeated translations and repeated punctuation",
  "Too-short and too-long segment ratios",
  "Sentence-boundary punctuation preservation",
  "Digits, percentages, dates, and currency checks",
  "Names, acronyms, and project term preservation",
  "Segment count, ordering, split, and merge integrity",
];

const phoneticChecks = [
  "Pronunciation dictionary for protected terms",
  "Acronym expansion for TTS-only text",
  "Proper noun and romanized-name protection",
  "Number/date ambiguity warnings",
  "English homophone risk notes",
  "XTTS-safe chunk preparation",
  "Sarvam-safe Indian-script preservation",
  "Display text and TTS-prepared text kept separate",
];

const flow = [
  "Translation output",
  "Linguistic integrity engine",
  "Phonetic resolver",
  "TTS text preparation",
  "XTTS / Sarvam",
  "Audio validation",
];

export default function LanguageIntegrityPage() {
  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-12 grid gap-8 lg:grid-cols-[0.78fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Language Integrity
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">Language integrity before the voice is generated.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Vidiolingua checks translated segments for script, names, numbers, segment alignment, expansion pressure, and pronunciation risk before speech synthesis. It is a validation and preparation layer around translation and TTS, not a claim of perfect grammar or perfect pronunciation.
          </p>
        </div>

        <div className="mb-12 grid gap-5 md:grid-cols-3">
          {[
            { label: "Computed score", value: "0-100", body: "Integrity severity is derived from actual errors, warnings, and affected segments.", icon: BadgeCheck },
            { label: "Canonical text preserved", value: "2 tracks", body: "Display text stays intact while TTS-safe text can carry pronunciation transformations.", icon: Braces },
            { label: "Job artifacts", value: "JSON proof", body: "Reports are registered in the manifest and surfaced through result metadata.", icon: FileJson },
          ].map((item) => (
            <div key={item.label} className="border border-foreground/10 bg-card p-6">
              <item.icon className="mb-8 size-7 text-muted-foreground" />
              <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">{item.label}</div>
              <div className="mt-2 font-display text-5xl">{item.value}</div>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>

        <div className="mb-12 border border-foreground/10 bg-foreground p-8 text-background">
          <div className="grid gap-8 lg:grid-cols-[0.7fr_1fr] lg:items-center">
            <div>
              <AlertTriangle className="mb-6 size-8 text-background/65" />
              <h2 className="font-display text-5xl leading-none">Small text failures create visible dubbing failures.</h2>
            </div>
            <div className="grid gap-3 text-sm text-background/70 sm:grid-cols-2">
              {["Names and numbers break trust when changed.", "Wrong script makes regional output unusable.", "Bad acronym pronunciation makes AI speech obvious.", "Segment expansion creates timing pressure for dubbing."].map((item) => (
                <div key={item} className="border border-background/15 p-4">{item}</div>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-12 grid gap-6 lg:grid-cols-2">
          <div className="border border-foreground/10 bg-card p-7">
            <div className="mb-6 flex items-center gap-3">
              <SpellCheck2 className="size-6 text-muted-foreground" />
              <h2 className="font-display text-4xl">Grammar and linguistic integrity engine</h2>
            </div>
            <p className="mb-6 leading-relaxed text-muted-foreground">
              The engine evaluates translated segments with localization QA checks: Kannada script ratio, Devanagari and other Indic script ratios, Latin leakage, missing translations, punctuation drift, names, numbers, and expansion pressure.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {linguisticChecks.map((check) => (
                <div key={check} className="border border-foreground/10 p-3 text-sm">
                  <ShieldCheck className="mb-3 size-4 text-muted-foreground" />
                  {check}
                </div>
              ))}
            </div>
          </div>

          <div className="border border-foreground/10 bg-card p-7">
            <div className="mb-6 flex items-center gap-3">
              <Volume2 className="size-6 text-muted-foreground" />
              <h2 className="font-display text-4xl">Phonetic and ambiguity resolution layer</h2>
            </div>
            <p className="mb-6 leading-relaxed text-muted-foreground">
              Before TTS, Vidiolingua can apply safe pronunciation dictionary replacements and acronym expansion to a separate prepared-text field while preserving the translated display text for transcript and review.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {phoneticChecks.map((check) => (
                <div key={check} className="border border-foreground/10 p-3 text-sm">
                  <Mic2 className="mb-3 size-4 text-muted-foreground" />
                  {check}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-12 border border-foreground/10 bg-card p-7">
          <div className="mb-7 flex items-center gap-3">
            <GitBranch className="size-6 text-muted-foreground" />
            <h2 className="font-display text-4xl">Pipeline position</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-6">
            {flow.map((stage, index) => (
              <div key={stage} className="relative border border-foreground/10 p-4">
                <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">0{index + 1}</div>
                <div className="mt-3 min-h-12 font-display text-2xl leading-none">{stage}</div>
                {index < flow.length - 1 && <ArrowRight className="absolute right-3 top-3 hidden size-4 text-muted-foreground md:block" />}
              </div>
            ))}
          </div>
        </div>

        <div className="mb-12 grid gap-6 lg:grid-cols-[0.72fr_1fr]">
          <div className="border border-foreground/10 bg-card p-7">
            <ScanLine className="mb-6 size-7 text-muted-foreground" />
            <h2 className="mb-4 font-display text-4xl">Real output evidence</h2>
            <div className="grid gap-3 text-sm">
              <div className="border border-foreground/10 p-3">Kannada linguistic report: <span className="font-mono">outputs\validation\linguistic_integrity_kn_report.json</span></div>
              <div className="border border-foreground/10 p-3">Kannada phonetic report: <span className="font-mono">outputs\validation\phonetic_resolution_kn_report.json</span></div>
              <div className="border border-foreground/10 p-3">Per-job reports: <span className="font-mono">translation\linguistic_integrity_report.json</span> and <span className="font-mono">tts\phonetic_resolution_report.json</span></div>
            </div>
          </div>
          <div className="border border-foreground/10 bg-card p-7">
            <BookOpenCheck className="mb-6 size-7 text-muted-foreground" />
            <h2 className="mb-4 font-display text-4xl">Backend artifacts</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {["linguistic_integrity_report.json", "phonetic_resolution_report.json", "job_manifest.json artifact map", "pipeline_result.json summaries", "metrics_report.json reflection", "API job status metadata"].map((item) => (
                <div key={item} className="border border-foreground/10 p-3 text-sm">{item}</div>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-12 border border-foreground/10 bg-card p-7">
          <FileJson className="mb-6 size-7 text-muted-foreground" />
          <div className="grid gap-6 lg:grid-cols-[0.45fr_1fr] lg:items-start">
            <div>
              <h2 className="mb-4 font-display text-4xl">Roadmap</h2>
              <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
                The validation layer stays additive while these review and pronunciation workflows mature.
              </p>
            </div>
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              {["Stronger NER and transliteration-aware preservation.", "Glossary editor UI and pronunciation dictionary management.", "COMET/QE translation quality estimator.", "SSML and phoneme support where a TTS backend supports it.", "Pronunciation feedback loop after generated audio.", "Human review queue for failed integrity gates."].map((item) => (
                <div key={item} className="border border-foreground/10 p-3">{item}</div>
              ))}
            </div>
          </div>
        </div>

        <div className="border border-foreground/10 bg-foreground p-8 text-background">
          <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <h2 className="mb-3 font-display text-5xl">A deeper checkpoint before speech.</h2>
              <p className="max-w-3xl text-background/65">Language Integrity makes Vidiolingua’s translation-to-voice path inspectable, auditable, and honest about what was validated.</p>
            </div>
            <Button asChild size="lg" className="h-14 rounded-full bg-background px-8 text-base text-foreground hover:bg-background/90">
              <Link href="/architecture">
                View architecture
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
