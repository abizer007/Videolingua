import { sarvamLanguages, xttsLanguages } from "@/lib/language-capabilities";

export function LanguageSupportSection() {
  return (
    <section id="languages" className="bg-foreground py-24 text-background lg:py-32">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-12">
        <div className="mb-14 grid gap-8 lg:grid-cols-[0.8fr_1fr] lg:items-end">
          <div>
            <span className="mb-6 inline-flex items-center gap-3 font-mono text-sm text-background/55">
              <span className="h-px w-8 bg-background/30" />
              Supported languages
            </span>
            <h2 className="font-display text-4xl tracking-normal lg:text-6xl">Two language families, two honest voice paths.</h2>
          </div>
          <p className="max-w-2xl text-lg leading-relaxed text-background/62">
            The UI separates XTTS speaker-reference languages from Sarvam managed regional-language TTS, so the expected voice behavior is clear before upload.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="border border-background/10 p-6">
            <h3 className="mb-2 font-display text-3xl">XTTS speaker-reference</h3>
            <p className="mb-6 text-sm text-background/55">Reference audio required for speaker style preservation where supported.</p>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {xttsLanguages.map((language) => (
                <div key={language.code} className="border border-background/10 px-3 py-2">
                  <div className="font-medium">{language.name}</div>
                  <div className="font-mono text-xs text-background/45">{language.code}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-background/10 p-6">
            <h3 className="mb-2 font-display text-3xl">Sarvam managed Indian-language TTS</h3>
            <p className="mb-6 text-sm text-background/55">Natural regional speech. Not exact speaker cloning.</p>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {sarvamLanguages.map((language) => (
                <div key={language.code} className="border border-background/10 px-3 py-2">
                  <div className="font-medium">{language.name}</div>
                  <div className="font-mono text-xs text-background/45">{language.code}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
