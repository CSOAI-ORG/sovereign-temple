import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e0e0e0] flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl text-center">
        <div className="mb-6">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00d4aa]/10 text-[#00d4aa] text-xs font-medium border border-[#00d4aa]/20">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00d4aa] animate-pulse" />
            8 Nodes Online
          </span>
        </div>
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
          Your AI.{" "}
          <span className="text-[#00d4aa]">Your Hardware.</span>{" "}
          Your Rules.
        </h1>
        <p className="text-lg text-gray-400 mb-8 leading-relaxed">
          MEOKCLAW is the sovereign AI operating system. Run a council of
          intelligence models on your own machines — no cloud lock-in, no data
          exfiltration, no subscription rent.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/chat"
            className="px-8 py-3 rounded-xl bg-[#00d4aa] text-black font-semibold hover:bg-[#00e6b8] transition"
          >
            Start Chatting →
          </Link>
          <a
            href="http://localhost:3201/dashboard"
            className="px-8 py-3 rounded-xl bg-[#151520] text-white font-semibold border border-[#1a1a2e] hover:border-[#00d4aa]/30 transition"
          >
            Open Dashboard
          </a>
        </div>
        <div className="mt-12 grid grid-cols-3 gap-8 text-sm text-gray-500">
          <div>
            <div className="text-2xl font-bold text-white mb-1">8</div>
            <div>Mesh Nodes</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white mb-1">$0</div>
            <div>Cost to Start</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white mb-1">MIT</div>
            <div>Open Source</div>
          </div>
        </div>
      </div>
    </div>
  );
}
