"use client";

import { useState, useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/navigation";
import { LOCALES, Locale, LOCALE_METADATA } from "@/i18n/config";

export default function LocaleSwitcher() {
  const t = useTranslations("localeSwitcher");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filtered = LOCALES.filter((l) => {
    const meta = LOCALE_METADATA[l];
    const q = search.toLowerCase();
    return (
      meta.label.toLowerCase().includes(q) ||
      meta.nativeLabel.toLowerCase().includes(q) ||
      l.toLowerCase().includes(q)
    );
  });

  const handleSelect = (next: Locale) => {
    setOpen(false);
    startTransition(() => {
      router.replace(pathname, { locale: next });
    });
  };

  const currentMeta = LOCALE_METADATA[locale];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={isPending}
        className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors border border-[var(--border)]"
        aria-label={t("label")}
      >
        <span className="font-medium">{currentMeta.nativeLabel}</span>
        <svg
          className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute bottom-full right-0 mb-1 w-56 rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-xl z-50 overflow-hidden">
            <div className="p-2 border-b border-[var(--border)]">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t("search")}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded px-2 py-1 text-xs text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)]"
                autoFocus
              />
            </div>
            <div className="max-h-48 overflow-y-auto">
              {filtered.map((l) => {
                const meta = LOCALE_METADATA[l];
                const isActive = l === locale;
                return (
                  <button
                    key={l}
                    onClick={() => handleSelect(l)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors ${
                      isActive
                        ? "bg-[var(--primary)]/10 text-[var(--primary)]"
                        : "text-[var(--foreground)] hover:bg-[var(--surface-raised)]"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{meta.nativeLabel}</span>
                      <span className="text-[var(--muted)]">{meta.label}</span>
                    </span>
                    {isActive && (
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </button>
                );
              })}
              {filtered.length === 0 && (
                <div className="px-3 py-2 text-xs text-[var(--muted)]">{t("search")}</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
