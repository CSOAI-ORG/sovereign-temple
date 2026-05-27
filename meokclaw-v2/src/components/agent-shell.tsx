"use client";

import { useState } from "react";
import { ChatMessage, ConversationBranch } from "@/lib/api";
import ChatPanel from "./chat-panel";
import ModelSelector from "./model-selector";
import ConversationFork from "./conversation-fork";
import BrainVisualizer from "./brain-visualizer";
import StatusBar from "./status-bar";

interface BrainState {
  hemisphere: "left" | "right" | "both" | "care" | null;
  primaryModel?: string;
  secondaryModel?: string;
  confidence?: number;
}

export default function AgentShell() {
  const [selectedModel, setSelectedModel] = useState("gemma4-local");
  const [brainState, setBrainState] = useState<BrainState>({ hemisphere: null });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [branches, setBranches] = useState<ConversationBranch[]>([
    {
      id: "main",
      parentId: null,
      messages: [],
      label: "Main thread",
      createdAt: new Date().toISOString(),
    },
  ]);
  const [activeBranchId, setActiveBranchId] = useState("main");
  const [isProcessing, setIsProcessing] = useState(false);
  const [totalCost, setTotalCost] = useState(0);

  const activeMessages = branches.find((b) => b.id === activeBranchId)?.messages || [];

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setBranches((prev) =>
      prev.map((b) =>
        b.id === activeBranchId ? { ...b, messages: [...b.messages, userMsg] } : b
      )
    );
    setIsProcessing(true);
    setBrainState({ hemisphere: null });

    try {
      // Call the dual-brain API
      const res = await fetch("http://localhost:3201/api/dual-brain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: activeMessages.slice(-6) }),
      });

      if (!res.ok) throw new Error("Dual brain API error");
      const data = await res.json();

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.text || "[No response]",
        metadata: {
          model: data.primary_model,
          hemisphere: data.hemisphere,
          tokens_in: data.tokens_in,
          tokens_out: data.tokens_out,
          latency_ms: data.latency_ms,
          cost_usd: data.cost_usd,
        },
        timestamp: new Date().toISOString(),
      };

      setBrainState({
        hemisphere: data.hemisphere,
        primaryModel: data.primary_model,
        secondaryModel: data.secondary_model,
        confidence: data.confidence,
      });

      if (data.cost_usd) {
        setTotalCost((c) => c + data.cost_usd);
      }

      setBranches((prev) =>
        prev.map((b) =>
          b.id === activeBranchId ? { ...b, messages: [...b.messages, assistantMsg] } : b
        )
      );
    } catch (exc) {
      const errorMsg: ChatMessage = {
        role: "assistant",
        content: "⚠️ Dual brain temporarily offline. Using local fallback.",
        metadata: { hemisphere: "care", model: "local-fallback" },
        timestamp: new Date().toISOString(),
      };
      setBranches((prev) =>
        prev.map((b) =>
          b.id === activeBranchId ? { ...b, messages: [...b.messages, errorMsg] } : b
        )
      );
      setBrainState({ hemisphere: "care" });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFork = () => {
    const newId = `branch-${Date.now()}`;
    const activeBranch = branches.find((b) => b.id === activeBranchId);
    if (!activeBranch) return;

    const newBranch: ConversationBranch = {
      id: newId,
      parentId: activeBranchId,
      messages: [...activeBranch.messages],
      label: `Fork ${branches.length}`,
      createdAt: new Date().toISOString(),
    };

    setBranches((prev) => [...prev, newBranch]);
    setActiveBranchId(newId);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[var(--background)]">
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 border-r border-[var(--border)] bg-[var(--surface)] flex flex-col">
          <div className="p-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-6 h-6 rounded bg-[var(--primary)] flex items-center justify-center text-[var(--background)] text-xs font-bold">
                M
              </div>
              <h1 className="text-sm font-bold tracking-tight">MEOKCLAW</h1>
            </div>
            <p className="text-[10px] text-[var(--muted)]">Dual-Brain Sovereign OS v2.0</p>
          </div>

          <div className="p-3 border-b border-[var(--border)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2">
              Active Brain
            </div>
            <BrainVisualizer
              hemisphere={brainState.hemisphere}
              primaryModel={brainState.primaryModel}
              secondaryModel={brainState.secondaryModel}
              confidence={brainState.confidence}
            />
          </div>

          <div className="p-3 border-b border-[var(--border)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2">
              Fallback Model
            </div>
            <ModelSelector selectedId={selectedModel} onSelect={setSelectedModel} />
          </div>

          <div className="p-3 flex-1 overflow-y-auto">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2">
              Context
            </div>
            <ConversationFork
              branches={branches}
              activeId={activeBranchId}
              onSelect={setActiveBranchId}
              onFork={handleFork}
            />
          </div>
        </aside>

        {/* Main Chat */}
        <main className="flex-1 flex flex-col min-w-0">
          <ChatPanel messages={activeMessages} onSend={handleSend} disabled={isProcessing} />
        </main>

        {/* Right Panel */}
        <aside className="w-72 border-l border-[var(--border)] bg-[var(--surface)] p-4 overflow-y-auto hidden xl:block">
          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-3">
            Dual-Brain Metrics
          </div>
          <div className="space-y-2">
            <div className="p-2 rounded border border-green-500/30 bg-green-500/5">
              <div className="text-[10px] text-green-400 font-medium">● Premium Active ($25)</div>
              <div className="text-[10px] text-[var(--muted)]">OpenRouter paid tier</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">Left Brain</div>
              <div className="text-xs font-medium text-[var(--primary)]">DeepSeek V4 Flash</div>
              <div className="text-[10px] text-[var(--muted)]">Fast · Coding · Cheap (~$0.0001)</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">Right Brain</div>
              <div className="text-xs font-medium text-[var(--accent)]">DeepSeek V4 Pro</div>
              <div className="text-[10px] text-[var(--muted)]">Reasoning · Synthesis (~$0.001-0.005)</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">Fallback GPU</div>
              <div className="text-xs font-medium text-[var(--muted)]">Llama 3.1 8B (Vast.ai)</div>
              <div className="text-[10px] text-[var(--muted)]">Free · Reliable · 2.5s</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">Session Cost</div>
              <div className="text-xs font-mono">${totalCost.toFixed(6)}</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">Router Latency</div>
              <div className="text-xs font-mono text-[var(--primary)]">~0.006ms</div>
            </div>
          </div>

          <div className="mt-6 text-[10px] uppercase tracking-wider text-[var(--muted)] mb-3">
            Quick Actions
          </div>
          <div className="space-y-1.5">
            {["Trigger Council", "Neural Retrain", "Export Session", "Reset Context"].map(
              (action) => (
                <button
                  key={action}
                  className="w-full text-left px-2.5 py-1.5 rounded text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors border border-transparent hover:border-[var(--border)]"
                >
                  {action}
                </button>
              )
            )}
          </div>
        </aside>
      </div>

      <StatusBar />
    </div>
  );
}
