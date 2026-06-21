/* MEOKCLAW Chat — Sovereign AI Interface v2.1 */
"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Copy, Check, Bot, User, Sparkles, Loader2, BrainCircuit, GitMerge, Users, Zap } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string;
  latency?: number;
  cost?: number;
  hy3_state?: number;
  partnership_score?: number;
  convergence_method?: string;
}

const MODELS = [
  { id: "auto", name: "🧠 Auto (Dual-Brain)", desc: "Routes to best model" },
  { id: "openrouter/owl-alpha", name: "🦉 Owl Alpha", desc: "Free, 1M ctx, agentic" },
  { id: "deepseek/deepseek-v4-flash", name: "⚡ DeepSeek V4", desc: "Free, fast reasoning" },
  { id: "google/gemma-4-27b-it", name: "👁️ Gemma 4 27B", desc: "Free, vision" },
  { id: "qwen3:8b", name: "🔥 Qwen3 8B (Local)", desc: "M4, fast, private" },
  { id: "qwen3:4b", name: "💨 Qwen3 4B (M2)", desc: "Mesh, lightweight" },
];

const MODES = [
  { id: "auto", name: "Auto", icon: Zap, desc: "Smart routing", endpoint: "/api/dual-brain" },
  { id: "quantman", name: "QuantMan", icon: BrainCircuit, desc: "Nested dual-brain + SOV3", endpoint: "/api/quantman" },
  { id: "council", name: "Council", icon: Users, desc: "Multi-model BFT vote", endpoint: "/api/council" },
  { id: "twin", name: "Twin", icon: GitMerge, desc: "M2 draft → M4 verify", endpoint: "/api/twin/chat" },
];

import { API_CONFIG } from "../../config/api";
const API_BASE = API_CONFIG.getBaseUrl();

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Welcome to MEOKCLAW v2.1 — QuantMan Mode is now available.\n\nYour sovereign AI mesh runs nested dual-brains: each hemisphere is API + local, mediated by SOV3, converged via HY3 ternary logic.\n\nSelect a mode from the sidebar and ask anything.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("auto");
  const [selectedMode, setSelectedMode] = useState("auto");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const modeCfg = MODES.find((m) => m.id === selectedMode) || MODES[0];
      const body: any = { message: userMsg.content, max_tokens: 1024 };
      if (selectedModel !== "auto" && selectedMode === "auto") body.model = selectedModel;
      if (selectedMode !== "auto") body.mode = selectedMode;

      const res = await fetch(`${API_BASE}${modeCfg.endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.text || data.consensus_text || "[No response]",
        model: data.model,
        latency: data.latency_ms,
        cost: data.cost_usd,
        hy3_state: data.hy3_state,
        partnership_score: data.partnership_score,
        convergence_method: data.convergence_method,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content: `[Error: ${err.message}]` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const hy3Badge = (state?: number) => {
    if (state === 1) return <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">HY3 +1</span>;
    if (state === 0) return <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">HY3 0</span>;
    if (state === -1) return <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400">HY3 -1</span>;
    return null;
  };

  return (
    <div className="flex h-screen bg-[#0a0a0f] text-[#e0e0e0]">
      {/* Sidebar */}
      <aside className="w-64 border-r border-[#1a1a2e] hidden md:flex flex-col">
        <div className="p-4 border-b border-[#1a1a2e]">
          <h1 className="text-xl font-bold text-[#00d4aa] flex items-center gap-2">
            <Sparkles size={20} /> MEOKCLAW
          </h1>
          <p className="text-xs text-gray-500 mt-1">Sovereign AI Mesh v2.1</p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* Mode Selector */}
          <div className="p-4 pb-2">
            <p className="text-xs text-gray-600 uppercase tracking-wider mb-2">Mode</p>
            {MODES.map((m) => {
              const Icon = m.icon;
              return (
                <button
                  key={m.id}
                  onClick={() => setSelectedMode(m.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition flex items-center gap-2 ${
                    selectedMode === m.id
                      ? "bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/30"
                      : "text-gray-400 hover:bg-[#1a1a2e]"
                  }`}
                >
                  <Icon size={14} />
                  <div>
                    <div className="font-medium">{m.name}</div>
                    <div className="text-xs text-gray-500">{m.desc}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Model Selector */}
          <div className="px-4 pb-4">
            <p className="text-xs text-gray-600 uppercase tracking-wider mb-2 mt-2">Model Override</p>
            {MODELS.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedModel(m.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition ${
                  selectedModel === m.id
                    ? "bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/30"
                    : "text-gray-400 hover:bg-[#1a1a2e]"
                }`}
              >
                <div className="font-medium">{m.name}</div>
                <div className="text-xs text-gray-500">{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-[#1a1a2e] text-xs text-gray-600">
          <p>8 nodes online</p>
          <p>M4 + M2 + Vast + 5 cloud</p>
        </div>
      </aside>

      {/* Main Chat */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-14 border-b border-[#1a1a2e] flex items-center px-4 justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00d4aa] animate-pulse" />
            <span className="text-sm font-medium">Mesh Online</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="px-2 py-0.5 rounded bg-[#1a1a2e]">
              {MODES.find((m) => m.id === selectedMode)?.name}
            </span>
            {selectedMode === "auto" && selectedModel !== "auto" && (
              <span>{MODELS.find((m) => m.id === selectedModel)?.name}</span>
            )}
          </div>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center flex-shrink-0">
                    <Bot size={16} className="text-[#00d4aa]" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-[#1a3a3a] text-white rounded-br-md"
                      : "bg-[#151520] text-[#e0e0e0] rounded-bl-md border border-[#1a1a2e]"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.role === "assistant" && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 flex-wrap">
                      {msg.model && <span className="truncate max-w-[200px]">{msg.model}</span>}
                      {msg.latency && <span>{msg.latency}ms</span>}
                      {msg.cost !== undefined && <span>${msg.cost.toFixed(4)}</span>}
                      {hy3Badge(msg.hy3_state)}
                      {msg.partnership_score !== undefined && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
                          P={msg.partnership_score.toFixed(2)}
                        </span>
                      )}
                      <button
                        onClick={() => copyToClipboard(msg.content, msg.id)}
                        className="hover:text-[#00d4aa] transition"
                      >
                        {copiedId === msg.id ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-lg bg-[#1a3a3a] flex items-center justify-center flex-shrink-0">
                    <User size={16} className="text-emerald-400" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
                <Loader2 size={16} className="text-[#00d4aa] animate-spin" />
              </div>
              <div className="bg-[#151520] border border-[#1a1a2e] rounded-2xl rounded-bl-md px-4 py-3 text-sm text-gray-400">
                {selectedMode === "quantman" ? "Running nested dual-brain + SOV3 mediation + HY3 convergence..." : "Thinking..."}
              </div>
            </motion.div>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[#1a1a2e]">
          <div className="max-w-3xl mx-auto relative">
            <textarea
              placeholder={selectedMode === "quantman" ? "Ask anything... QuantMan will route through 4 models" : "Ask anything... your data stays local"}
              rows={1}
              className="w-full bg-[#151520] border border-[#1a1a2e] rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[#00d4aa]/50 resize-none max-h-32"
              style={{ minHeight: 48 }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
            />
            <button
              disabled={loading || !input.trim()}
              onClick={sendMessage}
              className="absolute right-2 bottom-2 w-8 h-8 rounded-lg bg-[#00d4aa] flex items-center justify-center text-black hover:bg-[#00e6b8] transition disabled:opacity-30 disabled:hover:bg-[#00d4aa]"
            >
              <Send size={14} />
            </button>
          </div>
          <p className="text-center text-xs text-gray-600 mt-2">
            {selectedMode === "quantman"
              ? "QuantMan: Left (Kimi+Qw2.5) ↔ SOV3 ↔ Right (Owl+Llama) → HY3 converge"
              : "MEOKCLAW routes through local models first. Cloud models only when needed."}
          </p>
        </div>
      </main>
    </div>
  );
}
