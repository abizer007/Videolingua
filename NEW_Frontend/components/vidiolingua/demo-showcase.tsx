import Link from "next/link";
import { ArrowUpRight, CheckCircle2, Film } from "lucide-react";
import { Button } from "@/components/ui/button";

const demos = [
  {
    title: "French via XTTS",
    language: "fr",
    backend: "XTTS speaker-reference voice",
    path: "outputs\\french_official_test\\results\\Vidiolingua_Test_Official_dubbed_fr.mp4",
    note: "Known-good speaker-reference route with final MP4 audio and video streams.",
    accent: "from-cyan-500 to-blue-500",
  },
  {
    title: "Kannada via Sarvam",
    language: "kn",
    backend: "IndicTrans2 + Sarvam managed TTS",
    path: "outputs\\kannada_sarvam_practical_test_clipfix\\results\\Vidiolingua_Test_Official_dubbed_kn.mp4",
    note: "Known-good Indian-language route through IndicTrans2 and Sarvam managed speech.",
    accent: "from-emerald-500 to-green-500",
  },
];

export function DemoShowcase() {
  return (
    <section id="demos" className="py-24 lg:py-32">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-12">
        <div className="mb-14 grid gap-8 lg:grid-cols-[0.8fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Two proven demo paths
            </span>
            <h2 className="font-display text-4xl tracking-normal lg:text-6xl">Proof outputs, not promises.</h2>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            French and Kannada are protected known-good runs. New uploads write into separate job folders, so the demo artifacts stay intact while the live pipeline can be tested.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {demos.map((demo) => (
            <div key={demo.language} className="group overflow-hidden border border-foreground/10 bg-card">
              <div className={`h-2 bg-gradient-to-r ${demo.accent}`} />
              <div className="grid gap-8 p-7 md:grid-cols-[1fr_220px]">
                <div>
                  <div className="mb-5 flex items-center gap-3">
                    <Film className="size-5 text-muted-foreground" />
                    <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">{demo.language}</span>
                  </div>
                  <h3 className="mb-3 font-display text-4xl">{demo.title}</h3>
                  <p className="mb-5 text-muted-foreground">{demo.note}</p>
                  <div className="mb-5 inline-flex items-center gap-2 border border-foreground/10 px-3 py-2 text-sm">
                    <CheckCircle2 className="size-4" />
                    {demo.backend}
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">{demo.path}</p>
                </div>
                <div className="flex aspect-video items-center justify-center border border-foreground/10 bg-foreground/[0.03] md:aspect-auto">
                  <div className="text-center">
                    <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-full border border-foreground/10">
                      <Film className="size-7" />
                    </div>
                    <div className="font-mono text-xs text-muted-foreground">Final MP4 artifact</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10">
          <Button asChild variant="outline" className="rounded-full border-foreground/20">
            <Link href="/results">
              Open results page
              <ArrowUpRight className="size-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
