# Show HN: MEOKCLAW — Sovereign AI that runs on your hardware

**TL;DR:** I built an open-source AI orchestration platform that lets you run multi-model systems (DeepSeek, Qwen, Llama, Gemma) entirely on your own machines — no API keys needed, no data leaves your network. It has a novel "QuantMan" mode where two AI hemispheres (API + local) debate and converge via a ternary logic system.

**Live demo:** http://192.168.50.105:3000 (local network)
**GitHub:** https://github.com/nicholastempleman/meokclaw
**One-liner install:** `curl -fsSL https://meok.ai/install.sh | bash`

---

## What is it?

MEOKCLAW is a "sovereign intelligence mesh":

- **Dual-Brain Architecture:** Left brain (analytical/Kimi) + Right brain (creative/Owl Alpha), each with API + local model failover
- **QuantMan Mode:** Nested dual-brain with SOV3 neural mediation and HY3 ternary convergence (+1 agree, 0 partial, -1 disagree)
- **Universal Connector:** Talks to Ollama, llama.cpp, vLLM, OpenRouter, MCP servers, A2A agents
- **8-Node Mesh:** M4 MacBook + M2 Air + Vast.ai GPU + 5 cloud models, auto-discovered
- **Zero-Cost Tier:** DeepSeek V4 Flash, Gemma 4, Owl Alpha all free via OpenRouter
- **15-Language Guardrails:** Including Unicode attack detection (bidi, homoglyphs, zero-width)

## Why I built it

I got tired of:
- Sending every query to OpenAI and hoping they don't train on it
- Paying $20/mo for ChatGPT when I have $3K of Apple Silicon sitting on my desk
- Single-model hallucinations with no way to verify
- Vendor lock-in

So I built the system I actually want to use.

## Architecture

```
User → Web UI / Mobile App
          ↓
    Dual-Brain API (:3201)
          ↓
    ┌─────┴─────┐
    ▼           ▼
 Left Mesh   Right Mesh
 Kimi+Qwen   Owl+Llama
    └────┬────┘
         ▼
    SOV3 QuantMan
    (neural scoring)
         ▼
    HY3 Convergence
    +1/0/-1 ternary
```

## What's working now

✅ QuantMan mode tested across 5 languages (EN/ES/ZH/AR/JP)  
✅ Twin Brain: M2 drafts (0.6B) → M4 verifies (8B)  
✅ Council mode: Multi-model BFT consensus  
✅ Semantic cache: 28% hit rate, $0.0003 saved/query  
✅ Guardrails: Blocks injection, Unicode attacks, PII  
✅ iOS/Android apps (Capacitor)  
✅ One-liner install script  

## What's next

- SOC2 prep for enterprise pilots
- Custom model training pipeline
- Hacker News launch (this post!)

## Ask HN

I'd love feedback on:
1. The HY3 ternary convergence logic — is this actually useful or just academic?
2. What would make you switch from ChatGPT/Claude to a self-hosted setup?
3. Enterprise features: what compliance/governance do you need?

---

**Tech stack:** Python 3.14, FastAPI, Next.js 14, TypeScript, Tailwind, Capacitor, Ollama, OpenRouter
**License:** MIT
**Grant:** Applying to NLnet NGI Zero Commons (deadline June 1)
