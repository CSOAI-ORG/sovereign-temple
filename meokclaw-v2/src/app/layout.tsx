import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { LOCALES, Locale, LOCALE_METADATA } from "@/i18n/config";
import "./globals.css";
import "@/styles/fonts.css";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale() as Locale;
  const meta = LOCALE_METADATA[locale] ?? LOCALE_METADATA.en;
  return {
    title: locale === 'en' ? "MEOKCLAW v2 — Sovereign Intelligence OS" : undefined,
    description: locale === 'en' ? "Ecosystem of Intelligence. Dual-Brain Sovereign AI." : undefined,
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale() as Locale;

  if (!LOCALES.includes(locale)) {
    notFound();
  }

  const meta = LOCALE_METADATA[locale];
  const messages = await getMessages();

  return (
    <html lang={locale} dir={meta.dir} className="dark">
      <body
        className="antialiased h-screen w-screen overflow-hidden"
        style={{
          backgroundColor: "var(--background)",
          color: "var(--foreground)",
          fontFamily: meta.fontFamily,
        }}
      >
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
