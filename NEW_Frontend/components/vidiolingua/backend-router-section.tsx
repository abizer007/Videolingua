import { Cpu, Languages, Mic2, ShieldOff, Video } from "lucide-react";

const backends = [
  { name: "XTTS", label: "Global speaker-reference voice", body: "Used where a reference voice is supported, including the protected French proof output.", icon: Mic2, accent: "from-cyan-500 to-blue-500" },
  { name: "IndicTrans2", label: "Indic translation routing", body: "The validated route for supported Indic pairs, including English to Kannada.", icon: Languages, accent: "from-violet-500 to-indigo-500" },
  { name: "Sarvam AI", label: "Managed Indian-language TTS", body: "Natural regional-language speech for Hindi, Kannada, Tamil, Telugu, and more. Not exact voice cloning.", icon: Cpu, accent: "from-emerald-500 to-green-500" },
  { name: "IndicF5", label: "Disabled local experiment", body: "Scaffolding remains in the repo, but local execution stays off due to Windows memory and load risk.", icon: ShieldOff, accent: "from-amber-500 to-stone-500" },
  { name: "FFmpeg / Lipsync", label: "Media output path", body: "Validated generated audio is muxed into final localized MP4 files.", icon: Video, accent: "from-rose-500 to-orange-500" },
];

export function BackendRouterSection() {
  return (
    <section className="py-24 lg:py-32">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-12">
        <div className="mb-14">
          <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
            <span className="h-px w-8 bg-foreground/30" />
            Voice backend router
          </span>
          <h2 className="max-w-4xl font-display text-4xl tracking-normal lg:text-6xl">
            The backend choice is visible before the job runs.
          </h2>
        </div>

        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-5">
          {backends.map((backend) => (
            <div key={backend.name} className="group border border-foreground/10 bg-card p-5 transition-all duration-300 hover:-translate-y-1 hover:border-foreground/25">
              <div className={`mb-8 flex size-12 items-center justify-center bg-gradient-to-br ${backend.accent} text-white`}>
                <backend.icon className="size-6" />
              </div>
              <h3 className="mb-2 font-display text-3xl">{backend.name}</h3>
              <div className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">{backend.label}</div>
              <p className="text-sm leading-relaxed text-muted-foreground">{backend.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
