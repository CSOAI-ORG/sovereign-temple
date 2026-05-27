import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MEOKCLAW v2 — Sovereign Intelligence OS",
  description: "Ecosystem of Intelligence. Step3 aesthetic. Western frontend. OpenCode model routing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased h-screen w-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
        {children}
      </body>
    </html>
  );
}
