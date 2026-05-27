import { Download, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CaptionTrack } from "@/lib/types";

function isRealUrl(url?: string) {
  return !!url && (url.startsWith("http://") || url.startsWith("https://"));
}

export function ResultVideoCard({
  title,
  url,
  backend,
  note,
  captions = [],
}: {
  title: string;
  url?: string;
  backend: string;
  note: string;
  captions?: CaptionTrack[];
}) {
  const vttCaption = captions.find((caption) => caption.format === "vtt" && isRealUrl(caption.url));
  const downloadableCaptions = captions.filter((caption) => isRealUrl(caption.url) && (caption.format === "vtt" || caption.format === "srt"));

  return (
    <div className="border border-foreground/10 bg-card p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-3xl">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{backend}</p>
        </div>
        <PlayCircle className="size-6 text-muted-foreground" />
      </div>
      {isRealUrl(url) ? (
        <video src={url} controls className="aspect-video w-full border border-foreground/10 bg-black object-contain" crossOrigin="anonymous">
          {vttCaption && (
            <track
              kind={vttCaption.kind || "subtitles"}
              src={vttCaption.url}
              srcLang={vttCaption.languageCode || "und"}
              label={vttCaption.label || "Original-language captions"}
              default
            />
          )}
        </video>
      ) : (
        <div className="flex aspect-video items-center justify-center border border-foreground/10 bg-foreground/[0.03] p-6 text-center text-sm text-muted-foreground">
          Result video appears here when a real backend job completes.
        </div>
      )}
      <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{note}</p>
      {downloadableCaptions.length > 0 && (
        <div className="mt-4 border border-foreground/10 bg-background p-3">
          <p className="text-xs text-muted-foreground">Captions are generated from the original ASR transcript.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {downloadableCaptions.map((caption) => (
              <Button key={`${caption.format}-${caption.url}`} asChild variant="outline" size="sm" className="rounded-full border-foreground/20">
                <a href={caption.url} download>
                  <Download className="size-4" />
                  {caption.format === "vtt" ? "WebVTT" : "SRT"}
                </a>
              </Button>
            ))}
          </div>
        </div>
      )}
      {isRealUrl(url) && (
        <Button asChild variant="outline" className="mt-4 w-full rounded-full border-foreground/20">
          <a href={url} download>
            <Download className="size-4" />
            Download MP4
          </a>
        </Button>
      )}
    </div>
  );
}
