import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function VideoLinguaCtaSection() {
  return (
    <section className="px-6 py-24 lg:px-12 lg:py-32">
      <div className="mx-auto max-w-[1400px] border border-foreground/10 bg-foreground p-8 text-background md:p-12 lg:p-16">
        <div className="grid gap-10 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-background/55">
              <span className="h-px w-8 bg-background/30" />
              Launch a localization run
            </span>
            <h2 className="max-w-4xl font-display text-5xl leading-none tracking-normal lg:text-7xl">
              Upload once. Follow the route all the way to MP4.
            </h2>
          </div>
          <Button asChild size="lg" className="h-14 rounded-full bg-background px-8 text-base text-foreground hover:bg-background/90">
            <Link href="/upload">
              Start a localization job
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
