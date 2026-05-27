"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const navLinks = [
  { name: "Workflow", href: "/#workflow" },
  { name: "Differentiators", href: "/differentiators" },
  { name: "Backends", href: "/backends" },
  { name: "Economics", href: "/economics" },
  { name: "OTT Export", href: "/multilingual-export" },
  { name: "Language Integrity", href: "/language-integrity" },
  { name: "Languages", href: "/#languages" },
  { name: "Architecture", href: "/architecture" },
  { name: "Results", href: "/results" },
];

const primaryNavLinks = navLinks.slice(0, 6);
const secondaryNavLinks = navLinks.slice(6);

export function SiteNavigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (!isMoreOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!moreMenuRef.current?.contains(event.target as Node)) {
        setIsMoreOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsMoreOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMoreOpen]);

  return (
    <header className={`fixed z-50 transition-all duration-500 ${isScrolled ? "top-4 left-4 right-4" : "top-0 left-0 right-0"}`}>
      <nav className={`mx-auto transition-all duration-500 ${isScrolled || isOpen ? "max-w-[1320px] rounded-2xl border border-foreground/10 bg-background/85 shadow-lg backdrop-blur-xl" : "max-w-[1540px] bg-transparent"}`}>
        <div className={`grid grid-cols-[minmax(220px,auto)_minmax(0,1fr)_auto] items-center gap-4 px-6 transition-all duration-500 lg:px-8 xl:gap-6 ${isScrolled ? "h-14" : "h-20"}`}>
          <Link href="/" className="flex min-w-[220px] shrink-0 items-baseline gap-2.5">
            <span className={`whitespace-nowrap font-display tracking-normal transition-all duration-500 ${isScrolled ? "text-2xl" : "text-[2rem]"}`}>VideoLingua</span>
            <span className="font-mono text-[10px] uppercase text-muted-foreground">Localization</span>
          </Link>

          <div className="hidden min-w-0 items-center justify-center gap-4 xl:flex 2xl:gap-6">
            {primaryNavLinks.map((link) => (
              <Link key={link.name} href={link.href} className="group relative shrink-0 whitespace-nowrap text-center text-sm leading-tight text-foreground/70 transition-colors hover:text-foreground">
                {link.name}
                <span className="absolute -bottom-1 left-0 h-px w-0 bg-foreground transition-all duration-300 group-hover:w-full" />
              </Link>
            ))}
            <div ref={moreMenuRef} className="relative">
              <button
                type="button"
                id="site-navigation-more-trigger"
                aria-haspopup="menu"
                aria-expanded={isMoreOpen}
                aria-controls="site-navigation-more-menu"
                className="group relative inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-sm leading-tight text-foreground/70 outline-none transition-colors hover:text-foreground focus-visible:text-foreground"
                onClick={() => setIsMoreOpen((value) => !value)}
              >
                More
                <ChevronDown className={`size-3.5 transition-transform duration-300 ${isMoreOpen ? "rotate-180" : ""}`} />
                <span className="absolute -bottom-1 left-0 h-px w-0 bg-foreground transition-all duration-300 group-hover:w-full group-focus-visible:w-full" />
              </button>
              {isMoreOpen ? (
                <div
                  id="site-navigation-more-menu"
                  role="menu"
                  aria-labelledby="site-navigation-more-trigger"
                  className="absolute left-1/2 top-full z-50 mt-4 min-w-48 -translate-x-1/2 rounded-xl border border-foreground/10 bg-background/90 p-2 shadow-xl backdrop-blur-xl"
                >
                  {secondaryNavLinks.map((link) => (
                    <Link
                      key={link.name}
                      href={link.href}
                      role="menuitem"
                      className="block rounded-lg px-3 py-2 text-sm text-foreground/70 outline-none transition-colors hover:bg-foreground/5 hover:text-foreground focus:bg-foreground/5 focus:text-foreground"
                      onClick={() => setIsMoreOpen(false)}
                    >
                      {link.name}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          <div className="hidden min-w-max items-center gap-3 xl:flex">
            <Button asChild variant="outline" size="sm" className="rounded-full border-foreground/20 bg-background/40">
              <Link href="/architecture">View architecture</Link>
            </Button>
            <Button asChild size="sm" className="rounded-full bg-foreground px-5 text-background hover:bg-foreground/90">
              <Link href="/upload">Start a run</Link>
            </Button>
          </div>

          <button type="button" className="p-2 xl:hidden" aria-label="Toggle navigation" onClick={() => setIsOpen((value) => !value)}>
            {isOpen ? <X className="size-6" /> : <Menu className="size-6" />}
          </button>
        </div>
      </nav>

      <div className={`fixed inset-0 z-40 bg-background transition-all duration-500 xl:hidden ${isOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"}`}>
        <div className="flex h-full flex-col px-8 pb-8 pt-28">
          <div className="flex flex-1 flex-col justify-center gap-8">
            {navLinks.map((link, index) => (
              <Link
                key={link.name}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className={`font-display text-5xl transition-all duration-500 ${isOpen ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}
                style={{ transitionDelay: isOpen ? `${index * 75}ms` : "0ms" }}
              >
                {link.name}
              </Link>
            ))}
          </div>
          <Button asChild className="h-14 rounded-full bg-foreground text-background" onClick={() => setIsOpen(false)}>
            <Link href="/upload">Start a localization job</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
