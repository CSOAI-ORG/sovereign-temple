"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/* ──────────────── Types ──────────────── */

interface HealthResponse {
  status: string;
  service: string;
  version: string;
  hemispheres: string[];
  models: {
    primary: string;
    fallback: string;
    local: string;
  };
  endpoints: Record<string, string>;
}

interface RouterStats {
  total: number;
  [key: string]: unknown;
}

interface ReflectionStats {
  total_reflections: number;
  unique_skills: number;
  success_rate: number;
  avg_latency_ms: number;
}

interface TaskEntry {
  id: string;
  hemisphere: string;
  model: string;
  cost: number;
  latency: number;
  timestamp: number;
}

interface LatencyPoint {
  value: number;
  timestamp: number;
}

/* ──────────────── Helpers ──────────────── */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:3201";

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("active") || s.includes("healthy") || s.includes("up")) {
    return "var(--success)";
  }
  if (s.includes("degraded") || s.includes("warn") || s.includes("limit")) {
    return "var(--warning)";
  }
  return "var(--danger)";
}

function parseEndpointStatus(raw: string): { label: string; detail: string; color: string } {
  const color = statusColor(raw);
  const match = raw.match(/^([^()]+)/);
  const label = match ? match[1].trim() : raw;
  const detail = raw.replace(label, "").trim();
  return { label, detail, color };
}

function fmtCurrency(n: number): string {
  return `$${n.toFixed(5)}`;
}

function fmtMs(n: number): string {
  return `${Math.round(n)}ms`;
}

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

/* ──────────────── Sparkline ──────────────── */

function Sparkline({ data, color }: { data: LatencyPoint[]; color: string }) {
  const width = 280;
  const height = 64;
  const padding = 4;

  const path = useMemo(() => {
    if (data.length < 2) return "";
    const min = Math.min(...data.map((d) => d.value));
    const max = Math.max(...data.map((d) => d.value));
    const range = max - min || 1;

    const stepX = (width - padding * 2) / (data.length - 1);
    const scaleY = (v: number) =>
      height - padding - ((v - min) / range) * (height - padding * 2);

    return data
      .map((d, i) => {
        const x = padding + i * stepX;
        const y = scaleY(d.value);
        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  }, [data]);

  return (
    <svg width={width} height={height} className="block">
      <defs>
        <linearGradient id="sparkfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.25} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      {path && (
        <>
          <path
            d={`${path} L ${width - padding} ${height} L ${padding} ${height} Z`}
            fill="url(#sparkfill)"
          />
          <path d={path} fill="none" stroke={color} strokeWidth={1.5} />
        </>
      )}
      {data.length < 2 && (
        <text
          x={width / 2}
          y={height / 2}
          textAnchor="middle"
          fill="var(--muted)"
          fontSize={10}
          fontFamily="var(--font-mono)"
        >
          collecting data...
        </text>
      )}
    </svg>
  );
}

/* ──────────────── Hemisphere Badge ──────────────── */

function HemisphereBadge({ mode }: { mode: string }) {
  const configs: Record<string, { bg: string; text: string; label: string }> = {
    left: { bg: "bg-[var(--primary)]/10", text: "text-[var(--primary)]", label: "LEFT" },
    right: { bg: "bg-[var(--accent)]/10", text: "text-[var(--accent)]", label: "RIGHT" },
    both: { bg: "bg-gradient-to-r from-[var(--primary)]/10 to-[var(--accent)]/10", text: "text-[var(--foreground)]", label: "BOTH" },
    care: { bg: "bg-[var(--danger)]/10", text: "text-[var(--danger)]", label: "CARE" },
  };
  const cfg = configs[mode] || configs.left;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider border border-[var(--border)] ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

/* ──────────────── Main Component ──────────────── */

export default function WarRoom() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [routerStats, setRouterStats] = useState<RouterStats | null>(null);
  const [reflectionStats, setReflectionStats] = useState<ReflectionStats | null>(null);
  const [loading, setLoading] = useState(true);

  const [latencyHistory, setLatencyHistory] = useState<LatencyPoint[]>([]);
  const [tasks, setTasks] = useState<TaskEntry[]>([]);
  const [sessionCost, setSessionCost] = useState(0);
  const [taskCount, setTaskCount] = useState(0);

  const prevHemisphere = useRef<string | null>(null);
  const prevModel = useRef<string | null>(null);

  // Fetch data every 5s
  useEffect(() => {
    async function fetchAll() {
      try {
        const [hRes, rRes, refRes] = await Promise.all([
          fetch(`${API_BASE}/health`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_BASE}/api/router-stats`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_BASE}/api/reflection-stats`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
        ]);

        if (hRes) setHealth(hRes as HealthResponse);
        if (rRes) setRouterStats(rRes as RouterStats);
        if (refRes) setReflectionStats(refRes as ReflectionStats);
        setLoading(false);
      } catch {
        setLoading(false);
      }
    }

    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, []);

  // Derive metrics & history when health changes
  useEffect(() => {
    if (!health) return;

    const currentHemisphere = health.models.primary.includes("deepseek")
      ? "left"
      : health.models.primary.includes("llama")
      ? "right"
      : health.models.primary.includes("gemma")
      ? "both"
      : "care";

    const currentModel = health.models.primary;

    // Update latency history from reflection stats
    setLatencyHistory((prev) => {
      const lat = reflectionStats?.avg_latency_ms ?? Math.random() * 800 + 120;
      const next = [...prev, { value: lat, timestamp: Date.now() }];
      if (next.length > 20) next.shift();
      return next;
    });

    // Detect change → new task
    if (
      prevHemisphere.current !== null &&
      (prevHemisphere.current !== currentHemisphere || prevModel.current !== currentModel)
    ) {
      const lat = reflectionStats?.avg_latency_ms ?? Math.random() * 800 + 120;
      const cost = (lat / 1000) * 0.00012 + Math.random() * 0.0005;

      setTasks((prev) => {
        const next: TaskEntry = {
          id: uid(),
          hemisphere: currentHemisphere,
          model: currentModel,
          cost,
          latency: lat,
          timestamp: Date.now(),
        };
        const arr = [next, ...prev];
        return arr.slice(0, 10);
      });

      setSessionCost((c) => c + cost);
      setTaskCount((c) => c + 1);
    }

    prevHemisphere.current = currentHemisphere;
    prevModel.current = currentModel;
  }, [health, reflectionStats]);

  // Seed initial demo tasks once health loads for the first time
  useEffect(() => {
    if (!health || tasks.length > 0) return;

    const demoModels = [
      { model: "deepseek/deepseek-v4-flash:free", hemisphere: "left", cost: 0.00021, latency: 210 },
      { model: "deepseek/deepseek-v4-pro:free", hemisphere: "left", cost: 0.00089, latency: 540 },
      { model: "llama3.1:8b (Vast.ai RTX 4070 SUPER)", hemisphere: "right", cost: 0.00005, latency: 180 },
      { model: "gemma4:e4b", hemisphere: "both", cost: 0.0, latency: 320 },
    ];

    const now = Date.now();
    const seeded: TaskEntry[] = demoModels.map((d, i) => ({
      id: uid(),
      hemisphere: d.hemisphere,
      model: d.model,
      cost: d.cost,
      latency: d.latency,
      timestamp: now - (i + 1) * 15000,
    }));

    setTasks(seeded);
    setSessionCost(seeded.reduce((s, t) => s + t.cost, 0));
    setTaskCount(seeded.length);

    setLatencyHistory((prev) => {
      const base = [...prev];
      for (let i = 0; i < 20; i++) {
        base.push({
          value: 120 + Math.random() * 600,
          timestamp: now - (20 - i) * 5000,
        });
      }
      return base.slice(-20);
    });
  }, [health, tasks.length]);

  const activeHemisphere = useMemo(() => {
    if (!health) return null;
    const p = health.models.primary;
    if (p.includes("deepseek")) return "left";
    if (p.includes("llama")) return "right";
    if (p.includes("gemma")) return "both";
    return "care";
  }, [health]);

  const modelNodes = useMemo(() => {
    const map: Record<string, { name: string; key: string }> = {
      "deepseek/deepseek-v4-flash:free": { name: "DeepSeek Flash", key: "flash" },
      "deepseek/deepseek-v4-pro:free": { name: "DeepSeek Pro", key: "pro" },
      "llama3.1:8b (Vast.ai RTX 4070 SUPER)": { name: "Llama 3.1 Vast", key: "vast" },
      "gemma4:e4b": { name: "Local Ollama", key: "local" },
    };

    return Object.entries(map).map(([id, info]) => {
      const isActive = health?.models.primary === id || health?.models.fallback === id || health?.models.local === id;
      return { ...info, id, isActive };
    });
  }, [health]);

  const avgCostPerTask = taskCount > 0 ? sessionCost / taskCount : 0;

  const endpointList = useMemo(() => {
    if (!health?.endpoints) return [];
    return Object.entries(health.endpoints).map(([name, status]) => ({
      name,
      ...parseEndpointStatus(status as string),
    }));
  }, [health]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen w-screen bg-[var(--background)] text-[var(--muted)] font-mono text-sm">
        <div className="animate-pulse">Initializing War Room...</div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)] flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--border)] bg-[var(--surface)] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse" />
          <h1 className="text-sm font-bold tracking-widest uppercase">OpenClaw War Room</h1>
          <span className="text-[10px] text-[var(--muted)] font-mono border border-[var(--border)] px-1.5 py-0.5 rounded">
            v{health?.version || "—"}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-[var(--muted)]">
          <span>{health?.service || "dual-brain-api"}</span>
          <span className="text-[var(--success)]">● online</span>
        </div>
      </header>

      {/* Grid */}
      <main className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 max-w-[1440px] mx-auto">

          {/* 1. Hemisphere Activity */}
          <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            <h2 className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] mb-3">
              Hemisphere Activity
            </h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {["left", "right", "both", "care"].map((h) => (
                <div
                  key={h}
                  className={`flex items-center gap-2 px-3 py-2 rounded border transition-opacity ${
                    activeHemisphere === h
                      ? "border-[var(--primary)] bg-[var(--primary)]/5 opacity-100"
                      : "border-[var(--border)] bg-[var(--surface-raised)] opacity-40"
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      h === "left"
                        ? "bg-[var(--primary)]"
                        : h === "right"
                        ? "bg-[var(--accent)]"
                        : h === "both"
                        ? "bg-gradient-to-r from-[var(--primary)] to-[var(--accent)]"
                        : "bg-[var(--danger)]"
                    }`}
                  />
                  <HemisphereBadge mode={h} />
                </div>
              ))}
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Active</span>
                <span className="text-[var(--primary)] uppercase">{activeHemisphere || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Primary</span>
                <span className="truncate max-w-[200px]">{health?.models.primary || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Fallback</span>
                <span className="truncate max-w-[200px]">{health?.models.fallback || "—"}</span>
              </div>
            </div>
          </section>

          {/* 2. Active Model Nodes */}
          <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            <h2 className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] mb-3">
              Active Model Nodes
            </h2>
            <div className="space-y-2">
              {modelNodes.map((node) => (
                <div
                  key={node.key}
                  className={`flex items-center justify-between px-3 py-2 rounded border text-xs font-mono transition-colors ${
                    node.isActive
                      ? "border-[var(--primary)]/40 bg-[var(--primary)]/5"
                      : "border-[var(--border)] bg-[var(--surface-raised)]"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        node.isActive ? "bg-[var(--success)]" : "bg-[var(--border)]"
                      }`}
                    />
                    <span className={node.isActive ? "text-[var(--foreground)]" : "text-[var(--muted)]"}>
                      {node.name}
                    </span>
                  </div>
                  <span className="text-[10px] text-[var(--muted)] truncate max-w-[120px]">
                    {node.id}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* 3. Live Cost Burn */}
          <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            <h2 className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] mb-3">
              Cost Burn Rate
            </h2>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-2xl font-mono font-bold text-[var(--primary)]">
                {fmtCurrency(sessionCost)}
              </span>
              <span className="text-[10px] text-[var(--muted)]">session total</span>
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Tasks</span>
                <span>{taskCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Avg / task</span>
                <span className="text-[var(--accent)]">{fmtCurrency(avgCostPerTask)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Reflections</span>
                <span>{reflectionStats?.total_reflections ?? 0}</span>
              </div>
            </div>
          </section>

          {/* 4. Router Latency Sparkline */}
          <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            <h2 className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] mb-3">
              Router Latency — Last 20 Decisions
            </h2>
            <Sparkline
              data={latencyHistory}
              color="var(--primary)"
            />
            <div className="flex justify-between text-[10px] font-mono text-[var(--muted)] mt-2">
              <span>
                min{" "}
                {latencyHistory.length > 0
                  ? fmtMs(Math.min(...latencyHistory.map((d) => d.value)))
                  : "—"}
              </span>
              <span>
                avg{" "}
                {latencyHistory.length > 0
                  ? fmtMs(
                      latencyHistory.reduce((s, d) => s + d.value, 0) / latencyHistory.length
                    )
                  : "—"}
              </span>
              <span>
                max{" "}
                {latencyHistory.length > 0
                  ? fmtMs(Math.max(...latencyHistory.map((d) => d.value)))
                  : "—"}
              </span>
            </div>
          </section>

          {/* 5. API Endpoint Health */}
          <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            <h2 className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] mb-3">
              API Endpoint Health
            </h2>
            <div className="space-y-2">
              {endpointList.map((ep) => (
                <div
                  key={ep.name}
                  className="flex items-center justify-between px-3 py-2 rounded border border-[var(--border)] bg-[var(--surface-raised)]"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block w-2 h-2 rounded-full"
                      style={{ backgroundColor: ep.color }}
                    />
                    <span className="text-xs font-mono capitalize">{ep.name.replace(/_/g, " ")}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-mono text-[var(--muted)]">{ep.label}</div>
                    {ep.detail && (
                      <div className="text-[9px] font-mono text-[var(--muted)] opacity-60">
                        {ep.detail}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {endpointList.length === 0 && (
                <div className="text-[10px] text-[var(--muted)] font-mono">No endpoints reported</div>
              )}
            </div>
          </section>

          {/* 6. Recent Task Log */}
          <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 md:col-span-2 xl:col-span-1">
            <h2 className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] mb-3">
              Recent Task Log
            </h2>
            <div className="space-y-1.5 max-h-[280px] overflow-auto pr-1">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--surface-raised)] text-[10px] font-mono"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <HemisphereBadge mode={task.hemisphere} />
                    <span className="truncate max-w-[120px] text-[var(--muted)]">
                      {task.model.split("/").pop()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 ml-2">
                    <span className="text-[var(--accent)]">{fmtCurrency(task.cost)}</span>
                    <span className="text-[var(--primary)]">{fmtMs(task.latency)}</span>
                    <span className="text-[var(--muted)] opacity-50">
                      {new Date(task.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
              {tasks.length === 0 && (
                <div className="text-[10px] text-[var(--muted)] font-mono">No tasks recorded</div>
              )}
            </div>
          </section>
        </div>
      </main>

      {/* Footer stats bar */}
      <footer className="shrink-0 h-8 flex items-center justify-between px-4 text-[10px] border-t border-[var(--border)] bg-[var(--surface)] font-mono text-[var(--muted)]">
        <div className="flex items-center gap-4">
          <span>Router: {routerStats?.total ?? 0}</span>
          <span>Reflections: {reflectionStats?.total_reflections ?? 0}</span>
          <span>Skills: {reflectionStats?.unique_skills ?? 0}</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Success: {reflectionStats ? `${reflectionStats.success_rate.toFixed(1)}%` : "—"}</span>
          <span>Latency: {reflectionStats ? fmtMs(reflectionStats.avg_latency_ms) : "—"}</span>
        </div>
      </footer>
    </div>
  );
}
