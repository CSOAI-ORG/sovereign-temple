import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { LOCALES, Locale, LOCALE_METADATA } from "@/i18n/config";
import "./globals.css";
import "@/styles/fonts.css";

export const viewport: Viewport = {
  themeColor: "#0a0a10",
  width: "device-width",
  initialScale: 1,
};

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale() as Locale;
  const meta = LOCALE_METADATA[locale] ?? LOCALE_METADATA.en;
  const title = locale === 'en'
    ? "MEOKCLAW — Sovereign AI Orchestration"
    : undefined;
  const description = locale === 'en'
    ? "Dual-brain sovereign AI operating system. Run a council of intelligence models on your own hardware — no cloud lock-in, no data exfiltration, no subscription rent."
    : undefined;

  return {
    title,
    description,
    metadataBase: new URL("https://dist-xi-nine-56.vercel.app"),
    icons: {
      icon: "/branding/icon.svg",
      shortcut: "/favicon.ico",
      apple: "/branding/apple-touch-icon.png",
    },
    openGraph: {
      title: title ?? "MEOKCLAW",
      description: description ?? "Sovereign AI Orchestration",
      url: "https://dist-xi-nine-56.vercel.app",
      siteName: "MEOKCLAW",
      images: [
        {
          url: "/branding/og-image.png",
          width: 1200,
          height: 630,
          alt: "MEOKCLAW — Sovereign AI Orchestration",
        },
      ],
      locale: locale.replace('-', '_'),
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: title ?? "MEOKCLAW",
      description: description ?? "Sovereign AI Orchestration",
      images: ["/branding/og-image.png"],
    },
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
