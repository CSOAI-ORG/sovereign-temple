"use client";

import { ConversationBranch, ChatMessage } from "@/lib/api";

function BranchNode({
  branch,
  activeId,
  onSelect,
  depth = 0,
}: {
  branch: ConversationBranch;
  activeId: string;
  onSelect: (id: string) => void;
  depth?: number;
}) {
  const isActive = branch.id === activeId;
  return (
    <div className="relative" style={{ marginLeft: depth * 16 }}>
      <button
        onClick={() => onSelect(branch.id)}
        className={`flex items-center gap-2 w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
          isActive
            ? "bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/20"
            : "text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)]"
        }`}
      >
        <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
        </svg>
        <span className="truncate">{branch.label}</span>
        <span className="text-[10px] text-[var(--muted)] ml-auto shrink-0">
          {branch.messages.length} msgs
        </span>
      </button>
    </div>
  );
}

export default function ConversationFork({
  branches,
  activeId,
  onSelect,
  onFork,
}: {
  branches: ConversationBranch[];
  activeId: string;
  onSelect: (id: string) => void;
  onFork: () => void;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-[var(--foreground)]">Conversation Forks</h3>
        <button
          onClick={onFork}
          className="text-[10px] px-2 py-1 rounded bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
        >
          + Fork here
        </button>
      </div>
      <div className="space-y-1">
        {branches.map((branch) => (
          <BranchNode
            key={branch.id}
            branch={branch}
            activeId={activeId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
