"use client";

import { useState } from "react";
import { MODEL_PRESETS, ModelPreset, getFallbackChain } from "@/lib/models";

function Tag({ label }: { label: string }) {
  const colorMap: Record<string, string> = {
    local: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    cloud: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    fast: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    free: "bg-lime-500/10 text-lime-400 border-lime-500/20",
    reasoning: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    creative: "bg-pink-500/10 text-pink-400 border-pink-500/20",
    agentic: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  };
  const cls = colorMap[label] || "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${cls}`}>
      {label}
    </span>
  );
}

export default function ModelSelector({
  selectedId,
  onSelect,
}: {
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const selected = MODEL_PRESETS.find((m) => m.id === selectedId) || MODEL_PRESETS[0];
  const fallbacks = getFallbackChain(selected);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:border-[var(--primary)] transition-colors"
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">{selected.name}</div>
            <div className="text-[10px] text-[var(--muted)]">
              {selected.provider} · {selected.maxTokens.toLocaleString()} tokens
            </div>
          </div>
          <svg
            className={`w-4 h-4 text-[var(--muted)] transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-xl overflow-hidden">
          {MODEL_PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => {
                onSelect(preset.id);
                setOpen(false);
              }}
              className={`w-full text-left px-3 py-2.5 hover:bg-[var(--surface-raised)] transition-colors border-b border-[var(--border)] last:border-0 ${
                preset.id === selectedId ? "bg-[var(--primary)]/10" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{preset.name}</span>
                <span className="text-[10px] text-[var(--muted)]">
                  ${preset.costPer1kOutput}/1K
                </span>
              </div>
              <div className="text-[11px] text-[var(--muted)] mt-0.5">{preset.description}</div>
              <div className="flex gap-1 mt-1.5 flex-wrap">
                {preset.tags.map((t) => (
                  <Tag key={t} label={t} />
                ))}
              </div>
            </button>
          ))}
        </div>
      )}

      {fallbacks.length > 0 && (
        <div className="mt-2 text-[10px] text-[var(--muted)]">
          Fallback chain: {fallbacks.map((f) => f.name).join(" → ")}
        </div>
      )}
    </div>
  );
}
