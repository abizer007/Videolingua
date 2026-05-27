"use client";

import { CheckCircle2 } from "lucide-react";
import { allLanguages, sarvamLanguages, xttsLanguages, type LanguageCapability } from "@/lib/language-capabilities";

type LanguageSelectorProps = {
  selectedCode: string;
  onSelect: (code: string) => void;
};

function LanguageButton({
  language,
  selected,
  onClick,
}: {
  language: LanguageCapability;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group relative border p-4 text-left transition-all duration-300 hover:-translate-y-0.5 ${
        selected ? "border-foreground bg-foreground text-background" : "border-foreground/10 bg-background hover:border-foreground/25"
      }`}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-[0.16em] opacity-65">{language.code}</span>
        {selected && <CheckCircle2 className="size-4" />}
      </div>
      <div className="font-medium">{language.name}</div>
      <div className={`mt-3 h-1 bg-gradient-to-r ${language.accentClass}`} />
    </button>
  );
}

export function LanguageSelector({ selectedCode, onSelect }: LanguageSelectorProps) {
  const selected = allLanguages.find((language) => language.code === selectedCode) ?? allLanguages[0];

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="border border-foreground/10 p-5">
          <h3 className="mb-2 font-display text-3xl">XTTS supported</h3>
          <p className="mb-4 text-sm text-muted-foreground">Speaker-reference voice for global languages. Reference audio is required before the job starts.</p>
          <div className="grid grid-cols-2 gap-2">
            {xttsLanguages.map((language) => (
              <LanguageButton key={language.code} language={language} selected={language.code === selectedCode} onClick={() => onSelect(language.code)} />
            ))}
          </div>
        </div>

        <div className="border border-foreground/10 p-5">
          <h3 className="mb-2 font-display text-3xl">Sarvam Indian-language TTS</h3>
          <p className="mb-4 text-sm text-muted-foreground">Managed regional speech through Sarvam AI. Not exact speaker cloning.</p>
          <div className="grid grid-cols-2 gap-2">
            {sarvamLanguages.map((language) => (
              <LanguageButton key={language.code} language={language} selected={language.code === selectedCode} onClick={() => onSelect(language.code)} />
            ))}
          </div>
        </div>
      </div>

      <div className="border border-foreground/10 bg-foreground/[0.03] p-5">
        <div className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">Selected voice behavior</div>
        <h3 className="mb-2 font-display text-3xl">{selected.voiceLabel}</h3>
        <p className="text-muted-foreground">{selected.description}</p>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
          <div className="border border-foreground/10 p-3">
            <div className="text-muted-foreground">Reference audio</div>
            <div className="font-medium">{selected.referenceAudio === "required" ? "Required" : "Optional"}</div>
          </div>
          <div className="border border-foreground/10 p-3">
            <div className="text-muted-foreground">Translation</div>
            <div className="font-medium">{selected.translationBackend}</div>
          </div>
          <div className="border border-foreground/10 p-3">
            <div className="text-muted-foreground">Policy</div>
            <div className="font-medium">No silent fallback</div>
          </div>
        </div>
      </div>
    </div>
  );
}
