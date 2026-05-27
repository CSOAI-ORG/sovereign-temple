"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

/* ────────────────────────────────────────────────────────────────
   Types
   ──────────────────────────────────────────────────────────────── */

interface ArenaModel {
  id: string;
  name: string;
  provider: string;
  costPer1kInput: number;
  costPer1kOutput: number;
  color: string;
  gradient: string;
  badge: string;
}

interface ArenaResult {
  modelId: string;
  text: string;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  timeToFirstTokenMs: number;
  totalTimeMs: number;
  status: "idle" | "loading" | "streaming" | "done" | "error" | "simulated";
  error?: string;
  voted: boolean;
}

/* ────────────────────────────────────────────────────────────────
   Model registry
   ──────────────────────────────────────────────────────────────── */

const ARENA_MODELS: ArenaModel[] = [
  {
    id: "deepseek-flash",
    name: "DeepSeek Flash",
    provider: "OpenRouter",
    costPer1kInput: 0.00007,
    costPer1kOutput: 0.00011,
    color: "#00D4AA",
    gradient: "from-emerald-400/20 to-teal-500/5",
    badge: "Fast",
  },
  {
    id: "deepseek-pro",
    name: "DeepSeek Pro",
    provider: "OpenRouter",
    costPer1kInput: 0.00055,
    costPer1kOutput: 0.00219,
    color: "#8B5CF6",
    gradient: "from-violet-400/20 to-purple-500/5",
    badge: "Reasoning",
  },
  {
    id: "kimi-k2-6",
    name: "Kimi K2.6",
    provider: "Moonshot",
    costPer1kInput: 0.0003,
    costPer1kOutput: 0.0006,
    color: "#3B82F6",
    gradient: "from-blue-400/20 to-sky-500/5",
    badge: "Long Context",
  },
  {
    id: "llama-3-1-vast",
    name: "Llama 3.1 8B",
    provider: "Vast.ai",
    costPer1kInput: 0.00002,
    costPer1kOutput: 0.00004,
    color: "#F59E0B",
    gradient: "from-amber-400/20 to-orange-500/5",
    badge: "Local GPU",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "OpenAI",
    costPer1kInput: 0.0025,
    costPer1kOutput: 0.01,
    color: "#10B981",
    gradient: "from-green-400/20 to-emerald-500/5",
    badge: "Reference",
  },
];

/* ────────────────────────────────────────────────────────────────
   Simulated responses (used when local API is unavailable)
   ──────────────────────────────────────────────────────────────── */

const SIMULATED_RESPONSES: Record<string, string> = {
  "deepseek-flash":
    "I'll analyze this step by step. The key insight is that efficient token usage directly correlates with lower inference costs. Flash models excel at straightforward tasks where reasoning depth isn't critical.",
  "deepseek-pro":
    "This is a nuanced question that benefits from chain-of-thought reasoning. Let me work through the implications systematically:\n\n1. **Cost structure**: Input tokens are typically 2-4x cheaper than output tokens across providers.\n2. **Latency trade-offs**: Faster first-token latency often means less reasoning depth.\n3. **Quality spectrum**: There's a clear pareto frontier where you pay more for either speed or depth, rarely both.\n\nThe optimal strategy depends on your use case's sensitivity to each dimension.",
  "kimi-k2-6":
    "Kimi's architecture emphasizes long-context understanding. For this query, the model processes the full context window efficiently, maintaining coherence across extended reasoning chains. The cost profile is competitive for mid-complexity tasks.",
  "llama-3-1-vast":
    "Running on consumer-grade hardware via Vast.ai rentals. Response quality is solid for general queries, though latency varies with GPU availability. The unbeatable cost ($0.00002/1K input) makes this ideal for high-volume, low-complexity workloads.",
  "gpt-4o":
    "As the reference benchmark, GPT-4o provides a consistent quality baseline. While not the cheapest option, its reliability and broad capability make it the standard against which other models are measured. Cost is the primary trade-off at scale.",
};

/* ────────────────────────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────────────────────────── */

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatCost(n: number): string {
  if (n < 0.0001) return `<$0.0001`;
  return `$${n.toFixed(4)}`;
}

function estimateTokens(text: string): number {
  // Rough estimate: ~4 chars per token for English
  return Math.max(1, Math.ceil(text.length / 4));
}

/* ────────────────────────────────────────────────────────────────
   Sub-components
   ──────────────────────────────────────────────────────────────── */

function ModelBadge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="text-[10px] font-semibold px-2 py-0.5 rounded-full border"
      style={{
        color,
        borderColor: `${color}40`,
        background: `${color}10`,
      }}
    >
      {label}
    </span>
  );
}

function MetricRow({
  label,
  value,
  unit,
  highlight = false,
}: {
  label: string;
  value: string;
  unit?: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-[11px] py-0.5">
      <span className="text-[var(--muted)]">{label}</span>
      <span
        className={`font-mono ${highlight ? "text-[var(--primary)]" : "text-[var(--foreground)]"}`}
      >
        {value}
        {unit && <span className="text-[var(--muted)] ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

function ResultCard({
  model,
  result,
  onVote,
  isWinner,
}: {
  model: ArenaModel;
  result: ArenaResult;
  onVote: () => void;
  isWinner: boolean;
}) {
  const t = useTranslations("arena");
  const tTags = useTranslations("modelSelector");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current && result.status === "streaming") {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [result.text, result.status]);

  const isLoading = result.status === "loading" || result.status === "streaming";
  const isSimulated = result.status === "simulated";
  const isError = result.status === "error";
  const isDone = result.status === "done";

  const translatedBadge = (() => {
    const key = model.badge.toLowerCase();
    if (["local", "cloud", "fast", "free", "reasoning", "creative", "agentic"].includes(key)) {
      return tTags(`tags.${key}` as any);
    }
    return model.badge;
  })();

  return (
    <div
      className={`relative flex flex-col rounded-xl border overflow-hidden transition-all duration-500 ${
        isWinner
          ? "border-[var(--primary)]/50 glow-primary scale-[1.01]"
          : "border-[var(--border)] hover:border-[var(--border)]"
      }`}
      style={{ background: "var(--surface)" }}
    >
      {/* Header */}
      <div
        className={`px-4 py-3 border-b border-[var(--border)] bg-gradient-to-r ${model.gradient}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ background: model.color, boxShadow: `0 0 8px ${model.color}60` }}
            />
            <span className="text-sm font-semibold">{model.name}</span>
          </div>
          <ModelBadge label={translatedBadge} color={model.color} />
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-[var(--muted)]">{model.provider}</span>
          <span className="text-[10px] font-mono text-[var(--muted)]">
            ${model.costPer1kInput.toFixed(5)} in / ${model.costPer1kOutput.toFixed(5)} out
          </span>
        </div>
      </div>

      {/* Response body */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-[180px] max-h-[420px] overflow-y-auto p-4 text-sm leading-relaxed whitespace-pre-wrap"
      >
        {isLoading && result.text === "" && (
          <div className="flex flex-col gap-2 animate-pulse">
            <div className="h-3 bg-[var(--border)] rounded w-3/4" />
            <div className="h-3 bg-[var(--border)] rounded w-full" />
            <div className="h-3 bg-[var(--border)] rounded w-5/6" />
            <div className="h-3 bg-[var(--border)] rounded w-1/2" />
          </div>
        )}

        {isError && (
          <div className="text-[var(--danger)] text-sm">
            ⚠️ {result.error || t("requestFailed")}
          </div>
        )}

        {isSimulated && (
          <>
            <div className="mb-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-amber-500/20 bg-amber-500/10 text-amber-400 text-[10px]">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {t("simulated")}
            </div>
            <div className="text-[var(--foreground)]/80">{result.text}</div>
          </>
        )}

        {(isDone || (isLoading && result.text !== "")) && (
          <div className="text-[var(--foreground)]">{result.text}</div>
        )}

        {isLoading && result.text !== "" && (
          <span className="inline-block w-1.5 h-4 ml-0.5 bg-[var(--primary)] animate-pulse align-middle" />
        )}
      </div>

      {/* Metrics footer */}
      <div className="px-4 py-3 border-t border-[var(--border)] bg-[var(--surface-raised)]/50">
        <MetricRow
          label={t("timeToFirstToken")}
          value={result.timeToFirstTokenMs > 0 ? formatMs(result.timeToFirstTokenMs) : "—"}
          highlight={result.timeToFirstTokenMs > 0 && result.timeToFirstTokenMs < 500}
        />
        <MetricRow
          label={t("totalTime")}
          value={result.totalTimeMs > 0 ? formatMs(result.totalTimeMs) : "—"}
        />
        <MetricRow label={t("tokensIn")} value={result.tokensIn.toLocaleString()} />
        <MetricRow label={t("tokensOut")} value={result.tokensOut.toLocaleString()} />
        <div className="mt-2 pt-2 border-t border-[var(--border)]/50 flex items-center justify-between">
          <span className="text-[11px] text-[var(--muted)]">{t("cost")}</span>
          <span className="text-sm font-mono font-semibold text-[var(--primary)]">
            {formatCost(result.costUsd)}
          </span>
        </div>
      </div>

      {/* Vote button */}
      <button
        onClick={onVote}
        disabled={!isDone && !isSimulated}
        className={`w-full py-2.5 text-xs font-semibold tracking-wide uppercase transition-all duration-300 border-t ${
          result.voted
            ? "bg-[var(--primary)]/20 text-[var(--primary)] border-[var(--primary)]/30"
            : isDone || isSimulated
            ? "text-[var(--muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10 border-[var(--border)]"
            : "text-[var(--muted)]/40 cursor-not-allowed border-[var(--border)]"
        }`}
      >
        {result.voted ? (
          <span className="flex items-center justify-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            {t("bestResponse")}
          </span>
        ) : (
          t("voteBest")
        )}
      </button>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────
   Main component
   ──────────────────────────────────────────────────────────────── */

export default function ModelArena() {
  const t = useTranslations("arena");
  const tNav = useTranslations("nav");

  const [prompt, setPrompt] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([
    "deepseek-flash",
    "deepseek-pro",
    "llama-3-1-vast",
  ]);
  const [results, setResults] = useState<Record<string, ArenaResult>>({});
  const [isRunning, setIsRunning] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const abortRefs = useRef<Record<string, AbortController>>({});

  // Load from URL params on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const urlPrompt = params.get("prompt");
    const urlModels = params.get("models");
    if (urlPrompt) {
      setPrompt(decodeURIComponent(urlPrompt));
    }
    if (urlModels) {
      const ids = urlModels.split(",").filter((id) => ARENA_MODELS.some((m) => m.id === id));
      if (ids.length > 0) setSelectedIds(ids);
    }
  }, []);

  const toggleModel = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }, []);

  const handleVote = useCallback((modelId: string) => {
    setResults((prev) => ({
      ...prev,
      [modelId]: { ...prev[modelId], voted: true },
    }));
  }, []);

  const winnerId = Object.entries(results).find(([, r]) => r.voted)?.[0] || null;

  const runArena = async () => {
    if (!prompt.trim() || selectedIds.length === 0) return;
    setIsRunning(true);
    setShareUrl(null);

    // Initialize results
    const initial: Record<string, ArenaResult> = {};
    selectedIds.forEach((id) => {
      initial[id] = {
        modelId: id,
        text: "",
        tokensIn: estimateTokens(prompt),
        tokensOut: 0,
        costUsd: 0,
        timeToFirstTokenMs: 0,
        totalTimeMs: 0,
        status: "loading",
        voted: false,
      };
    });
    setResults(initial);

    // Use the arena API for real parallel model execution
    const apiModelMap: Record<string, string> = {
      "deepseek-flash": "deepseek-v4-flash",
      "deepseek-pro": "deepseek-v4-pro",
      "kimi-k2": "kimi-k2.6",
      "llama-3.1": "llama3.1:8b",
    };

    try {
      const res = await fetch("http://localhost:3201/api/arena", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          models: selectedIds.map((id) => apiModelMap[id] || id),
        }),
      });

      if (!res.ok) throw new Error("Arena API error");

      const data = await res.json();

      // Map API results back to component model IDs
      const reverseMap: Record<string, string> = Object.fromEntries(
        Object.entries(apiModelMap).map(([k, v]) => [v, k])
      );

      data.models.forEach((m: any) => {
        const compId = reverseMap[m.model] || m.model;
        setResults((prev) => ({
          ...prev,
          [compId]: {
            ...prev[compId],
            status: "done",
            text: m.text,
            tokensIn: m.tokens_in,
            tokensOut: m.tokens_out,
            costUsd: m.cost_usd,
            timeToFirstTokenMs: Math.round(m.latency_ms * 0.3),
            totalTimeMs: m.latency_ms,
          },
        }));
      });
    } catch {
      // Fallback: run models individually with simulation
      await Promise.all(selectedIds.map((id) => runModelSimulated(id, prompt)));
    }

    setIsRunning(false);
  };

  const runModelSimulated = async (modelId: string, userPrompt: string) => {
    const model = ARENA_MODELS.find((m) => m.id === modelId)!;
    const abort = new AbortController();
    abortRefs.current[modelId] = abort;

    const setModelResult = (patch: Partial<ArenaResult>) => {
      setResults((prev) => ({
        ...prev,
        [modelId]: { ...prev[modelId], ...patch },
      }));
    };

    const ttfb = 300 + Math.random() * 1200;
    const total = ttfb + 800 + Math.random() * 2000;

    const fullText = SIMULATED_RESPONSES[modelId] || "[Simulated response placeholder]";
    const tokensOut = estimateTokens(fullText);
    const costInput = (estimateTokens(userPrompt) / 1000) * model.costPer1kInput;
    const costOutput = (tokensOut / 1000) * model.costPer1kOutput;

    setModelResult({
      status: "streaming",
      text: "",
      tokensOut,
      costUsd: costInput + costOutput,
      timeToFirstTokenMs: ttfb,
      totalTimeMs: total,
    });

    // Simulate streaming
    let streamed = "";
    const chunks = fullText.split(" ");
    for (let i = 0; i < chunks.length; i++) {
      if (abort.signal.aborted) return;
      streamed += (i > 0 ? " " : "") + chunks[i];
      setModelResult({ text: streamed });
      await new Promise((r) => setTimeout(r, 15 + Math.random() * 25));
    }

    setModelResult({ status: "simulated", text: fullText });
  };

  const handleShare = () => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    params.set("prompt", encodeURIComponent(prompt));
    params.set("models", selectedIds.join(","));
    const url = `${window.location.origin}/arena?${params.toString()}`;
    setShareUrl(url);
    navigator.clipboard?.writeText(url).catch(() => {});
  };

  const handleStop = () => {
    Object.values(abortRefs.current).forEach((ctrl) => ctrl.abort());
    setIsRunning(false);
    setResults((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((k) => {
        if (next[k].status === "loading" || next[k].status === "streaming") {
          next[k] = { ...next[k], status: "error", error: t("stoppedByUser") };
        }
      });
      return next;
    });
  };

  const allDoneOrError = selectedIds.every((id) => {
    const r = results[id];
    return r && (r.status === "done" || r.status === "simulated" || r.status === "error");
  });

  return (
    <div className="flex flex-col h-screen w-full bg-[var(--background)] overflow-hidden">
      {/* Top bar */}
      <header className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--primary)] to-[var(--primary-dim)] flex items-center justify-center text-[var(--background)] text-sm font-bold shadow-lg shadow-[var(--primary)]/20">
            M
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">{t("title")}</h1>
            <p className="text-[10px] text-[var(--muted)]">{t("subtitle")}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {shareUrl && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/10 text-[var(--primary)] text-[11px]">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {t("linkCopied")}
            </div>
          )}
          <button
            onClick={handleShare}
            disabled={!prompt.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--border)] hover:bg-[var(--surface-raised)] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            {t("share")}
          </button>
          <a href="/council" className="text-[11px] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors px-2 py-1 rounded hover:bg-[var(--surface-raised)]">{tNav("council")}</a>
          <a href="/war-room" className="text-[11px] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors px-2 py-1 rounded hover:bg-[var(--surface-raised)]">{tNav("warRoom")}</a>
          <a href="/" className="text-[11px] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors px-2 py-1 rounded hover:bg-[var(--surface-raised)]">← {tNav("os")}</a>
        </div>
      </header>

      {/* Prompt section */}
      <div className="shrink-0 px-6 py-4 border-b border-[var(--border)] bg-gradient-to-b from-[var(--surface)]/40 to-transparent">
        <div className="max-w-5xl mx-auto">
          <label className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2 block">
            {t("yourPrompt")}
          </label>
          <div className="flex gap-3">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !isRunning) {
                  e.preventDefault();
                  runArena();
                }
              }}
              placeholder={t("promptPlaceholder")}
              rows={2}
              className="flex-1 px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] text-sm text-[var(--foreground)] placeholder:text-[var(--muted)]/50 focus:outline-none focus:border-[var(--primary)]/50 focus:ring-1 focus:ring-[var(--primary)]/20 resize-none transition-all"
              disabled={isRunning}
            />
            <div className="flex flex-col gap-2">
              {isRunning ? (
                <button
                  onClick={handleStop}
                  className="h-full px-5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 text-[var(--danger)] text-sm font-medium hover:bg-[var(--danger)]/20 transition-all flex items-center gap-2"
                >
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t("stop")}
                </button>
              ) : (
                <button
                  onClick={runArena}
                  disabled={!prompt.trim() || selectedIds.length === 0}
                  className="h-full px-5 rounded-xl bg-gradient-to-r from-[var(--primary)] to-[var(--primary-dim)] text-[var(--background)] text-sm font-semibold shadow-lg shadow-[var(--primary)]/20 hover:shadow-[var(--primary)]/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  {t("runArena")}
                </button>
              )}
            </div>
          </div>

          {/* Model toggles */}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] mr-1">
              {t("models")}
            </span>
            {ARENA_MODELS.map((m) => {
              const active = selectedIds.includes(m.id);
              return (
                <button
                  key={m.id}
                  onClick={() => !isRunning && toggleModel(m.id)}
                  disabled={isRunning}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all ${
                    active
                      ? "border-[var(--primary)]/40 bg-[var(--primary)]/10 text-[var(--primary)]"
                      : "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--muted)] hover:text-[var(--foreground)]"
                  } disabled:cursor-not-allowed`}
                >
                  <div
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: active ? m.color : "var(--muted)", opacity: active ? 1 : 0.4 }}
                  />
                  {m.name}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Results grid */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {selectedIds.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[var(--muted)]">
            <svg className="w-12 h-12 mb-3 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <p className="text-sm">{t("selectModel")}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 max-w-[1600px] mx-auto">
            {selectedIds.map((id) => {
              const model = ARENA_MODELS.find((m) => m.id === id)!;
              const result = results[id] || {
                modelId: id,
                text: "",
                tokensIn: 0,
                tokensOut: 0,
                costUsd: 0,
                timeToFirstTokenMs: 0,
                totalTimeMs: 0,
                status: "idle",
                voted: false,
              };
              return (
                <ResultCard
                  key={id}
                  model={model}
                  result={result}
                  onVote={() => handleVote(id)}
                  isWinner={winnerId === id}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Cost summary bar */}
      {allDoneOrError && selectedIds.length > 0 && (
        <div className="shrink-0 px-6 py-3 border-t border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-6">
              <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{t("arenaSummary")}</span>
              <div className="flex items-center gap-4 text-[11px]">
                {selectedIds.map((id) => {
                  const r = results[id];
                  if (!r || r.status === "error") return null;
                  const m = ARENA_MODELS.find((x) => x.id === id)!;
                  return (
                    <div key={id} className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full" style={{ background: m.color }} />
                      <span className="text-[var(--muted)]">{m.name}:</span>
                      <span className="font-mono text-[var(--foreground)]">{formatCost(r.costUsd)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="text-[11px] text-[var(--muted)]">
              {t("savingsVsGpt")}{" "}
              <span className="font-mono text-[var(--primary)]">
                {(() => {
                  const gpt = results["gpt-4o"];
                  if (!gpt || gpt.status === "error") return "—";
                  const others = selectedIds
                    .filter((id) => id !== "gpt-4o")
                    .map((id) => results[id])
                    .filter((r) => r && r.status !== "error");
                  if (others.length === 0) return "—";
                  const cheapest = Math.min(...others.map((r) => r.costUsd));
                  const saved = gpt.costUsd - cheapest;
                  const pct = gpt.costUsd > 0 ? (saved / gpt.costUsd) * 100 : 0;
                  return `${pct.toFixed(0)}%`;
                })()}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
