"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ToolCall } from "@/lib/api";

function StatusBadge({ status }: { status: ToolCall["status"] }) {
  const t = useTranslations("tool");
  const colors: Record<string, string> = {
    pending: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    running: "bg-sky-500/10 text-sky-400 border-sky-500/20 animate-pulse",
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    error: "bg-red-500/10 text-red-400 border-red-500/20",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${colors[status]}`}>
      {t(`status.${status}`)}
    </span>
  );
}

export default function ToolCard({ tool }: { tool: ToolCall }) {
  const t = useTranslations("tool");
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden my-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--surface-raised)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-xs font-medium">{tool.name}</span>
          <StatusBadge status={tool.status} />
        </div>
        <svg
          className={`w-3.5 h-3.5 text-[var(--muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-[var(--border)]">
          <div className="mt-2">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-1">{t("arguments")}</div>
            <pre className="text-[11px] bg-[var(--surface-raised)] rounded p-2 overflow-auto font-mono text-[var(--foreground)]">
              {JSON.stringify(tool.arguments, null, 2)}
            </pre>
          </div>
          {tool.result !== undefined && (
            <div className="mt-2">
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-1">{t("result")}</div>
              <pre className="text-[11px] bg-[var(--surface-raised)] rounded p-2 overflow-auto font-mono text-[var(--foreground)]">
                {typeof tool.result === "string" ? tool.result : JSON.stringify(tool.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
