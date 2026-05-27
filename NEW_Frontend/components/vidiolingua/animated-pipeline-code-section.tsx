"use client";

import { useEffect, useRef, useState } from "react";

const steps = [
  {
    number: "I",
    title: "Create the run",
    description: "The UI sends only the source video, selected languages, source hint, and voice options. Secrets stay behind FastAPI.",
    file: "upload_contract.ts",
    status: "upload accepted",
    code: `const form = new FormData()
form.append("video", sourceVideo)
form.append("languages", JSON.stringify(["kn"]))
form.append("sourceLanguage", "en")
form.append("voiceOptions", JSON.stringify({
  cloned: false,
  mode: "managed",
  backendHint: "sarvam"
}))`,
  },
  {
    number: "II",
    title: "Route the pipeline",
    description: "FastAPI moves the job through ASR, translation, voice, validation, and muxing with visible stage history.",
    file: "pipeline_runner.py",
    status: "routing live",
    code: `job.stage("asr")
transcript = whisperx.transcribe(video)

job.stage("translation")
translation = indictrans2.route(
  source="en",
  target="kn",
  segments=transcript.segments
)`,
  },
  {
    number: "III",
    title: "Generate and verify",
    description: "Voice generation is routed intentionally: XTTS for supported reference dubbing, Sarvam for managed Indian-language speech.",
    file: "voice_route.py",
    status: "audio checked",
    code: `voice = router.select(target="kn")
assert voice.engine == "sarvam"
assert voice.exact_clone is False

audio = voice.synthesize(translation)
validate_audio(audio)
mux(video, audio, output="localized.mp4")`,
  },
];

export function AnimatedPipelineCodeSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.18 },
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveStep((step) => (step + 1) % steps.length);
    }, 5200);
    return () => window.clearInterval(interval);
  }, []);

  const active = steps[activeStep];

  return (
    <section ref={sectionRef} className="relative mt-12 overflow-hidden bg-foreground py-20 text-background">
      <div className="absolute inset-0 opacity-[0.055] pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: "repeating-linear-gradient(-45deg, transparent, transparent 38px, currentColor 38px, currentColor 39px)",
        }} />
      </div>

      <div className="relative z-10 mx-auto grid max-w-[1400px] gap-12 px-6 lg:grid-cols-[0.9fr_1fr] lg:px-12">
        <div>
          <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-background/50">
            <span className="h-px w-8 bg-background/30" />
            Pipeline contract
          </span>
          <h2 className={`font-display text-5xl leading-none transition-all duration-700 lg:text-6xl ${isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}>
            The run is code-shaped,
            <br />
            <span className="text-background/45">not black-box shaped.</span>
          </h2>

          <div className="mt-12">
            {steps.map((step, index) => (
              <button
                key={step.number}
                type="button"
                onClick={() => setActiveStep(index)}
                className={`group w-full border-b border-background/10 py-7 text-left transition-opacity duration-300 ${activeStep === index ? "opacity-100" : "opacity-38 hover:opacity-70"}`}
              >
                <div className="flex gap-6">
                  <span className="font-display text-3xl text-background/30">{step.number}</span>
                  <div>
                    <h3 className="font-display text-3xl transition-transform duration-300 group-hover:translate-x-1">{step.title}</h3>
                    <p className="mt-3 max-w-xl leading-relaxed text-background/58">{step.description}</p>
                    {activeStep === index && (
                      <div className="mt-5 h-px overflow-hidden bg-background/15">
                        <div className="h-full bg-background" style={{ animation: "vidio-progress 5.2s linear forwards" }} />
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="self-start border border-background/12 bg-background/[0.025]">
          <div className="flex items-center justify-between border-b border-background/10 px-6 py-4">
            <div className="flex gap-2">
              <span className="size-3 rounded-full bg-background/20" />
              <span className="size-3 rounded-full bg-background/20" />
              <span className="size-3 rounded-full bg-background/20" />
            </div>
            <span className="font-mono text-xs text-background/42">{active.file}</span>
          </div>

          <div className="min-h-[360px] p-8 font-mono text-sm">
            <pre className="overflow-x-auto text-background/72">
              {active.code.split("\n").map((line, lineIndex) => (
                <div
                  key={`${activeStep}-${lineIndex}`}
                  className="vidio-code-line leading-loose"
                  style={{ animationDelay: `${lineIndex * 70}ms` }}
                >
                  <span className="inline-block w-8 select-none text-background/20">{lineIndex + 1}</span>
                  <span>
                    {line.split("").map((char, charIndex) => (
                      <span
                        key={`${activeStep}-${lineIndex}-${charIndex}`}
                        className="vidio-code-char"
                        style={{ animationDelay: `${lineIndex * 70 + charIndex * 12}ms` }}
                      >
                        {char === " " ? "\u00A0" : char}
                      </span>
                    ))}
                  </span>
                </div>
              ))}
            </pre>
          </div>

          <div className="flex items-center gap-3 border-t border-background/10 px-6 py-4">
            <span className="size-2 rounded-full bg-emerald-400" />
            <span className="font-mono text-xs text-background/42">{active.status}</span>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes vidio-progress {
          from { width: 0%; }
          to { width: 100%; }
        }

        .vidio-code-line {
          opacity: 0;
          transform: translateX(-8px);
          animation: vidio-line-reveal 0.36s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }

        @keyframes vidio-line-reveal {
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .vidio-code-char {
          opacity: 0;
          filter: blur(7px);
          animation: vidio-char-reveal 0.28s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }

        @keyframes vidio-char-reveal {
          to {
            opacity: 1;
            filter: blur(0);
          }
        }
      `}</style>
    </section>
  );
}
