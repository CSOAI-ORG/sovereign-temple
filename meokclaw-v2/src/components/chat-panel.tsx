"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage, ToolCall } from "@/lib/api";
import ToolCard from "./tool-card";
import ReasoningPanel from "./reasoning-panel";

function HemisphereBadge({ hemisphere }: { hemisphere?: string }) {
  if (!hemisphere) return null;
  const configs: Record<string, { bg: string; text: string; label: string }> = {
    left: { bg: "bg-[var(--primary)]/10", text: "text-[var(--primary)]", label: "LEFT" },
    right: { bg: "bg-[var(--accent)]/10", text: "text-[var(--accent)]", label: "RIGHT" },
    both: { bg: "bg-gradient-to-r from-[var(--primary)]/10 to-[var(--accent)]/10", text: "text-[var(--foreground)]", label: "FUSION" },
    care: { bg: "bg-[var(--danger)]/10", text: "text-[var(--danger)]", label: "CARE" },
  };
  const cfg = configs[hemisphere] || configs.left;
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded border border-[var(--border)] ${cfg.bg} ${cfg.text} font-bold tracking-wider`}>
      {cfg.label}
    </span>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const isReasoning = msg.role === "reasoning";

  if (isReasoning) {
    return <ReasoningPanel content={msg.content} />;
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-[var(--primary)] text-[var(--background)] rounded-br-md"
            : "bg-[var(--surface-raised)] text-[var(--foreground)] rounded-bl-md border border-[var(--border)]"
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          {!isUser && <HemisphereBadge hemisphere={msg.metadata?.hemisphere} />}
          {!isUser && msg.metadata?.model && (
            <span className="text-[9px] text-[var(--muted)] font-mono truncate max-w-[120px]">
              {msg.metadata.model}
            </span>
          )}
        </div>
        <div className="whitespace-pre-wrap">{msg.content}</div>
        {msg.metadata?.tool_calls && msg.metadata.tool_calls.length > 0 && (
          <div className="mt-2">
            {msg.metadata.tool_calls.map((tc: ToolCall) => (
              <ToolCard key={tc.id} tool={tc} />
            ))}
          </div>
        )}
        {msg.metadata && (
          <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[var(--muted)]">
            {msg.metadata.tokens_out && <span>{msg.metadata.tokens_out} tok</span>}
            {msg.metadata.latency_ms && <span>{msg.metadata.latency_ms}ms</span>}
            {msg.metadata.cost_usd !== undefined && <span>${msg.metadata.cost_usd.toFixed(6)}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPanel({
  messages,
  onSend,
  disabled,
}: {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-[var(--muted)]">
            <div className="text-4xl mb-4">◈</div>
            <h2 className="text-lg font-medium mb-1">MEOKCLAW v2</h2>
            <p className="text-sm">Dual-Brain Sovereign Intelligence</p>
            <p className="text-xs mt-4 opacity-60">Left brain: Kimi K2.6 · Right brain: DeepSeek V4</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
      </div>

      <form
        onSubmit={handleSubmit}
        className="px-4 py-3 border-t border-[var(--border)] bg-[var(--surface)]"
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={disabled ? "Processing..." : "Message the Dual Brain..."}
            disabled={disabled}
            className="flex-1 bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] transition-colors"
          />
          <button
            type="submit"
            disabled={disabled || !input.trim()}
            className="p-2 rounded-lg bg-[var(--primary)] text-[var(--background)] disabled:opacity-40 hover:bg-[var(--primary-dim)] transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
