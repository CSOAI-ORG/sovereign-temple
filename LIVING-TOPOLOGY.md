# LIVING TOPOLOGY — MEOKCLAW Ecosystem Map

> **Version:** 2.4.0 | **Date:** 2026-05-27 | **Status:** Active

---

## The Ecosystem at a Glance

```
MEOKCLAW ECOSYSTEM — "The Sovereign Brain"

USERS          SOV3           MESH           CLOUD
• iOS (Siri)   • Agent        • M2 Sidekick  • Vast.ai
• Android      • Swarm (63)   • M4 Orch.     • Lambda
• Web (Next)   • BFT Vote     • Speculative  • RunPod
• Windows      • Task Queue   • Decoding     • CoreWeave
• macOS        • Memory       • Health Dash
• WatchOS
      |            |              |              |
      v            v              v              v
   INFERENCE CASCADE (L0 -> L3)
   L0 Intent -> L1 Edge (M2) -> L2 Local (M4) -> L3 Cloud (Vast)
   2ms          50ms             300ms             2000ms
                    |
                    v
   SAFETY & GOVERNANCE
   Guardrails -> RAGuard -> GVU -> BFT Council -> Audit Log
```

---

## Component Inventory

### Frontend

| Component | Tech | Path | Status |
|-----------|------|------|--------|
| MEOKCLAW Web | Next.js 14, TS, Tailwind | meokclaw-v2/ | Active |
| War Room | Next.js + Recharts | war-room.tsx | Active |
| Model Arena | Next.js | model-arena.tsx | Active |
| Brain Viz | Canvas/WebGL | brain-visualizer.tsx | Active |
| Ops Room | Static HTML | dashboard/opsroom/ | Built |
| Republic Dashboard | Static HTML | dashboard/republic/ | Built |
| Predictive Dashboard | Static HTML | dashboard/predictive/ | Built |
| iOS App | Swift, MLX, SwiftUI | mobile/ios/ | Scaffold |
| Android App | Kotlin, MediaPipe | mobile/android/ | Scaffold |
| Siri Shortcuts | iOS + FastAPI | siri_integration.py | Active |
| Android Bridge | FastAPI + WebSocket | android_mesh_bridge.py | Built |
| Windows Bridge | Python + ONNX | windows_bridge.py | New |

### Backend

| Component | Tech | Path | Port | Status |
|-----------|------|------|------|--------|
| Dual-Brain API | FastAPI | dual_brain_api.py | 3201 | Active |
| Mesh Orchestrator | FastAPI | mac_mesh_orchestrator.py | 3202 | Built |
| M2 Sidekick v2 | FastAPI | m2_sidekick_v2.py | 8080 | Built |
| M4 Sovereign Node | asyncio | m4_sovereign_node.py | — | Active |
| Health Dashboard | FastAPI + Rich | mesh_health_dashboard.py | 9090 | Built |
| Speculative Bridge | httpx | speculative_bridge.py | — | Built |
| Inference Cascade | Python | inference-cascade/ | — | Active |
| Model Gateway | httpx | model_gateway.py | — | Active |
| LLM Router | Intent classifier | llm_providers/router.py | — | Active |
| Guardrails | Regex + LLM | guardrails.py | — | Active |
| RAGuard | SHA-256, JSONL | raguard/engine.py | — | Built |
| Voice Pipeline | Piper, Whisper | voice_pipeline/ | — | Active |

### AI Models

| Location | Models | Status |
|----------|--------|--------|
| M2 Local | Qwen3-0.6B, 1.8B, 4B, nomic-embed | Active |
| M4 Local | Qwen3-8B, Coder-8B, Gemma3-12B | Active |
| Vast Cloud | Gemma-4-27B, DeepSeek-V4 | Configured |
| Browser (WebLLM) | Gemma-3-4B, Qwen2.5-7B, Phi-3 | Built |
| iOS (MLX) | Gemma-3-4B, Qwen2.5-7B | Scaffold |
| Android (MediaPipe) | Gemma-2B, 4B, Phi-2 | Scaffold |
| Council Mode | 12 models via OpenRouter | Active |

---

## Performance Reality Check

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| L0 Intent | < 5ms | ~2ms | Green |
| L1 TTFT (M2) | < 100ms | ~50ms | Green |
| L2 TTFT (M4) | < 200ms | ~150ms | Green |
| L3 TTFT (Vast) | < 1000ms | ~800ms | Green |
| Speculative Speedup | 2.0x | 1.5-2.5x | Green |
| Guardrails Block Rate | 100% | 66.7% en, 100% i18n | Yellow |
| Council Latency P50 | < 5000ms | 29091ms | Red |
| i18n Coverage | 100% | 15 locales | Green |
| RTL Support | ar only | Complete | Green |

---

## Trust Zones

**TIER 1 — ULTRA-TRUSTED (No network)**
- Local Ollama on M2/M4, Siri on-device speech, iOS MLX, local guardrails

**TIER 2 — TRUSTED LAN (mDNS/Bonjour)**
- M2-M4 speculative decoding, mesh health checks, SOV3 gossip

**TIER 3 — TRUSTED CLOUD (Encrypted)**
- Vast.ai SSH tunnel, OpenRouter API, Redis cloud sync

**TIER 4 — UNTRUSTED (Sandboxed)**
- Web search, third-party MCPs, public APIs via OpenRouter
