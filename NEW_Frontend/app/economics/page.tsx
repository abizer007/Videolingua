import Link from "next/link";
import { ArrowRight, BadgeIndianRupee, BarChart3, CheckCircle2, Cpu, GitBranch, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";
import {
  evaluationMetricDefinitions,
  gpuPricing,
  managedVoicePricing,
  marketComparison,
  measuredRunEvidence,
  translationApiPricing,
  type SourceBackedValue,
} from "@/lib/cost-analysis-data";

const costFormula = ["media processing", "transcription", "translation", "voice generation", "validation", "human review"];

const backendEconomics = [
  {
    name: "XTTS",
    role: "Speaker-reference voice for supported global languages",
    costType: "Local compute/runtime",
    status: "Working",
    risk: "CPU path can be slow; CUDA optimization is future work.",
  },
  {
    name: "IndicTrans2",
    role: "Indic translation for supported pairs",
    costType: "Local GPU compute",
    status: "Working for en->kn",
    risk: "Model access and isolated environment dependencies need to stay stable.",
  },
  {
    name: "Sarvam",
    role: "Managed Indian-language TTS",
    costType: "API usage",
    status: "Working for Kannada",
    risk: "External API price, quota, and key availability.",
  },
  {
    name: "IndicF5",
    role: "Future self-hosted Indic reference-conditioned voice",
    costType: "Heavy GPU memory/runtime",
    status: "Disabled/local experimental",
    risk: "Local Windows load timeout; not used for normal runs.",
  },
  {
    name: "FFmpeg / mux",
    role: "Final media assembly",
    costType: "Local CPU/media processing",
    status: "Working",
    risk: "Requires validated audio and stream inspection before delivery.",
  },
];

const costDrivers = ["video duration", "target language count", "ASR runtime", "translation backend", "voice backend", "retries/failures", "output storage", "human review"];

const computedMetrics = [
  "stage timings",
  "segment counts",
  "translation expansion ratio",
  "audio peak/clipping/silence",
  "MP4 ffprobe metadata",
  "backend routing evidence",
  "validation status",
];

const referenceMetrics = [
  "WER/CER needs ground-truth transcript",
  "BLEU/chrF needs reference translation",
  "MOS needs human or evaluator rating",
  "LSE-C/LSE-D needs a lip-sync evaluator",
  "voice similarity needs speaker embeddings",
];

function SourceBadge({ item }: { item: SourceBackedValue }) {
  return (
    <div className="mt-4 flex flex-wrap gap-2 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">
      <span className="border border-foreground/10 px-2 py-1">{item.kind}</span>
      <span className="border border-foreground/10 px-2 py-1">Confidence: {item.confidence}</span>
      <span className="border border-foreground/10 px-2 py-1">Accessed {item.accessed}</span>
    </div>
  );
}

function EvidenceCard({ item }: { item: SourceBackedValue }) {
  return (
    <div className="border border-foreground/10 bg-card p-5">
      <div className="mb-2 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">{item.source}</div>
      <h3 className="font-display text-3xl">{item.label}</h3>
      <div className="mt-4 text-2xl">{item.value}</div>
      <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{item.note}</p>
      {item.url ? (
        <Link href={item.url} className="mt-4 inline-flex text-sm text-foreground underline underline-offset-4">
          Source
        </Link>
      ) : null}
      <SourceBadge item={item} />
    </div>
  );
}

function SectionIntro({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="mb-8 grid gap-5 lg:grid-cols-[0.7fr_1fr] lg:items-end">
      <div>
        <span className="mb-4 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
          <span className="h-px w-8 bg-foreground/30" />
          {eyebrow}
        </span>
        <h2 className="font-display text-4xl leading-tight lg:text-6xl">{title}</h2>
      </div>
      <p className="max-w-3xl text-lg leading-relaxed text-muted-foreground">{body}</p>
    </div>
  );
}

export default function EconomicsPage() {
  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-14 grid gap-8 lg:grid-cols-[0.78fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Economics and evaluation
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">Economics of real video localization.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            VideoLingua separates translation, voice generation, validation, and muxing so each backend decision has a cost and quality reason. Local models and managed APIs are used intentionally, with routing evidence kept visible.
          </p>
        </div>

        <div className="mb-16 border border-foreground/10 bg-card p-6">
          <div className="mb-6 flex items-center gap-3">
            <BarChart3 className="size-6 text-muted-foreground" />
            <h2 className="font-display text-4xl">Total localization cost</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            {costFormula.map((item, index) => (
              <div key={item} className="border border-foreground/10 p-4">
                <div className="mb-6 font-mono text-xs text-muted-foreground">{index === 0 ? "cost =" : "+"}</div>
                <div className="text-sm">{item}</div>
              </div>
            ))}
          </div>
        </div>

        <section className="mb-16">
          <SectionIntro
            eyebrow="Backend economics"
            title="The router is the cost model."
            body="The economics are not hidden behind a single black-box call. XTTS, IndicTrans2, Sarvam, disabled IndicF5 work, and FFmpeg each carry a different runtime, reliability, and validation profile."
          />
          <div className="grid gap-4 lg:grid-cols-5">
            {backendEconomics.map((backend) => (
              <div key={backend.name} className="border border-foreground/10 bg-card p-5">
                <h3 className="font-display text-3xl">{backend.name}</h3>
                <p className="mt-3 min-h-20 text-sm text-muted-foreground">{backend.role}</p>
                <div className="mt-5 grid gap-2 text-sm">
                  <div className="border border-foreground/10 p-2">{backend.costType}</div>
                  <div className="border border-foreground/10 p-2">{backend.status}</div>
                  <div className="border border-foreground/10 p-2 text-muted-foreground">{backend.risk}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-16">
          <SectionIntro
            eyebrow="POC vs MVP"
            title="From validated demo to reliable service."
            body="The current state proves feasibility with local environments and protected outputs. MVP economics add hosting, job queues, storage, monitoring, concurrency, support, compliance, and human review."
          />
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="border border-foreground/10 bg-card p-6">
              <Cpu className="mb-6 size-7 text-muted-foreground" />
              <h3 className="font-display text-4xl">POC / current state</h3>
              <div className="mt-5 grid gap-2 text-sm">
                {["local laptop and isolated local envs", "protected XTTS local backend", "IndicTrans2 local GPU env", "Sarvam managed API for Indian-language voice", "generated outputs stored locally", "focus: feasibility and validated demo"].map((item) => (
                  <div key={item} className="border border-foreground/10 p-3">{item}</div>
                ))}
              </div>
            </div>
            <div className="border border-foreground/10 bg-card p-6">
              <GitBranch className="mb-6 size-7 text-muted-foreground" />
              <h3 className="font-display text-4xl">MVP / scaled state</h3>
              <div className="mt-5 grid gap-2 text-sm">
                {["hosted backend API", "job queue and persistent storage", "monitoring and structured logs", "GPU/cloud workers only where needed", "optional managed voice APIs", "focus: reliability, concurrency, support, compliance"].map((item) => (
                  <div key={item} className="border border-foreground/10 p-3">{item}</div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mb-16">
          <SectionIntro
            eyebrow="Measured evidence"
            title="Validated outputs, not projected ROI."
            body="The page uses real VideoLingua artifacts where they exist: French XTTS and Kannada IndicTrans2 plus Sarvam outputs. These facts prove routing and media generation, not generic savings claims."
          />
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {measuredRunEvidence.map((item) => <EvidenceCard key={item.label} item={item} />)}
          </div>
        </section>

        <section className="mb-16">
          <SectionIntro
            eyebrow="External planning data"
            title="Source-backed assumptions stay labeled."
            body="Provider prices change by region, tier, and date. These cards are planning references and comparisons, not guaranteed quotes or measured VideoLingua costs."
          />
          <div className="grid gap-5 lg:grid-cols-3">
            {[...managedVoicePricing, ...translationApiPricing, ...gpuPricing, ...marketComparison].map((item) => <EvidenceCard key={`${item.source}-${item.label}`} item={item} />)}
          </div>
        </section>

        <section className="mb-16">
          <SectionIntro
            eyebrow="Cost drivers"
            title="What actually moves the number."
            body="The same 30-second demo and a one-hour batch have different economics because duration, route, retries, storage, and review load do the real work."
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {costDrivers.map((driver) => (
              <div key={driver} className="border border-foreground/10 bg-card p-4 text-sm">{driver}</div>
            ))}
          </div>
        </section>

        <section className="mb-16">
          <SectionIntro
            eyebrow="Evaluation framework"
            title="Automatic metrics first; expert metrics only when enabled."
            body="Normal users should not have to bring reference transcripts or MOS scores to run the product. VideoLingua computes automatic evaluation evidence and keeps reference-backed metrics clearly labeled."
          />
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="border border-foreground/10 bg-card p-6">
              <CheckCircle2 className="mb-6 size-7 text-muted-foreground" />
              <h3 className="font-display text-4xl">Computed automatically</h3>
              <div className="mt-5 grid gap-2 text-sm">
                {computedMetrics.map((item) => <div key={item} className="border border-foreground/10 p-3">{item}</div>)}
              </div>
            </div>
            <div className="border border-foreground/10 bg-card p-6">
              <ShieldCheck className="mb-6 size-7 text-muted-foreground" />
              <h3 className="font-display text-4xl">Requires reference or evaluator</h3>
              <div className="mt-5 grid gap-2 text-sm">
                {referenceMetrics.map((item) => <div key={item} className="border border-foreground/10 p-3">{item}</div>)}
              </div>
            </div>
          </div>
          <div className="mt-5 grid gap-5 lg:grid-cols-3">
            {evaluationMetricDefinitions.map((item) => <EvidenceCard key={item.label} item={item} />)}
          </div>
        </section>

        <section className="mb-16">
          <SectionIntro
            eyebrow="Guardrails"
            title="Cost-aware does not mean opaque."
            body="The product stays honest by refusing silent fallback, keeping secrets backend-only, validating audio before mux, and labeling Sarvam as managed speech rather than exact cloning."
          />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {["no silent fallback", "no generic TTS fallback", "audio validation before mux", "backend routing visible", "secrets backend-only", "Sarvam used where reliability matters", "IndicF5 disabled locally", "generated media ignored from Git"].map((item) => (
              <div key={item} className="border border-foreground/10 bg-card p-4 text-sm">{item}</div>
            ))}
          </div>
        </section>

        <section className="border border-foreground/10 bg-foreground p-6 text-background">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <BadgeIndianRupee className="mb-5 size-8 text-background/60" />
              <h2 className="font-display text-4xl">Cost-aware dubbing, ready to test.</h2>
              <p className="mt-3 max-w-3xl text-background/65">
                Start a run, inspect the backend route, then validate the resulting MP4 and metrics report without adding fake ROI or benchmark numbers.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild className="rounded-full bg-background text-foreground hover:bg-background/90">
                <Link href="/upload">Start a run <ArrowRight className="size-4" /></Link>
              </Button>
              <Button asChild variant="outline" className="rounded-full border-background/25 bg-transparent text-background hover:bg-background/10 hover:text-background">
                <Link href="/architecture">View architecture</Link>
              </Button>
              <Button asChild variant="outline" className="rounded-full border-background/25 bg-transparent text-background hover:bg-background/10 hover:text-background">
                <Link href="/results">View results</Link>
              </Button>
            </div>
          </div>
        </section>
      </section>
      <SiteFooter />
    </main>
  );
}
