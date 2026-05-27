import Link from "next/link";
import { ArrowRight, Ban, BrainCircuit, Cloud, Cpu, FileAudio, FileJson, FileVideo, GitBranch, LockKeyhole, Mic2, PackageCheck, RadioTower, ScanLine, ShieldCheck, Volume2, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ArchitectureFlow } from "@/components/vidiolingua/architecture-flow";
import { AnimatedPipelineCodeSection } from "@/components/vidiolingua/animated-pipeline-code-section";
import { InteractiveArchitectureDiagram } from "@/components/vidiolingua/interactive-architecture-diagram";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";

const lanes = [
  { title: "XTTS path", body: "Supported global languages use reference audio for speaker-style dubbing, and missing references are treated as real errors.", icon: Mic2 },
  { title: "Sarvam path", body: "Indian-language voice is routed to Sarvam intentionally as managed speech: clear, useful, and not sold as cloning.", icon: Cloud },
  { title: "IndicTrans2 path", body: "Supported Indic translation pairs use IndicTrans2, with English to Kannada validated in the current backend state.", icon: GitBranch },
  { title: "Translation QA layer", body: "After the primary engine runs, glossary, entity, number, script, expansion, and context-window checks produce auditable integrity metadata.", icon: ShieldCheck },
  { title: "Language integrity gate", body: "A dedicated report scores script, segment, number, name, punctuation, repetition, and expansion checks before TTS begins.", icon: ScanLine },
  { title: "Phonetic resolver", body: "A separate TTS-prepared text field can expand acronyms and preserve pronunciation terms without changing canonical translations.", icon: Volume2 },
  { title: "Prosody & Elocution Engine", body: "Source rhythm, pauses, speech rate, and energy become guidance and validation artifacts.", icon: Waves },
  { title: "HuBERT-guided adapter", body: "Pretrained HuBERT features feed a lightweight project-trained adapter; HuBERT itself is not trained from scratch.", icon: BrainCircuit },
  { title: "Disabled IndicF5", body: "IndicF5 stays disabled/local experimental due to Windows memory and load-time risk.", icon: Cpu },
  { title: "No silent fallback", body: "Strict practical jobs fail clearly instead of masking voice routing problems.", icon: Ban },
  { title: "Backend-only secrets", body: "Sarvam keys remain in backend env files and never move into NEXT_PUBLIC variables.", icon: LockKeyhole },
];

const runtimeEnvironments = [
  {
    name: ".venv_api",
    status: "Verified active",
    purpose: "FastAPI, job status, orchestration, lightweight validation tools.",
    packages: "Python 3.11.11; FastAPI 0.136.1; Uvicorn 0.46.0; requests 2.33.1; no torch/TTS/transformers detected.",
    isolatedBecause: "API startup should not import model runtimes or GPU stacks.",
    calledBy: "uvicorn backend.main:app; backend tools.",
    produces: "API responses, job status/result payloads, manifests through pipeline calls.",
    guardrail: "Do not eagerly import XTTS, IndicTrans2, IndicF5, or HuBERT.",
    icon: ShieldCheck,
  },
  {
    name: ".venv_tts",
    status: "Protected known-good",
    purpose: "Coqui XTTS speaker-reference voice generation for supported global languages.",
    packages: "Python 3.11.11; TTS 0.22.0; torch 2.5.1+cpu; torchaudio 2.5.1+cpu; transformers 4.46.3; numpy 1.26.4.",
    isolatedBecause: "XTTS dependency drift has been treated as a direct risk to the working French path.",
    calledBy: "pipeline_runner -> tts/run_tts.py for TTS stage.",
    produces: "Timed WAV output and phonetic-resolution reports.",
    guardrail: "Do not install IndicTrans2 or IndicF5 dependencies here.",
    icon: Mic2,
  },
  {
    name: ".venv_indictrans2",
    status: "Verified CUDA worker",
    purpose: "IndicTrans2 translation for supported Indic pairs, including the Kannada path.",
    packages: "Python 3.11.11; torch 2.5.1+cu121; transformers 4.51.3; IndicTransToolkit 1.1.1; numpy 2.2.6.",
    isolatedBecause: "IndicTrans2 uses a separate CUDA fp16 model/runtime and workspace HF caches.",
    calledBy: "translation.engines.IndicTrans2Engine -> workers.indictrans2_worker.",
    produces: "JSON translation responses with device, dtype, model, and no-fallback metadata.",
    guardrail: "Batch size 1; fail loudly when unavailable; no LLM/deep-translator fallback for supported pairs.",
    icon: GitBranch,
  },
  {
    name: ".venv_indicf5",
    status: "Disabled / quarantined",
    purpose: "Local experimental IndicF5 sandbox retained for future approved work.",
    packages: "Python 3.11.11; torch 2.5.1+cu121; transformers 4.57.6; f5-tts 1.1.20; numpy 2.4.3.",
    isolatedBecause: "Local IndicF5 hit timeout, ckpt_path/API mismatch, and torch.device compatibility failures.",
    calledBy: "Only voice.engines.indicf5_engine when explicitly enabled; current policy blocks local execution.",
    produces: "No production output in current state.",
    guardrail: "VIDIOLINGUA_ENABLE_INDICF5=false and local_disabled; do not load locally.",
    icon: Ban,
  },
  {
    name: ".venv_prosody",
    status: "Evidence layer",
    purpose: "HuBERT feature extraction, prosody validation, and adapter reports.",
    packages: "Python 3.11.11; torch 2.11.0+cpu; transformers 5.8.0; numpy 2.4.4; soundfile 0.13.1.",
    isolatedBecause: "HuBERT/transformers loads should not disturb XTTS or IndicTrans2.",
    calledBy: "voice.hubert_prosody -> workers.hubert_prosody_worker.",
    produces: "HuBERT feature JSON, embeddings, prosody similarity reports.",
    guardrail: "Unavailable HuBERT reports evidence; it should not break XTTS/Sarvam routing.",
    icon: BrainCircuit,
  },
];

const packageNodes = [
  ["Frontend", "NEW_Frontend", "Upload, status polling, evidence UI"],
  ["Backend API", "backend/main.py", "FastAPI routes and safe file serving"],
  ["Orchestration", "pipeline_runner + job_manifest", "Subprocess stages and durable artifact registry"],
  ["ASR", "asr/run_asr.py", "WhisperX/faster-whisper, PyAnnote metadata"],
  ["Translation", "translation/*", "Router, IndicTrans2 engine, QA/integrity"],
  ["Voice", "tts + voice/*", "XTTS, Sarvam, disabled IndicF5, audio validation"],
  ["Workers", "workers/*", "IndicTrans2, IndicF5, HuBERT process boundaries"],
  ["Evidence", "evaluation + compliance", "Metrics, provenance, reports, passports"],
  ["Export", "tools/create_multilingual_export.py", "Packaging-only HLS/MP4/manifest layer"],
];

const pipelineChain = [
  "Frontend upload",
  "FastAPI /api/upload",
  "job_store",
  "pipeline_runner",
  "ASR",
  "speaker analysis",
  "translation router",
  "IndicTrans2 worker when supported",
  "translation QA + linguistic integrity",
  "phonetic + prosody planning",
  "TTS router",
  "XTTS or Sarvam",
  "audio validation",
  "mux/lip-sync",
  "metrics + compliance",
  "job_manifest + pipeline_result",
  "frontend polling/results",
];

const artifactRows = [
  ["Upload", "input_video.mp4", "source video copied into the job/results area"],
  ["Manifest", "job_manifest.json", "stage status, routing, artifacts, warnings, errors"],
  ["ASR", "asr/output/*_transcription.json", "segments, timestamps, language, diarization metadata"],
  ["Translation", "translation/output/*_LANG.json", "translated segments and selected engine metadata"],
  ["QA", "translation_qa_report.json + linguistic_integrity_report.json", "script, entity, number, context, expansion, severity evidence"],
  ["Voice", "tts/output/*.wav + phonetic_resolution_report.json", "timed dubbed WAV and TTS-prepared text evidence"],
  ["Prosody", "prosody/*.json", "source profile, TTS plan, validation, HuBERT reports when available"],
  ["Speaker", "speaker_analysis/*.json", "diarization, segment mapping, profiles, voice assignment plan"],
  ["Result", "results/*_dubbed_LANG.mp4 + pipeline_result.json", "final media and API result contract"],
  ["Evaluation", "evaluation/metrics_report.json", "operational, audio, media, translation, prosody, compliance summaries"],
  ["Compliance", "compliance/*", "consent, SGI/abuse reports, provenance, fingerprints, passport"],
  ["Export", "metadata/multilingual_manifest.json", "packaging-only multilingual HLS/MP4 evidence"],
];

const engineeringDecisions = [
  ["XTTS dependency fragility", "Working French speaker-reference path could break with torch/transformers drift.", "Keep XTTS in .venv_tts.", "TTS 0.22.0, torch 2.5.1+cpu, transformers 4.46.3 verified.", "COMMAND_LOG.md; VALIDATE_WORKING_XTTS_PIPELINE.md"],
  ["IndicTrans2 CUDA/model needs", "IndicTrans2 remote-code model and CUDA fp16 runtime differ from XTTS.", "Use .venv_indictrans2 plus JSON subprocess worker.", "IndicTrans2Engine shells into workers.indictrans2_worker.", "PHASE3B_INDICTRANS2_INSTALL_REPORT_2026-04-29.md"],
  ["IndicF5 local instability", "Windows local execution hit timeout and API/device mismatches.", "Quarantine .venv_indicf5 and keep production routing disabled.", "voice.router requires explicit enablement and local_enabled mode.", "PHASE3C_INDICF5_* reports; VOICE_BACKENDS.md"],
  ["Reliable Indian-language TTS", "Local IndicF5 was not production-ready for Kannada delivery.", "Use Sarvam as managed Indian-language TTS.", "SarvamEngine posts backend-side to Sarvam and labels output as managed TTS.", "PHASE4_SARVAM_INTEGRATION_REPORT_2026-04-29.md"],
  ["Long failures were hard to inspect", "Stage crashes could hide which artifact failed.", "Add job_manifest.json and per-stage logs/artifact registration.", "job_manifest tracks receive_upload through complete.", "JOB_MANIFEST_ORCHESTRATION_REPORT_2026-05-05.md"],
  ["Multilingual delivery needed packaging", "One dubbed MP4 per language did not prove OTT-style delivery.", "Create packaging-only multilingual export.", "create_multilingual_export reads existing WAV/MP4 artifacts only.", "MULTILINGUAL_AUDIO_EXPORT_REPORT_2026-05-05.md"],
  ["Synthetic media accountability", "Generated dubbing needs provenance, consent, and risk evidence.", "Add report-only compliance passport sidecars.", "compliance_passport registers provenance, hashes, audit ledger, retention.", "RESPONSIBLE_AI_PROVENANCE_ENGINE_REPORT_2026-05-06.md"],
];

const diagramSources = [
  "docs/architecture/package_diagram.mmd",
  "docs/architecture/component_diagram.mmd",
  "docs/architecture/deployment_diagram.mmd",
  "docs/architecture/sequence_pipeline_run.mmd",
  "docs/architecture/sequence_indictrans2_worker.mmd",
  "docs/architecture/sequence_voice_backend_selection.mmd",
  "docs/architecture/artifact_flow_diagram.mmd",
];

export default function ArchitecturePage() {
  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-12 grid gap-8 lg:grid-cols-[0.82fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              System architecture
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">Built as a real localization pipeline, not a black box.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            The frontend uploads, FastAPI orchestrates, ASR writes the source transcript, translation routes through the right engine, and voice generation splits cleanly between XTTS speaker-reference output and Sarvam managed Indian-language speech. Each stage leaves evidence before the final MP4 is muxed.
          </p>
        </div>

        <InteractiveArchitectureDiagram />

        <div className="mt-8">
          <ArchitectureFlow />
        </div>

        <div className="mt-12 border border-foreground/10 bg-card p-7">
          <div className="mb-8 grid gap-6 lg:grid-cols-[0.78fr_1fr] lg:items-end">
            <div>
              <span className="mb-4 inline-flex items-center gap-3 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                <span className="h-px w-8 bg-foreground/30" />
                Delivery expansion
              </span>
              <h2 className="font-display text-5xl leading-none">OTT-style multilingual delivery.</h2>
            </div>
            <p className="text-muted-foreground">
              The next layer packages one source video with multiple localized audio tracks, so French XTTS and Kannada Sarvam evidence can travel together as HLS alternate audio, a multi-audio MP4, and a manifest.
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-4">
            {[
              { title: "Source video", body: "One picture track remains the anchor.", icon: FileVideo },
              { title: "Localized audio", body: "French, Kannada, Hindi, and future tracks stay selectable.", icon: FileAudio },
              { title: "HLS / MP4", body: "Distribution artifacts are generated without rerunning models.", icon: RadioTower },
              { title: "Manifest proof", body: "Each language records translation, voice route, and validation status.", icon: FileJson },
            ].map((item) => (
              <div key={item.title} className="border border-foreground/10 p-4">
                <item.icon className="mb-6 size-6 text-muted-foreground" />
                <h3 className="mb-2 font-display text-2xl">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.body}</p>
              </div>
            ))}
          </div>
          <Button asChild className="mt-6 rounded-full">
            <Link href="/multilingual-export">
              <PackageCheck className="size-4" />
              Open OTT export
            </Link>
          </Button>
          <Button asChild variant="outline" className="ml-3 mt-6 rounded-full border-background/20">
            <Link href="/language-integrity">
              <ScanLine className="size-4" />
              Language integrity
            </Link>
          </Button>
          <Button asChild variant="outline" className="ml-3 mt-6 rounded-full border-background/20">
            <Link href="/differentiators">
              <Waves className="size-4" />
              Differentiators
            </Link>
          </Button>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {lanes.map((lane) => (
            <div key={lane.title} className="border border-foreground/10 bg-card p-6">
              <lane.icon className="mb-8 size-8 text-muted-foreground" />
              <h2 className="mb-3 font-display text-3xl">{lane.title}</h2>
              <p className="leading-relaxed text-muted-foreground">{lane.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 border border-foreground/10 bg-foreground p-8 text-background">
          <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <FileVideo className="mb-6 size-8 text-background/65" />
              <h2 className="mb-3 font-display text-5xl">A route you can inspect.</h2>
              <p className="max-w-3xl text-background/65">Start a run from the upload page, then follow the backend status and final result metadata instead of trusting a hidden one-click promise.</p>
            </div>
            <Button asChild size="lg" className="h-14 rounded-full bg-background px-8 text-base text-foreground hover:bg-background/90">
              <Link href="/upload">
                Start a run
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>

        <section id="deep-technical-architecture" className="mt-20 border-t border-foreground/10 pt-16">
          <div className="mb-10 grid gap-6 lg:grid-cols-[0.76fr_1fr] lg:items-end">
            <div>
              <span className="mb-4 inline-flex items-center gap-3 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                <span className="h-px w-8 bg-foreground/30" />
                Verified from repo code and reports
              </span>
              <h2 className="font-display text-5xl leading-none lg:text-6xl">Inside the pipeline: environments, workers, and artifacts.</h2>
            </div>
            <p className="text-lg leading-relaxed text-muted-foreground">
              Vidiolingua is wired as a set of isolated runtimes and evidence-producing stages. FastAPI stays light, model-heavy work runs in subprocesses, and each major stage leaves JSON, WAV, MP4, manifest, metrics, or provenance artifacts that the UI can inspect.
            </p>
          </div>

          <div className="mb-8 flex flex-wrap gap-2">
            {["System map", "Runtime environments", "Package diagram", "Worker sequences", "Artifact flow", "Engineering decisions"].map((item) => (
              <a key={item} href={`#${item.toLowerCase().replaceAll(" ", "-")}`} className="border border-foreground/10 bg-card px-4 py-2 font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground">
                {item}
              </a>
            ))}
          </div>

          <div id="system-map" className="grid gap-4 lg:grid-cols-4">
            {[
              { label: "Control plane", value: "FastAPI + job_store", detail: "Uploads, status, results, export endpoints.", icon: ShieldCheck },
              { label: "Execution plane", value: "pipeline_runner", detail: "Stage subprocesses, logs, manifests.", icon: Cpu },
              { label: "Model plane", value: "XTTS / IndicTrans2 / Sarvam", detail: "Explicit routing and no silent fallback.", icon: GitBranch },
              { label: "Evidence plane", value: "metrics + compliance", detail: "Reports, manifests, passports, exports.", icon: FileJson },
            ].map((item) => (
              <div key={item.label} className="border border-foreground/10 bg-card p-5">
                <item.icon className="mb-6 size-6 text-muted-foreground" />
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">{item.label}</p>
                <h3 className="mb-2 font-display text-2xl">{item.value}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{item.detail}</p>
              </div>
            ))}
          </div>

          <div id="runtime-environments" className="mt-12">
            <div className="mb-6 flex items-end justify-between gap-4">
              <div>
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Runtime isolation</p>
                <h3 className="font-display text-4xl">Custom Python environments.</h3>
              </div>
              <p className="max-w-xl text-sm text-muted-foreground">Captured with safe read-only metadata probes. No dependencies were installed, no venvs were mutated, and no model pipeline was run.</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-5">
              {runtimeEnvironments.map((env) => (
                <div key={env.name} className="flex min-h-[420px] flex-col border border-foreground/10 bg-card p-5">
                  <env.icon className="mb-6 size-7 text-muted-foreground" />
                  <div className="mb-4">
                    <h4 className="font-mono text-lg">{env.name}</h4>
                    <p className="mt-1 font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">{env.status}</p>
                  </div>
                  <dl className="space-y-4 text-sm">
                    <div>
                      <dt className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">Purpose</dt>
                      <dd className="mt-1 leading-relaxed">{env.purpose}</dd>
                    </div>
                    <div>
                      <dt className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">Verified packages</dt>
                      <dd className="mt-1 leading-relaxed text-muted-foreground">{env.packages}</dd>
                    </div>
                    <div>
                      <dt className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">Why isolated</dt>
                      <dd className="mt-1 leading-relaxed text-muted-foreground">{env.isolatedBecause}</dd>
                    </div>
                    <div>
                      <dt className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">Calls / produces</dt>
                      <dd className="mt-1 leading-relaxed text-muted-foreground">{env.calledBy} Produces: {env.produces}</dd>
                    </div>
                  </dl>
                  <p className="mt-auto pt-5 text-xs leading-relaxed text-muted-foreground">{env.guardrail}</p>
                </div>
              ))}
            </div>
          </div>

          <div id="package-diagram" className="mt-12 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="border border-foreground/10 bg-card p-6">
              <p className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Package diagram</p>
              <h3 className="mb-4 font-display text-4xl">The package map.</h3>
              <p className="mb-6 leading-relaxed text-muted-foreground">
                Mermaid source is stored in the repo, and this page uses a static visual map so the frontend does not need a new Mermaid dependency.
              </p>
              <div className="grid gap-3">
                {diagramSources.map((source) => (
                  <div key={source} className="border border-foreground/10 px-3 py-2 font-mono text-xs text-muted-foreground">{source}</div>
                ))}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {packageNodes.map(([title, module, detail]) => (
                <div key={title} className="border border-foreground/10 bg-card p-4">
                  <p className="mb-2 font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">{module}</p>
                  <h4 className="mb-2 font-display text-2xl">{title}</h4>
                  <p className="text-sm leading-relaxed text-muted-foreground">{detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div id="worker-sequences" className="mt-12 border border-foreground/10 bg-card p-6">
            <div className="mb-8 grid gap-6 lg:grid-cols-[0.8fr_1fr] lg:items-end">
              <div>
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Worker-call architecture</p>
                <h3 className="font-display text-4xl">Heavy work crosses process boundaries.</h3>
              </div>
              <p className="leading-relaxed text-muted-foreground">
                The backend does not load every ML stack inside FastAPI. Stages serialize input to job-local files, invoke the right Python runtime, read structured outputs, and let process exit release memory. That matters on the verified local i5 + RTX 4050 development machine.
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {[
                ["Translation", "IndicTrans2Engine writes request.json, calls .venv_indictrans2, reads response.json."],
                ["Voice", "tts/run_tts.py routes each target to XTTS or Sarvam; IndicF5 stays blocked unless explicitly enabled."],
                ["Prosody", "HuBERT extraction calls .venv_prosody and reports unavailable instead of breaking the core route."],
                ["Memory", "Subprocess exits are the cleanup strategy for model-heavy stages; manifests preserve the evidence trail."],
              ].map(([title, body]) => (
                <div key={title} className="border border-foreground/10 p-4">
                  <h4 className="mb-2 font-display text-2xl">{title}</h4>
                  <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
                </div>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-2">
              {pipelineChain.map((step, index) => (
                <div key={step} className="flex items-center gap-2">
                  <span className="border border-foreground/10 px-3 py-2 text-sm text-muted-foreground">{step}</span>
                  {index < pipelineChain.length - 1 ? <ArrowRight className="size-4 text-muted-foreground" /> : null}
                </div>
              ))}
            </div>
          </div>

          <div id="artifact-flow" className="mt-12">
            <div className="mb-6 grid gap-6 lg:grid-cols-[0.8fr_1fr] lg:items-end">
              <div>
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Artifact flow</p>
                <h3 className="font-display text-4xl">Every stage leaves something inspectable.</h3>
              </div>
              <p className="leading-relaxed text-muted-foreground">
                `job_manifest.json` registers stage artifacts when present, while `pipeline_result.json` remains the API result contract. Metrics, speaker, prosody, translation QA, compliance, and export reports attach around those files.
              </p>
            </div>
            <div className="overflow-x-auto border border-foreground/10">
              <table className="w-full min-w-[900px] border-collapse bg-card text-left text-sm">
                <thead>
                  <tr className="border-b border-foreground/10 text-muted-foreground">
                    <th className="px-4 py-3 font-mono text-xs uppercase tracking-[0.12em]">Layer</th>
                    <th className="px-4 py-3 font-mono text-xs uppercase tracking-[0.12em]">Artifacts</th>
                    <th className="px-4 py-3 font-mono text-xs uppercase tracking-[0.12em]">Flow role</th>
                  </tr>
                </thead>
                <tbody>
                  {artifactRows.map(([layer, artifacts, role]) => (
                    <tr key={layer} className="border-b border-foreground/10 last:border-0">
                      <td className="px-4 py-3 font-display text-xl">{layer}</td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{artifacts}</td>
                      <td className="px-4 py-3 leading-relaxed text-muted-foreground">{role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div id="engineering-decisions" className="mt-12">
            <div className="mb-6 grid gap-6 lg:grid-cols-[0.8fr_1fr] lg:items-end">
              <div>
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Dependency-conflict history</p>
                <h3 className="font-display text-4xl">Architecture decisions backed by failures.</h3>
              </div>
              <p className="leading-relaxed text-muted-foreground">
                These rows are limited to verified source, docs, command logs, and current runtime probes. IndicF5 remains disabled, generic fallback remains blocked, and Sarvam stays backend-only.
              </p>
            </div>
            <div className="overflow-x-auto border border-foreground/10">
              <table className="w-full min-w-[1100px] border-collapse bg-card text-left text-sm">
                <thead>
                  <tr className="border-b border-foreground/10 text-muted-foreground">
                    {["Problem encountered", "Technical risk", "Architecture decision", "Current implementation", "Proof artifact/doc"].map((head) => (
                      <th key={head} className="px-4 py-3 font-mono text-xs uppercase tracking-[0.12em]">{head}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {engineeringDecisions.map((row) => (
                    <tr key={row[0]} className="border-b border-foreground/10 last:border-0">
                      {row.map((cell, index) => (
                        <td key={cell} className={`px-4 py-3 leading-relaxed ${index === 0 ? "font-display text-xl text-foreground" : "text-muted-foreground"}`}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-12 grid gap-4 lg:grid-cols-3">
            {[
              ["Verified", "Runtime versions, worker scripts, route policy, env-key presence, package layout, job manifest and export artifacts."],
              ["Inferred", "Process exit is the intended memory-release pattern for heavy worker calls; exact memory savings were not benchmarked in this pass."],
              ["Needs verification", "A fresh full upload run was intentionally not performed; historical protected outputs may predate job_manifest.json."],
            ].map(([title, body]) => (
              <div key={title} className="border border-foreground/10 bg-card p-5">
                <h4 className="mb-2 font-display text-2xl">{title}</h4>
                <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>

          <div className="mt-12 border border-foreground/10 bg-foreground p-8 text-background">
            <PackageCheck className="mb-6 size-8 text-background/65" />
            <h3 className="mb-4 font-display text-5xl">What this enables.</h3>
            <div className="grid gap-4 text-sm leading-relaxed text-background/70 md:grid-cols-2 lg:grid-cols-4">
              {["Safer development without destabilizing XTTS or IndicTrans2.", "Debuggable failures through manifests, reports, and logs.", "One-model-at-a-time execution that can migrate to cloud workers later.", "Frontend evidence panels that show unavailable/failed states instead of invented success."].map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          </div>
        </section>
      </section>
      <AnimatedPipelineCodeSection />
      <SiteFooter />
    </main>
  );
}
