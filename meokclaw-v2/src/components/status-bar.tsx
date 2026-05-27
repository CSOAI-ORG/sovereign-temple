"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  fetchSov3Health,
  fetchMeokMcpHealth,
  fetchMeokApiHealth,
  HealthStatus,
} from "@/lib/api";

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full mr-1.5 ${
        ok ? "bg-[var(--success)]" : "bg-[var(--danger)]"
      }`}
    />
  );
}

export default function StatusBar() {
  const t = useTranslations("status");
  const [sov3, setSov3] = useState<HealthStatus | null>(null);
  const [mcp, setMcp] = useState<HealthStatus | null>(null);
  const [api, setApi] = useState<HealthStatus | null>(null);
  const [tokensPerSec, setTokensPerSec] = useState(0);
  const [cost, setCost] = useState(0);

  useEffect(() => {
    const check = async () => {
      try {
        setSov3(await fetchSov3Health());
      } catch {
        setSov3(null);
      }
      try {
        setMcp(await fetchMeokMcpHealth());
      } catch {
        setMcp(null);
      }
      try {
        setApi(await fetchMeokApiHealth());
      } catch {
        setApi(null);
      }
    };
    check();
    const iv = setInterval(check, 10000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const iv = setInterval(() => {
      setTokensPerSec((t) => {
        const next = Math.max(0, t + (Math.random() - 0.5) * 40);
        return Math.min(450, Math.max(20, next));
      });
      setCost((c) => c + Math.random() * 0.0001);
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  return (
    <footer className="h-8 flex items-center justify-between px-4 text-xs border-t border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center gap-4">
        <span className="flex items-center">
          <StatusDot ok={!!sov3} />
          {t("sov3")} {sov3 ? "3101" : t("down")}
        </span>
        <span className="flex items-center">
          <StatusDot ok={!!mcp} />
          {t("mcp")} {mcp ? "3102" : t("down")}
        </span>
        <span className="flex items-center">
          <StatusDot ok={!!api} />
          {t("api")} {api ? "3200" : t("down")}
        </span>
      </div>

      <div className="flex items-center gap-4 text-[var(--muted)]">
        <span className="font-mono">
          {t("tokensPerSec", { count: tokensPerSec.toFixed(0) })}
        </span>
        <span className="font-mono">
          {t("sessionCost", { amount: cost.toFixed(4) })}
        </span>
        <span className="font-mono text-[var(--primary)]">
          {sov3?.components?.consciousness
            ? t("consciousness", {
                pct: Math.round(
                  (sov3.components.consciousness.consciousness_level || 0) * 100
                ),
              })
            : t("consciousnessUnknown")}
        </span>
      </div>
    </footer>
  );
}
