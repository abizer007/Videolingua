"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileAudio, FileVideo, Loader2, ShieldCheck, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LanguageSelector } from "@/components/vidiolingua/language-selector";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";
import { getLanguageCapability, backendNameForLanguage } from "@/lib/language-capabilities";
import { uploadVideo } from "@/lib/api";
import { clearRunState, prepareFreshRunSession, readTerminalJob, saveStoredJob } from "@/lib/pipeline-storage";

export default function UploadPage() {
  const router = useRouter();
  const voiceSampleInputRef = useRef<HTMLInputElement | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [voiceSample, setVoiceSample] = useState<File | null>(null);
  const [autoReference, setAutoReference] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState("fr");
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [includeCaptions, setIncludeCaptions] = useState(false);
  const [groundTruthTranscriptFile, setGroundTruthTranscriptFile] = useState<File | null>(null);
  const [groundTruthTranscriptText, setGroundTruthTranscriptText] = useState("");
  const [referenceTranslationFile, setReferenceTranslationFile] = useState<File | null>(null);
  const [referenceTranslationText, setReferenceTranslationText] = useState("");
  const [humanMosRating, setHumanMosRating] = useState("");
  const [humanQualityNotes, setHumanQualityNotes] = useState("");
  const [contentOwnerConfirmation, setContentOwnerConfirmation] = useState(false);
  const [speakerConsent, setSpeakerConsent] = useState(false);
  const [intendedUse, setIntendedUse] = useState("internal_demo");
  const [commercialUseAllowed, setCommercialUseAllowed] = useState(false);
  const [retentionDays, setRetentionDays] = useState(30);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState("");
  const [videoMeta, setVideoMeta] = useState<{ duration: number; width: number; height: number } | null>(null);
  const [staleNotice, setStaleNotice] = useState<string | null>(null);

  const capability = useMemo(() => getLanguageCapability(targetLanguage), [targetLanguage]);
  const requiresReference = capability.referenceAudio === "required";
  const isSarvam = capability.family === "sarvam";
  const referenceMode = voiceSample ? "uploaded" : autoReference ? "auto_extract" : "none";
  const canSubmit = !!video && !submitting;

  function openVoiceSamplePicker() {
    setAutoReference(false);
    setError(null);
    window.setTimeout(() => voiceSampleInputRef.current?.click(), 0);
  }

  useEffect(() => {
    const terminalJob = readTerminalJob();
    if (terminalJob) {
      setStaleNotice(`Previous job ${terminalJob.jobId} ended with ${terminalJob.status}. Starting a new run will use fresh state.`);
    }
  }, []);

  useEffect(() => {
    if (!requiresReference) {
      setError((current) => current && /XTTS speaker-reference/i.test(current) ? null : current);
    }
  }, [requiresReference]);

  useEffect(() => {
    if (!video) {
      setVideoPreviewUrl("");
      setVideoMeta(null);
      return;
    }

    const objectUrl = URL.createObjectURL(video);
    setVideoPreviewUrl(objectUrl);
    setVideoMeta(null);

    return () => URL.revokeObjectURL(objectUrl);
  }, [video]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!video) {
      setError("Choose a source video before starting the pipeline.");
      return;
    }
    if (video.size <= 0) {
      setError("The selected video appears to be empty.");
      return;
    }
    if (requiresReference && !voiceSample && !autoReference) {
      setError("XTTS speaker-reference dubbing needs either a reference audio file or auto-extract from the uploaded video.");
      return;
    }

    setSubmitting(true);
    setError(null);
    const runSession = prepareFreshRunSession();

    try {
      const response = await uploadVideo({
        video,
        targetLanguage,
        sourceLanguage,
        voiceSample,
        autoReference: autoReference && !voiceSample,
        referenceMode,
        groundTruthTranscriptFile,
        groundTruthTranscriptText,
        referenceTranslationFile,
        referenceTranslationText,
        humanMosRating,
        humanQualityNotes,
        includeCaptions,
        cloningRequired: capability.family === "xtts",
        responsibleAIConsent: {
          contentOwnerConfirmation,
          speakerConsent,
          intendedUse,
          commercialUseAllowed,
          retentionDays,
        },
      });

      saveStoredJob({
        jobId: response.jobId,
        runSessionId: runSession.runSessionId,
        targetLanguage,
        voiceBackend: backendNameForLanguage(targetLanguage),
        voiceLabel: capability.voiceLabel,
        translationBackend: capability.translationBackend,
        videoName: video.name,
        sourceFileName: video.name,
        voiceSampleName: voiceSample?.name,
        referenceMode,
        includeCaptions,
        createdAt: runSession.createdAt,
        status: "queued",
        terminal: false,
      });

      router.push(`/pipeline?jobId=${encodeURIComponent(response.jobId)}`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <section className="mx-auto max-w-[1400px] px-6 pb-20 pt-32 lg:px-12 lg:pt-40">
        <div className="mb-12 grid gap-8 lg:grid-cols-[0.8fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-muted-foreground">
              <span className="h-px w-8 bg-foreground/30" />
              Start a dubbing run
            </span>
            <h1 className="font-display text-5xl leading-none tracking-normal lg:text-7xl">Upload, route, and localize.</h1>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Pick a target language, confirm the voice route, and let the backend carry the video through transcription, translation integrity checks, speech, validation, and final MP4 output.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-8">
          <div className="grid gap-6 lg:grid-cols-[0.72fr_1fr]">
            <div className="space-y-6">
              <label className="block border border-foreground/10 bg-card p-6">
                <div className="mb-5 flex items-center gap-3">
                  <FileVideo className="size-6 text-muted-foreground" />
                  <div>
                    <div className="font-display text-3xl">Source video</div>
                    <div className="text-sm text-muted-foreground">Use the original clip you want localized.</div>
                  </div>
                </div>
                <input
                  type="file"
                  accept="video/*"
                  onChange={(event) => {
                    setVideo(event.target.files?.[0] ?? null);
                    setVideoMeta(null);
                    setError(null);
                  }}
                  className="w-full border border-foreground/10 p-3 text-sm"
                />
                {video && <p className="mt-4 font-mono text-xs text-muted-foreground">{video.name} - {(video.size / (1024 * 1024)).toFixed(2)} MB</p>}
              </label>

              {videoPreviewUrl && (
                <div className="border border-foreground/10 bg-card p-6">
                  <div className="mb-4">
                    <div className="font-display text-3xl">Preview source</div>
                    <div className="text-sm text-muted-foreground">Play the selected file before the backend receives it.</div>
                  </div>
                  <video
                    src={videoPreviewUrl}
                    controls
                    preload="metadata"
                    className="aspect-video w-full bg-foreground object-contain"
                    onLoadedMetadata={(event) => {
                      const element = event.currentTarget;
                      setVideoMeta({
                        duration: element.duration,
                        width: element.videoWidth,
                        height: element.videoHeight,
                      });
                    }}
                  />
                  {videoMeta && (
                    <div className="mt-4 grid gap-2 font-mono text-xs text-muted-foreground sm:grid-cols-3">
                      <div className="border border-foreground/10 p-2">Duration: {videoMeta.duration.toFixed(2)}s</div>
                      <div className="border border-foreground/10 p-2">Resolution: {videoMeta.width} x {videoMeta.height}</div>
                      <div className="border border-foreground/10 p-2">Size: {video ? (video.size / (1024 * 1024)).toFixed(2) : "0.00"} MB</div>
                    </div>
                  )}
                </div>
              )}

              <div className="border border-foreground/10 bg-card p-6">
                <div className="mb-5 flex items-center gap-3">
                  <FileAudio className="size-6 text-muted-foreground" />
                  <div>
                    <div className="font-display text-3xl">Reference audio</div>
                    <div className="text-sm text-muted-foreground">
                      {requiresReference
                        ? "Upload reference audio or auto-extract from the uploaded video."
                        : "Sarvam uses managed Indian-language speech. Reference audio is optional and is not used for exact cloning."}
                    </div>
                  </div>
                </div>
                <div className="mb-4 grid gap-3 sm:grid-cols-2">
                  <label className={`flex cursor-pointer items-start gap-3 border p-3 ${referenceMode === "uploaded" ? "border-foreground/40 bg-background" : "border-foreground/10"}`}>
                    <input
                      type="radio"
                      name="referenceMode"
                      checked={referenceMode === "uploaded"}
                      onChange={openVoiceSamplePicker}
                      className="mt-1"
                    />
                    <span>
                      <span className="block text-sm font-medium">Upload a reference audio file</span>
                      <span className="block text-xs text-muted-foreground">Best when you already have a clean 6-30 second speaker clip.</span>
                    </span>
                  </label>
                  <label className={`flex cursor-pointer items-start gap-3 border p-3 ${autoReference ? "border-foreground/40 bg-background" : "border-foreground/10"}`}>
                    <input
                      type="radio"
                      name="referenceMode"
                      checked={autoReference}
                      onChange={() => {
                        setAutoReference(true);
                        setVoiceSample(null);
                        setError(null);
                      }}
                      className="mt-1"
                    />
                    <span>
                      <span className="block text-sm font-medium">{isSarvam ? "Auto-analyze speaker profile from uploaded video" : "Auto-extract from uploaded video"}</span>
                      <span className="block text-xs text-muted-foreground">
                        {isSarvam ? "Used for speaker-aware voice-fit hints, not exact cloning." : "The backend extracts and validates a speech-heavy WAV before XTTS runs."}
                      </span>
                    </span>
                  </label>
                </div>
                {!requiresReference && (
                  <p className="mb-4 text-xs text-muted-foreground">
                    For Sarvam, this helps choose a managed voice profile via Auto-analyze speaker profile only. It is not exact cloning.
                  </p>
                )}
                <input
                  ref={voiceSampleInputRef}
                  type="file"
                  accept="audio/*,.wav,.mp3,.m4a,.aac,.flac,.ogg,.opus,.webm"
                  onChange={(event) => {
                    setVoiceSample(event.target.files?.[0] ?? null);
                    if (event.target.files?.[0]) setAutoReference(false);
                    setError(null);
                  }}
                  className="hidden"
                />
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="button" variant="outline" onClick={openVoiceSamplePicker} className="rounded-full">
                    <Upload className="size-4" />
                    {voiceSample ? "Replace audio" : "Choose audio"}
                  </Button>
                  {voiceSample && (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setVoiceSample(null);
                        if (voiceSampleInputRef.current) voiceSampleInputRef.current.value = "";
                        setError(null);
                      }}
                      className="rounded-full"
                    >
                      <X className="size-4" />
                      Remove
                    </Button>
                  )}
                </div>
                {voiceSample && <p className="mt-4 break-all font-mono text-xs text-muted-foreground">{voiceSample.name} - {(voiceSample.size / (1024 * 1024)).toFixed(2)} MB</p>}
              </div>

              <label className="block border border-foreground/10 bg-card p-6">
                <div className="mb-3 font-display text-3xl">Source language</div>
                <select value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value)} className="w-full border border-foreground/10 bg-background p-3">
                  <option value="auto">Auto-detect</option>
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="hi">Hindi</option>
                  <option value="kn">Kannada</option>
                </select>
              </label>

              <label className="flex cursor-pointer items-start gap-3 border border-foreground/10 bg-card p-6">
                <input
                  type="checkbox"
                  checked={includeCaptions}
                  onChange={(event) => setIncludeCaptions(event.target.checked)}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-medium">Add original-language captions</span>
                  <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
                    Captions are generated from the original ASR transcript and shown over the translated video.
                  </span>
                </span>
              </label>

              <div className="border border-foreground/10 bg-card p-6">
                <div className="mb-5 flex items-center gap-3">
                  <ShieldCheck className="size-6 text-muted-foreground" />
                  <div>
                    <div className="font-display text-3xl">Responsible AI consent</div>
                    <div className="text-sm text-muted-foreground">Recorded as report-only evidence for the compliance passport.</div>
                  </div>
                </div>
                <div className="grid gap-3">
                  <label className="flex items-start gap-3 border border-foreground/10 p-3">
                    <input
                      type="checkbox"
                      checked={contentOwnerConfirmation}
                      onChange={(event) => setContentOwnerConfirmation(event.target.checked)}
                      className="mt-1"
                    />
                    <span className="text-sm">I confirm I have rights or permission to use this video/audio for localization.</span>
                  </label>
                  <label className="flex items-start gap-3 border border-foreground/10 p-3">
                    <input
                      type="checkbox"
                      checked={speakerConsent}
                      onChange={(event) => setSpeakerConsent(event.target.checked)}
                      className="mt-1"
                    />
                    <span className="text-sm">I confirm speaker consent for speaker-reference voice dubbing if a reference voice is used.</span>
                  </label>
                  <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
                    <label className="block">
                      <div className="mb-2 text-sm font-medium">Intended use</div>
                      <select value={intendedUse} onChange={(event) => setIntendedUse(event.target.value)} className="w-full border border-foreground/10 bg-background p-3 text-sm">
                        <option value="internal_demo">Internal demo</option>
                        <option value="academic">Academic</option>
                        <option value="commercial">Commercial</option>
                        <option value="public_distribution">Public distribution</option>
                      </select>
                    </label>
                    <label className="block">
                      <div className="mb-2 text-sm font-medium">Retention days</div>
                      <input
                        type="number"
                        min="1"
                        max="365"
                        value={retentionDays}
                        onChange={(event) => setRetentionDays(Number(event.target.value || 30))}
                        className="w-full border border-foreground/10 bg-background p-3 text-sm"
                      />
                    </label>
                  </div>
                  <label className="flex items-start gap-3 border border-foreground/10 p-3">
                    <input
                      type="checkbox"
                      checked={commercialUseAllowed}
                      onChange={(event) => setCommercialUseAllowed(event.target.checked)}
                      className="mt-1"
                    />
                    <span className="text-sm">Commercial use allowed.</span>
                  </label>
                </div>
              </div>

              <details className="border border-foreground/10 bg-card p-5">
                <summary className="cursor-pointer font-display text-2xl">Expert reference metrics</summary>
                <p className="mt-3 text-sm text-muted-foreground">
                  Optional. Only needed if you want reference-backed ASR, translation, or human MOS scoring; VideoLingua computes automatic transcript, translation, audio, sync, speaker, and output validation metrics after the run.
                </p>
                <div className="mt-5 grid gap-5">
                  <label className="block">
                    <div className="mb-2 text-sm font-medium">Reference transcript</div>
                    <input
                      type="file"
                      accept=".txt,text/plain"
                      onChange={(event) => setGroundTruthTranscriptFile(event.target.files?.[0] ?? null)}
                      className="w-full border border-foreground/10 p-3 text-sm"
                    />
                    {groundTruthTranscriptFile && <p className="mt-2 font-mono text-xs text-muted-foreground">{groundTruthTranscriptFile.name}</p>}
                    <textarea
                      value={groundTruthTranscriptText}
                      onChange={(event) => setGroundTruthTranscriptText(event.target.value)}
                      placeholder="Optional transcript for WER/CER scoring"
                      className="mt-3 min-h-24 w-full border border-foreground/10 bg-background p-3 text-sm"
                    />
                  </label>
                  <label className="block">
                    <div className="mb-2 text-sm font-medium">Reference translation</div>
                    <input
                      type="file"
                      accept=".txt,text/plain"
                      onChange={(event) => setReferenceTranslationFile(event.target.files?.[0] ?? null)}
                      className="w-full border border-foreground/10 p-3 text-sm"
                    />
                    {referenceTranslationFile && <p className="mt-2 font-mono text-xs text-muted-foreground">{referenceTranslationFile.name}</p>}
                    <textarea
                      value={referenceTranslationText}
                      onChange={(event) => setReferenceTranslationText(event.target.value)}
                      placeholder="Optional reference translation for BLEU/chrF-style scoring"
                      className="mt-3 min-h-24 w-full border border-foreground/10 bg-background p-3 text-sm"
                    />
                  </label>
                  <div className="grid gap-3 sm:grid-cols-[180px_1fr]">
                    <label className="block">
                      <div className="mb-2 text-sm font-medium">Optional human MOS</div>
                      <input
                        type="number"
                        min="1"
                        max="5"
                        step="0.1"
                        value={humanMosRating}
                        onChange={(event) => setHumanMosRating(event.target.value)}
                        className="w-full border border-foreground/10 bg-background p-3 text-sm"
                      />
                    </label>
                    <label className="block">
                      <div className="mb-2 text-sm font-medium">Optional quality notes</div>
                      <input
                        value={humanQualityNotes}
                        onChange={(event) => setHumanQualityNotes(event.target.value)}
                        className="w-full border border-foreground/10 bg-background p-3 text-sm"
                      />
                    </label>
                  </div>
                </div>
              </details>
            </div>

            <LanguageSelector selectedCode={targetLanguage} onSelect={setTargetLanguage} />
          </div>

          <div className="border border-foreground/10 bg-foreground p-6 text-background">
            <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <div className="mb-2 flex items-center gap-2 font-mono text-xs uppercase tracking-[0.16em] text-background/55">
                  <ShieldCheck className="size-4" />
                  Job summary
                </div>
                <h2 className="font-display text-3xl">{capability.name} - {capability.voiceLabel}</h2>
                <p className="mt-2 text-background/62">{capability.description}</p>
              </div>
              <Button type="submit" disabled={!canSubmit} size="lg" className="h-14 rounded-full bg-background px-8 text-base text-foreground hover:bg-background/90">
                {submitting ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4" />}
                {submitting ? "Creating job" : "Start the run"}
              </Button>
            </div>
            {error && <div className="mt-5 border border-destructive/40 bg-destructive/10 p-3 text-sm text-background">{error}</div>}
            {staleNotice && (
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border border-background/25 bg-background/10 p-3 text-sm text-background">
                <span>{staleNotice}</span>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="rounded-full"
                  onClick={() => {
                    clearRunState();
                    setStaleNotice(null);
                  }}
                >
                  Clear old job state
                </Button>
              </div>
            )}
          </div>
        </form>
      </section>
      <SiteFooter />
    </main>
  );
}
