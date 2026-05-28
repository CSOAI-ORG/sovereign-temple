import Link from "next/link";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4"
         style={{ background: "radial-gradient(ellipse at center, #0f0f1a 0%, #050508 100%)" }}>
      <div className="max-w-2xl text-center">
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <Image
            src="/branding/logo.svg"
            alt="MEOKCLAW"
            width={120}
            height={120}
            priority
            className="drop-shadow-[0_0_24px_rgba(0,212,170,0.15)]"
          />
        </div>

        {/* Status badge */}
        <div className="mb-6">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border"
                style={{ background: "rgba(0,212,170,0.08)", color: "#00d4aa", borderColor: "rgba(0,212,170,0.2)" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#00d4aa] animate-pulse" />
            8 Nodes Online
          </span>
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6 leading-tight"
            style={{ fontFamily: "var(--font-sans)" }}>
          Your AI.{" "}
          <span className="text-[#00d4aa]">Your Hardware.</span>{" "}
          <span className="text-[#e8e8ec]">Your Rules.</span>
        </h1>

        {/* Subhead */}
        <p className="text-lg mb-8 leading-relaxed" style={{ color: "#8b8b9a" }}>
          MEOKCLAW is the sovereign AI operating system. Run a council of
          intelligence models on your own machines — no cloud lock-in, no data
          exfiltration, no subscription rent.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/chat"
            className="px-8 py-3 rounded-xl font-semibold transition shadow-lg"
            style={{ background: "#00d4aa", color: "#050508" }}
          >
            Start Chatting →
          </Link>
          <a
            href="http://localhost:3201/dashboard"
            className="px-8 py-3 rounded-xl font-semibold border transition"
            style={{ background: "#0f0f14", color: "#e8e8ec", borderColor: "#272730" }}
          >
            Open Dashboard
          </a>
        </div>

        {/* Stats */}
        <div className="mt-12 grid grid-cols-3 gap-8 text-sm" style={{ color: "#8b8b9a" }}>
          <div>
            <div className="text-2xl font-bold mb-1" style={{ color: "#e8e8ec" }}>8</div>
            <div>Mesh Nodes</div>
          </div>
          <div>
            <div className="text-2xl font-bold mb-1" style={{ color: "#e8e8ec" }}>$0</div>
            <div>Cost to Start</div>
          </div>
          <div>
            <div className="text-2xl font-bold mb-1" style={{ color: "#e8e8ec" }}>MIT</div>
            <div>Open Source</div>
          </div>
        </div>

        {/* Protocol badges */}
        <div className="mt-10 flex flex-wrap justify-center gap-2 text-xs" style={{ color: "#8b8b9a" }}>
          <span className="px-2 py-1 rounded border" style={{ borderColor: "#272730" }}>MCP</span>
          <span className="px-2 py-1 rounded border" style={{ borderColor: "#272730" }}>A2A</span>
          <span className="px-2 py-1 rounded border" style={{ borderColor: "#272730" }}>x402</span>
          <span className="px-2 py-1 rounded border" style={{ borderColor: "#272730" }}>AGENTS.md</span>
        </div>
      </div>
    </div>
  );
}
