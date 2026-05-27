"use client";

interface BrainVisualizerProps {
  hemisphere: "left" | "right" | "both" | "care" | null;
  primaryModel?: string;
  secondaryModel?: string;
  confidence?: number;
}

export default function BrainVisualizer({
  hemisphere,
  primaryModel,
  secondaryModel,
  confidence = 0,
}: BrainVisualizerProps) {
  if (!hemisphere) {
    return (
      <div className="flex items-center gap-2 text-[var(--muted)] text-xs">
        <div className="w-3 h-3 rounded-full bg-[var(--border)]" />
        <span>Standby</span>
      </div>
    );
  }

  const configs: Record<string, { color: string; icon: string; label: string }> = {
    left: { color: "bg-[var(--primary)]", icon: "◀", label: "LEFT BRAIN" },
    right: { color: "bg-[var(--accent)]", icon: "▶", label: "RIGHT BRAIN" },
    both: { color: "bg-gradient-to-r from-[var(--primary)] to-[var(--accent)]", icon: "◈", label: "FUSION" },
    care: { color: "bg-[var(--danger)]", icon: "◉", label: "CARE MODE" },
  };

  const cfg = configs[hemisphere] || configs.left;

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${cfg.color} ${hemisphere === "both" ? "animate-pulse" : ""}`} />
          <span className="text-xs font-bold tracking-wider" style={{ color: hemisphere === "care" ? "var(--danger)" : "var(--foreground)" }}>
            {cfg.icon} {cfg.label}
          </span>
        </div>
        <span className="text-[10px] text-[var(--muted)]">
          {Math.round(confidence * 100)}% conf
        </span>
      </div>

      <div className="space-y-1">
        {primaryModel && (
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-[var(--muted)]">Primary</span>
            <span className="font-mono text-[var(--primary)] truncate max-w-[140px]">{primaryModel}</span>
          </div>
        )}
        {secondaryModel && (
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-[var(--muted)]">Secondary</span>
            <span className="font-mono text-[var(--accent)] truncate max-w-[140px]">{secondaryModel}</span>
          </div>
        )}
      </div>

      {hemisphere === "both" && (
        <div className="mt-2 text-[10px] text-[var(--muted)] border-t border-[var(--border)] pt-2">
          Speculative consensus active. Both hemispheres consulted.
        </div>
      )}
    </div>
  );
}
