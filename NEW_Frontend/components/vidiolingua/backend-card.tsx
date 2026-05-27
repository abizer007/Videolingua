import type { LucideIcon } from "lucide-react";

export function BackendCard({
  title,
  subtitle,
  body,
  icon: Icon,
  accent,
  details,
}: {
  title: string;
  subtitle: string;
  body: string;
  icon: LucideIcon;
  accent: string;
  details: string[];
}) {
  return (
    <div className="border border-foreground/10 bg-card">
      <div className={`h-2 bg-gradient-to-r ${accent}`} />
      <div className="p-6">
        <Icon className="mb-8 size-8 text-muted-foreground" />
        <h2 className="mb-2 font-display text-4xl">{title}</h2>
        <div className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">{subtitle}</div>
        <p className="mb-6 leading-relaxed text-muted-foreground">{body}</p>
        <div className="grid gap-2">
          {details.map((detail) => (
            <div key={detail} className="border border-foreground/10 px-3 py-2 text-sm">{detail}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
