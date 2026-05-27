import Link from "next/link";
import { ArrowRight, FileAudio, FileJson, FileVideo, PackageCheck, PlaySquare, RadioTower } from "lucide-react";
import { Button } from "@/components/ui/button";

const tracks = [
  { label: "French", route: "XTTS speaker-reference", status: "proof artifact" },
  { label: "Kannada", route: "IndicTrans2 + Sarvam", status: "proof artifact" },
  { label: "Hindi", route: "Sarvam managed voice", status: "roadmap track" },
];

const outputs = [
  { label: "HLS master playlist", icon: RadioTower },
  { label: "Multi-audio MP4", icon: FileVideo },
  { label: "Export manifest", icon: FileJson },
];

export function OttDeliverySection() {
  return (
    <section className="px-6 py-24 lg:px-12">
      <div className="mx-auto max-w-[1400px]">
        <div className="mb-10 grid gap-8 lg:grid-cols-[0.85fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              OTT-style multilingual delivery
            </span>
            <h2 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">One source video. Multiple localized voice tracks.</h2>
          </div>
          <div className="max-w-2xl">
            <p className="text-lg leading-relaxed text-muted-foreground">
              Vidiolingua is moving beyond one dubbed MP4 per language into packaged delivery: selectable audio tracks, HLS manifests, MP4 track metadata, and backend evidence per language.
            </p>
            <Button asChild className="mt-6 rounded-full">
              <Link href="/multilingual-export">
                Open OTT export
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.8fr_1fr_0.8fr] lg:items-stretch">
          <div className="border border-foreground/10 bg-card p-6">
            <PlaySquare className="mb-8 size-8 text-muted-foreground" />
            <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">Source video</div>
            <h3 className="mt-2 font-display text-3xl">Original picture track</h3>
            <p className="mt-3 text-sm text-muted-foreground">One video rendition anchors every localized voice.</p>
          </div>

          <div className="border border-foreground/10 bg-card p-6">
            <div className="mb-5 flex items-center gap-3">
              <FileAudio className="size-6 text-muted-foreground" />
              <h3 className="font-display text-3xl">Selectable voices</h3>
            </div>
            <div className="grid gap-3">
              {tracks.map((track) => (
                <div key={track.label} className="grid gap-2 border border-foreground/10 p-4 sm:grid-cols-[0.3fr_1fr_0.36fr] sm:items-center">
                  <div className="font-display text-2xl">{track.label}</div>
                  <div className="text-sm text-muted-foreground">{track.route}</div>
                  <div className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">{track.status}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-foreground/10 bg-foreground p-6 text-background">
            <PackageCheck className="mb-8 size-8 text-background/65" />
            <h3 className="mb-4 font-display text-3xl">Packaged output</h3>
            <div className="grid gap-3 text-sm text-background/75">
              {outputs.map((output) => (
                <div key={output.label} className="flex items-center gap-3 border border-background/15 p-3">
                  <output.icon className="size-4" />
                  {output.label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
