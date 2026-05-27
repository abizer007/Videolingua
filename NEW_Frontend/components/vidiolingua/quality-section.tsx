import Link from "next/link";
import { ArrowRight, LockKeyhole, RadioTower, ScanLine, ShieldCheck, Volume2, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";

const items = [
  { label: "Backend-only secrets", body: "Sarvam API keys stay in backend env files and never appear in frontend variables.", icon: LockKeyhole },
  { label: "Visible failures", body: "Routing problems stay visible instead of being hidden behind a generic voice path.", icon: ShieldCheck },
  { label: "Translation integrity", body: "Names, numbers, scripts, expansion ratios, and neighboring segment context are checked after translation.", icon: ScanLine },
  { label: "Phonetic preparation", body: "Acronyms and protected terms can be prepared for TTS without overwriting canonical translated text.", icon: Volume2 },
  { label: "HuBERT-guided prosody", body: "Extracts rhythm, pauses, energy, and HuBERT speech representations, then guides pacing and delivery controls.", icon: Waves },
  { label: "Intentional hybrid", body: "Local XTTS and IndicTrans2 sit beside managed Sarvam where managed Indian-language speech is the right tool.", icon: RadioTower },
];

export function QualitySection() {
  return (
    <section className="py-24 lg:py-32">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-12">
        <div className="mb-14">
          <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
            <span className="h-px w-8 bg-foreground/30" />
            Quality and validation
          </span>
          <h2 className="max-w-4xl font-display text-4xl tracking-normal lg:text-6xl">Built so the demo can be inspected, not just admired.</h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div key={item.label} className="border border-foreground/10 p-6">
              <item.icon className="mb-8 size-7 text-muted-foreground" />
              <h3 className="mb-3 font-display text-3xl">{item.label}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>
        <Button asChild variant="outline" className="mt-6 rounded-full border-foreground/20">
          <Link href="/language-integrity">
            Open language integrity
            <ArrowRight className="size-4" />
          </Link>
        </Button>
        <Button asChild className="ml-3 mt-6 rounded-full">
          <Link href="/differentiators">
            Open differentiators
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}
