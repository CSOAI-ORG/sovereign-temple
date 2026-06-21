"use client";

import React, { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Users, Crown, Share2, Clock, DollarSign, Sparkles, Shield, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CouncilResult {
  response_id: string;
  consensus_text: string;
  consensus_score: number;
  disagreeing_models: string[];
  total_cost_usd: number;
  total_latency_ms: number;
  models: Array<{
    model: string;
    text: string;
    cost_usd: number;
    latency_ms: number;
    tokens_in: number;
    tokens_out: number;
  }>;
  share_url: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:3201";

const AVAILABLE_MODELS = [
  { id: "deepseek-v4-flash", name: "DeepSeek Flash", cost: "$0.0001/1K", speed: "Fast" },
  { id: "deepseek-v4-pro", name: "DeepSeek Pro", cost: "$0.0015/1K", speed: "Smart" },
  { id: "kimi-k2.6", name: "Kimi K2.6", cost: "$0.002/1K", speed: "Powerful" },
  { id: "llama3.1:8b", name: "Llama 3.1 (Local)", cost: "FREE", speed: "Private" },
];

export default function CouncilPage() {
  const [prompt, setPrompt] = useState("");
  const [selectedModels, setSelectedModels] = useState<string[]>(["deepseek-v4-flash", "deepseek-v4-pro", "kimi-k2.6"]);
  const [result, setResult] = useState<CouncilResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [consensusThreshold, setConsensusThreshold] = useState(0.6);
  const [copied, setCopied] = useState(false);
  const router = useRouter();

  const toggleModel = (modelId: string) => {
    setSelectedModels((prev) =>
      prev.includes(modelId)
        ? prev.filter((m) => m !== modelId)
        : [...prev, modelId]
    );
  };

  const runCouncil = useCallback(async () => {
    if (!prompt.trim() || selectedModels.length < 2) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/council`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          models: selectedModels,
          consensus_threshold: consensusThreshold,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [prompt, selectedModels, consensusThreshold]);

  const handleShare = async () => {
    if (!result) return;
    const url = `${window.location.origin}/council?prompt=${encodeURIComponent(prompt)}&models=${selectedModels.join(",")}`;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-[var(--background)] overflow-hidden">
      {/* Header */}
      <header className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-violet-500/20">
            <Users className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">Council Mode</h1>
            <p className="text-[10px] text-[var(--muted)]">
              Multi-model BFT consensus — no single point of failure
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => router.push("/")} className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-all">Chat</button>
          <button onClick={() => router.push("/arena")} className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-all">Arena</button>
          <button onClick={() => router.push("/war-room")} className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-all">War Room</button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel — Input */}
        <div className="w-1/3 min-w-[320px] border-r border-[var(--border)] flex flex-col">
          <div className="p-4 border-b border-[var(--border)]">
            <h2 className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider mb-3">
              Select Council Members
            </h2>
            <div className="space-y-2">
              {AVAILABLE_MODELS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => toggleModel(m.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-left text-xs transition-all ${
                    selectedModels.includes(m.id)
                      ? "border-violet-500/50 bg-violet-500/10 text-violet-300"
                      : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)]"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border flex items-center justify-center ${selectedModels.includes(m.id) ? "bg-violet-500 border-violet-500" : "border-[var(--border)]"}`}>
                      {selectedModels.includes(m.id) && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <span className="font-medium">{m.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="text-emerald-400">{m.cost}</span>
                    <span className="text-[var(--muted)]">{m.speed}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[var(--muted)]">Consensus Threshold</span>
              <span className="text-xs font-mono text-violet-400">{Math.round(consensusThreshold * 100)}%</span>
            </div>
            <input type="range" min="0.3" max="1" step="0.1" value={consensusThreshold} onChange={(e) => setConsensusThreshold(parseFloat(e.target.value))} className="w-full accent-violet-500" />
          </div>

          <div className="flex-1 p-4">
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runCouncil(); }} placeholder="Ask the council anything... (Cmd+Enter to run)" className="w-full h-full min-h-[120px] bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3 text-xs resize-none focus:outline-none focus:border-violet-500/50 placeholder:text-[var(--muted)]" />
          </div>

          <div className="p-4 border-t border-[var(--border)]">
            <button onClick={runCouncil} disabled={loading || !prompt.trim() || selectedModels.length < 2} className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium flex items-center justify-center gap-2 transition-all shadow-lg shadow-violet-500/20">
              {loading ? <><div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Consulting Council...</> : <><Users className="w-3.5 h-3.5" />Run Council ({selectedModels.length} models)</>}
            </button>
          </div>
        </div>

        {/* Right panel — Results */}
        <div className="flex-1 overflow-y-auto">
          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-[var(--muted)]">
              <Users className="w-12 h-12 mb-4 opacity-20" />
              <p className="text-sm">The Council awaits your question</p>
              <p className="text-xs mt-1 opacity-60">Select models, type a prompt, and watch consensus form</p>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="flex items-center gap-3 mb-4">
                {selectedModels.map((m, i) => (
                  <motion.div key={m} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.1 }} className="w-10 h-10 rounded-lg bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-violet-400 animate-pulse" />
                  </motion.div>
                ))}
              </div>
              <p className="text-sm text-[var(--muted)]">Consulting {selectedModels.length} council members...</p>
            </div>
          )}

          {result && (
            <div className="p-6 space-y-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Crown className="w-4 h-4 text-violet-400" />
                  <h3 className="text-sm font-semibold text-violet-300">Consensus</h3>
                  <span className="ml-auto text-xs font-mono bg-violet-500/20 text-violet-300 px-2 py-0.5 rounded-full">{Math.round(result.consensus_score * 100)}% agreement</span>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.consensus_text}</p>
              </motion.div>

              <div>
                <h3 className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider mb-3">Individual Responses</h3>
                <div className="grid grid-cols-1 gap-3">
                  <AnimatePresence>
                    {result.models.map((m, i) => (
                      <motion.div key={m.model} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }} className={`rounded-xl border p-4 ${result.consensus_text === m.text ? "border-emerald-500/30 bg-emerald-500/5" : "border-[var(--border)] bg-[var(--surface)]"}`}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium">{m.model}</span>
                            {result.consensus_text === m.text && <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded-full">Consensus</span>}
                            {result.disagreeing_models.includes(m.model) && <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-full">Dissent</span>}
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-[var(--muted)]">
                            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{m.latency_ms}ms</span>
                            <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />${m.cost_usd.toFixed(4)}</span>
                          </div>
                        </div>
                        <p className="text-xs text-[var(--muted)] leading-relaxed line-clamp-4">{m.text}</p>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>

              <div className="flex items-center justify-between py-3 border-t border-[var(--border)] text-xs text-[var(--muted)]">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />Total: ${result.total_cost_usd.toFixed(4)}</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{result.total_latency_ms}ms</span>
                  <span className="flex items-center gap-1"><Shield className="w-3 h-3" />BFT Consensus</span>
                </div>
                <button onClick={handleShare} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--surface-raised)] transition-all">
                  <Share2 className="w-3 h-3" />{copied ? "Copied!" : "Share"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
