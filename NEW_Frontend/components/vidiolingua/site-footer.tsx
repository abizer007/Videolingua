import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-foreground/10 py-10">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-6 px-6 text-sm text-muted-foreground lg:flex-row lg:items-center lg:justify-between lg:px-12">
        <div>
          <div className="font-display text-2xl text-foreground">VideoLingua</div>
          <p className="mt-2 max-w-2xl">
            Vidiolingua: AI video localization POC built for Techgium.
          </p>
          <p className="mt-2 max-w-2xl text-xs">
            © L&amp;T Technology Services 2026. Vidiolingua is a Techgium proof-of-concept for AI video localization.
          </p>
        </div>
        <div className="flex flex-wrap gap-5">
          <Link href="/differentiators" className="hover:text-foreground">Differentiators</Link>
          <Link href="/multilingual-export" className="hover:text-foreground">OTT Export</Link>
          <Link href="/language-integrity" className="hover:text-foreground">Language Integrity</Link>
          <Link href="/pipeline" className="hover:text-foreground">Pipeline</Link>
          <Link href="/results" className="hover:text-foreground">Results</Link>
          <Link href="/architecture" className="hover:text-foreground">Architecture</Link>
          <Link href="/backends" className="hover:text-foreground">Backends</Link>
        </div>
      </div>
    </footer>
  );
}
