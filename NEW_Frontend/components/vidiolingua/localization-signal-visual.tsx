const lanes = [
  { label: "source", y: 24, tone: "text-foreground/25" },
  { label: "translate", y: 38, tone: "text-primary/35" },
  { label: "voice", y: 52, tone: "text-accent/45" },
  { label: "validate", y: 66, tone: "text-foreground/25" },
  { label: "mp4", y: 80, tone: "text-foreground/35" },
];

const waveform = [16, 26, 20, 34, 24, 40, 18, 30, 22, 36, 26, 28];

export function LocalizationSignalVisual() {
  return (
    <div className="relative h-full min-h-[420px] w-full overflow-hidden border-l border-foreground/5 bg-background/5">
      <div className="absolute inset-0 bg-gradient-to-r from-background via-background/90 to-transparent" />
      <div className="absolute inset-0 opacity-15" style={{ backgroundImage: "linear-gradient(to right, currentColor 1px, transparent 1px)", backgroundSize: "112px 112px" }} />

      <svg className="absolute inset-y-[17%] right-0 h-[66%] w-[86%]" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {lanes.map((lane, index) => (
          <g key={lane.label} className={lane.tone}>
            <path
              d={`M8 ${lane.y} C 28 ${lane.y - 6}, 48 ${lane.y + 6}, 70 ${lane.y} S 92 ${lane.y - 5}, 98 ${lane.y}`}
              fill="none"
              stroke="currentColor"
              strokeWidth={index === 2 ? "0.42" : "0.28"}
              strokeDasharray={index === 2 ? "none" : "3 4"}
              className="signal-route"
              style={{ animationDelay: `${index * 260}ms` }}
            />
            <circle cx={index === 4 ? 86 : 18 + index * 14} cy={lane.y} r={index === 2 ? "1.1" : "0.72"} fill="currentColor" className="signal-pulse" style={{ animationDelay: `${index * 360}ms` }} />
          </g>
        ))}

        <g className="text-foreground/35">
          <line x1="74" y1="24" x2="74" y2="80" stroke="currentColor" strokeWidth="0.2" strokeDasharray="2 4" />
          <circle cx="74" cy="52" r="1.4" fill="currentColor" />
        </g>
      </svg>

      <div className="absolute right-[10%] top-[36%] w-48 opacity-55">
        <div className="mb-3 flex items-end gap-1.5">
          {waveform.map((height, index) => (
            <span key={index} className="signal-bar block w-1.5 bg-foreground/28" style={{ height: `${height}px`, animationDelay: `${index * 70}ms` }} />
          ))}
        </div>
        <div className="flex justify-between font-mono text-[10px] uppercase text-muted-foreground/70">
          <span>subtitle</span>
          <span>voice</span>
        </div>
      </div>

      <div className="absolute bottom-[16%] right-[10%] flex items-center gap-3 font-mono text-[10px] uppercase text-muted-foreground/70">
        {lanes.map((lane) => (
          <span key={lane.label}>{lane.label}</span>
        ))}
      </div>
    </div>
  );
}
