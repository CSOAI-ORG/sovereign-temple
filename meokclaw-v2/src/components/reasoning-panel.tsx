"use client";

import { useState } from "react";

export default function ReasoningPanel({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)]/50 my-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-[var(--surface-raised)]/50 transition-colors"
      >
        <svg className="w-3.5 h-3.5 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <span className="text-[11px] text-[var(--primary)] font-medium">
          {expanded ? "Hide reasoning" : "Show reasoning"}
        </span>
        <span className="text-[10px] text-[var(--muted)] ml-auto">
          {content.length} chars
        </span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-[var(--border)]">
          <pre className="text-[11px] text-[var(--muted)] font-mono whitespace-pre-wrap mt-2 leading-relaxed">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
