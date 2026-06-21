"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { ChatMessage, ConversationBranch } from "@/lib/api";
import { webllmChat, isWebGPUSupported } from "@/lib/webllm-engine";
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
  const tSidebar = useTranslations("sidebar");
  const tRightPanel = useTranslations("rightPanel");
  const tConversation = useTranslations("conversation");
  const tErrors = useTranslations("errors");
  const tBrain = useTranslations("brain");

  const [selectedModel, setSelectedModel] = useState("gemma4-local");
  const [brainState, setBrainState] = useState<BrainState>({ hemisphere: null });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [branches, setBranches] = useState<ConversationBranch[]>([
    {
      id: "main",
      parentId: null,
      messages: [],
      label: tConversation("mainThread"),
      createdAt: new Date().toISOString(),
    },
  ]);
  const [activeBranchId, setActiveBranchId] = useState("main");
  const [isProcessing, setIsProcessing] = useState(false);
  const [totalCost, setTotalCost] = useState(0);
  const [useLocalInference, setUseLocalInference] = useState(false);
  const [webgpuAvailable, setWebgpuAvailable] = useState(false);
  const [webllmLoading, setWebllmLoading] = useState(false);

  useEffect(() => {
    setWebgpuAvailable(isWebGPUSupported());
  }, []);

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
      let assistantMsg: ChatMessage;

      // Try WebLLM local inference if enabled and available
      if (useLocalInference && webgpuAvailable) {
        setWebllmLoading(true);
        const start = performance.now();
        try {
          const historyMsgs = activeMessages.slice(-6).map((m) => ({
            role: m.role as "user" | "assistant",
            content: m.content,
          }));
          const reply = await webllmChat(
            [...historyMsgs, { role: "user", content: text }],
            { tier: "l1", temperature: 0.7, max_tokens: 1024 }
          );
          const latency = Math.round(performance.now() - start);
          assistantMsg = {
            role: "assistant",
            content: reply,
            metadata: {
              model: "gemma-4b-webllm",
              hemisphere: "left",
              latency_ms: latency,
              cost_usd: 0,
            },
            timestamp: new Date().toISOString(),
          };
          setBrainState({ hemisphere: "left", primaryModel: "gemma-4b-webllm", confidence: 0.85 });
        } catch (webllmErr) {
          // Fallback to cloud API
          console.warn("WebLLM failed, falling back to API:", webllmErr);
          assistantMsg = await callCloudAPI(text);
        } finally {
          setWebllmLoading(false);
        }
      } else {
        assistantMsg = await callCloudAPI(text);
      }

      setBranches((prev) =>
        prev.map((b) =>
          b.id === activeBranchId ? { ...b, messages: [...b.messages, assistantMsg] } : b
        )
      );
    } catch (exc) {
      const errorMsg: ChatMessage = {
        role: "assistant",
        content: tErrors("offline"),
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

  const callCloudAPI = async (text: string): Promise<ChatMessage> => {
    const res = await fetch("http://localhost:3201/api/dual-brain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: activeMessages.slice(-6) }),
    });
    if (!res.ok) throw new Error(tErrors("dualBrainError"));
    const data = await res.json();
    if (data.cost_usd) setTotalCost((c) => c + data.cost_usd);
    setBrainState({
      hemisphere: data.hemisphere,
      primaryModel: data.primary_model,
      secondaryModel: data.secondary_model,
      confidence: data.confidence,
    });
    return {
      role: "assistant",
      content: data.text || tErrors("noResponse"),
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
  };

  const handleFork = () => {
    const newId = `branch-${Date.now()}`;
    const activeBranch = branches.find((b) => b.id === activeBranchId);
    if (!activeBranch) return;

    const newBranch: ConversationBranch = {
      id: newId,
      parentId: activeBranchId,
      messages: [...activeBranch.messages],
      label: tConversation("forkLabel", { n: branches.length }),
      createdAt: new Date().toISOString(),
    };

    setBranches((prev) => [...prev, newBranch]);
    setActiveBranchId(newId);
  };

  const quickActions = [
    { key: "triggerCouncil", label: tRightPanel("triggerCouncil") },
    { key: "neuralRetrain", label: tRightPanel("neuralRetrain") },
    { key: "exportSession", label: tRightPanel("exportSession") },
    { key: "resetContext", label: tRightPanel("resetContext") },
  ];

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
              <h1 className="text-sm font-bold tracking-tight">{tSidebar("title")}</h1>
            </div>
            <p className="text-[10px] text-[var(--muted)]">{tSidebar("subtitle")}</p>
          </div>

          <div className="p-3 border-b border-[var(--border)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2">
              {tSidebar("activeBrain")}
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
              {tSidebar("fallbackModel")}
            </div>
            <ModelSelector selectedId={selectedModel} onSelect={setSelectedModel} />
          </div>

          <div className="p-3 flex-1 overflow-y-auto">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2">
              {tSidebar("context")}
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
            {tRightPanel("dualBrainMetrics")}
          </div>
          <div className="space-y-2">
            <div className="p-2 rounded border border-green-500/30 bg-green-500/5">
              <div className="text-[10px] text-green-400 font-medium">{tRightPanel("premiumActive")}</div>
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("premiumTier")}</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">{tBrain("left")}</div>
              <div className="text-xs font-medium text-[var(--primary)]">{tRightPanel("leftBrainModel")}</div>
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("leftBrainDesc")}</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">{tBrain("right")}</div>
              <div className="text-xs font-medium text-[var(--accent)]">{tRightPanel("rightBrainModel")}</div>
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("rightBrainDesc")}</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("fallbackGPU")}</div>
              <div className="text-xs font-medium text-[var(--muted)]">{tRightPanel("fallbackModel")}</div>
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("fallbackDesc")}</div>
            </div>
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("sessionCost")}</div>
              <div className="text-xs font-mono">${totalCost.toFixed(6)}</div>
            </div>
            {webgpuAvailable && (
              <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
                <div className="text-[10px] text-[var(--muted)]">Local Inference (WebLLM)</div>
                <label className="flex items-center gap-2 mt-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useLocalInference}
                    onChange={(e) => setUseLocalInference(e.target.checked)}
                    className="w-3 h-3 accent-[var(--primary)]"
                  />
                  <span className="text-xs text-[var(--foreground)]">
                    {useLocalInference ? "ON — Gemma 4B in browser" : "OFF — Cloud API"}
                  </span>
                </label>
                {webllmLoading && (
                  <div className="text-[10px] text-[var(--primary)] mt-1 animate-pulse">
                    Loading model...
                  </div>
                )}
              </div>
            )}
            <div className="p-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]">
              <div className="text-[10px] text-[var(--muted)]">{tRightPanel("routerLatency")}</div>
              <div className="text-xs font-mono text-[var(--primary)]">{tRightPanel("latencyValue")}</div>
            </div>
          </div>

          <div className="mt-6 text-[10px] uppercase tracking-wider text-[var(--muted)] mb-3">
            {tRightPanel("quickActions")}
          </div>
          <div className="space-y-1.5">
            {quickActions.map((action) => (
              <button
                key={action.key}
                className="w-full text-left px-2.5 py-1.5 rounded text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors border border-transparent hover:border-[var(--border)]"
              >
                {action.label}
              </button>
            ))}
          </div>
        </aside>
      </div>

      <StatusBar />
    </div>
  );
}
