# MEOKCLAW Universal Deployment Architecture v3.0
## "Eat All Platforms, All Protocols, All Models"

**Date:** 2026-05-27  
**Status:** Strategic Architecture — Implementation Phase  
**Goal:** 100/100 on iOS, Android, Windows, Web SaaS, Browser Extension, Chrome, with minimal GPU

---

## 1. The Google Secret: How They Use Less Space & GPU

Google doesn't run Gemini Pro on your phone. They run a **cascade of increasingly capable models**, routing each query to the smallest model that can handle it.

| Tier | Google Equivalent | Params | Use Case | Where It Runs |
|------|------------------|--------|----------|---------------|
| L0 | Gemma 4 270M / 1B | 0.27–1B | Intent classification, routing, guardrails | On-device, always |
| L1 | Gemini Nano / Gemma 4B | 2–4B | Quick answers, summarization, autocomplete | On-device, NPU/GPU |
| L2 | Gemini Flash / Gemma 12B | 8–12B | Standard chat, reasoning, tool use | On-device (premium) or edge server |
| L3 | Gemini Pro / DeepSeek-R1 | 100B+ | Complex reasoning, coding, multi-step agents | Cloud, GPU cluster |

**Key insight:** 80% of user queries can be answered by an L1 model. Only 5% need L3. The router is everything.

### Google's Efficiency Techniques (Reproducible)

1. **Sparse MoE Activation** — Only 5-10% of parameters active per token (DeepSeek R1: 671B total, 37B active)
2. **Post-Training Quantization (PTQ)** — 4-bit INT4 via QAT preserves quality at 1/4 size
3. **Speculative Decoding (EAGLE-3)** — Draft model predicts 2-6 tokens ahead, target model verifies in parallel
4. **KV Cache Optimization** — PagedAttention-style memory management reduces VRAM by 50%+
5. **Distillation** — Train small models to imitate large ones (Gemma 4B = 90% of Gemini Pro on common tasks)
6. **System-Level Model Hosting** — Android AICore hosts models in separate process; apps call via IPC. OS manages thermal throttling, memory pressure, NPU scheduling.

---

## 2. MEOKCLAW Split-Inference Cascade

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY (any platform)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L0 ROUTER (Gemma 1B / Qwen 0.5B / Phi-1) — On-device       │
│  • Intent classification (5ms)                               │
│  • Capability scoring: "Can L1 handle this?"                │
│  • Route to L1/L2/L3 or tool/MCP/A2A                        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐    ┌─────────┐    ┌─────────────┐
        │   L1    │    │   L2    │    │     L3      │
        │ 4B-8B   │    │ 12-27B  │    │ Cloud API   │
        │ On-dev  │    │ Edge/PC │    │ OpenRouter  │
        │ 50ms    │    │ 200ms   │    │ 1-3s        │
        └─────────┘    └─────────┘    └─────────────┘
              │               │               │
              └───────────────┴───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  RESPONSE STREAM → Unified across all platforms             │
│  Same UX: typing indicator, token streaming, tool calls     │
└─────────────────────────────────────────────────────────────┘
```

### Model Selection Per Platform

| Platform | L0 | L1 | L2 | L3 |
|----------|-----|-----|-----|-----|
| **iOS** | Phi-1.5 Q4 | Gemma 4B Q4 (MLX) | Qwen 7B Q4 | Cloud API |
| **Android** | Phi-1.5 Q4 | Gemma 4B Q4 (MediaPipe) | Qwen 7B Q4 | Cloud API |
| **Windows** | ONNX Runtime | Qwen 7B Q4 (llama.cpp) | DeepSeek 14B | Cloud API |
| **Web (SaaS)** | — | WebLLM (Gemma 4B WebGPU) | WebLLM (Qwen 7B) | Cloud API |
| **Chrome Ext** | — | WebLLM (Phi-2 WebGPU) | Cloud API | Cloud API |

---

## 3. Crown Jewels: Open-Source Arsenal

### 3.1 Browser / Web — WebLLM (MLC-LLM)
- **Repo:** `github.com/mlc-ai/web-llm`
- **What:** High-performance in-browser LLM via WebGPU + WASM
- **Performance:** 80% of native speed
- **API:** OpenAI-compatible (`chat.completions.create`)
- **Models:** Llama 3, Phi 3, Gemma, Mistral, Qwen
- **Install:** `npm install @mlc-ai/web-llm`
- **Why:** Zero server cost, 100% private, works offline after first load

### 3.2 Cross-Platform Mobile — MediaPipe LLM Inference API
- **Repo:** `github.com/google-ai-edge/mediapipe`
- **What:** Google's official on-device inference SDK
- **Platforms:** Android (Kotlin), iOS (Swift), Web (JS)
- **Models:** Gemma 2B/7B, Phi-2, Falcon, StableLM
- **Format:** TensorFlow Lite Flatbuffer (int4/int8)
- **Why:** Production-grade, NPU-accelerated, same code pattern across platforms

### 3.3 Mobile (Alternative) — llama.cpp + Flutter / KMP
- **Repo:** `github.com/ggerganov/llama.cpp`
- **Flutter bindings:** `llm_llamacpp` (pub.dev)
- **Format:** GGUF (Q4_K_M recommended)
- **Platforms:** Android, iOS, macOS, Windows, Linux
- **Why:** Largest model ecosystem, any GGUF on HuggingFace works

### 3.4 Apple Ecosystem — MLX (Apple Silicon)
- **Repo:** `github.com/ml-explore/mlx`
- **What:** Apple's ML framework optimized for unified memory
- **Swift API:** `MLX Swift`
- **Why:** Native Apple performance, no translation layers

### 3.5 Windows Desktop — Tauri + WebView2
- **Repo:** `github.com/tauri-apps/tauri`
- **What:** Rust-based desktop app framework, WebView2 frontend
- **Bundle size:** ~600KB (vs Electron ~150MB)
- **Why:** Native performance, tiny footprint, same codebase as web

### 3.6 Chrome Extension — Manifest V3 + WebLLM
- **Pattern:** Service worker handles API calls, content scripts read DOM
- **Innovation:** Embed WebLLM in service worker for local inference
- **Fallback:** Stream from MEOKCLAW cloud via SSE

### 3.7 Protocol Layer — MCP + A2A
- **MCP SDK:** `github.com/modelcontextprotocol/python-sdk`
- **A2A SDK:** `github.com/themanojdesai/python-a2a`
- **MCP Registry:** 14,000+ servers (mcp.so, mcp-awesome.com)
- **A2A Standard:** JSON-RPC 2.0 over HTTP, Agent Cards for discovery

---

## 4. Platform Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Scaffold `inference-cascade/` split-router engine
- [ ] Integrate WebLLM into Next.js web app
- [ ] Set up model quantization pipeline (GGUF + MLC formats)
- [ ] MCP client integration in FastAPI backend

### Phase 2: Mobile (Week 3-4)
- [ ] iOS: Swift app with MLX + Gemma 4B
- [ ] Android: Kotlin app with MediaPipe + Gemma 4B
- [ ] Shared UI components via Kotlin Multiplatform or Flutter

### Phase 3: Desktop + Extension (Week 5-6)
- [ ] Windows: Tauri app wrapping web UI
- [ ] Chrome Extension: MV3 with WebLLM + cloud fallback
- [ ] macOS: Native Swift app (reuse iOS logic)

### Phase 4: Protocol Ecosystem (Week 7-8)
- [ ] MCP server marketplace integration
- [ ] A2A agent discovery + task delegation
- [ ] Cross-platform sync (conversations, settings, models)

---

## 5. The "Eat All" MCP + A2A Strategy

### MCP Integration
```
MEOKCLAW Core ──► MCP Client Hub ──► 14,000+ MCP Servers
                    ├── GitHub (code)
                    ├── Playwright (browser)
                    ├── Postgres (data)
                    ├── Brave Search (web)
                    ├── Figma (design)
                    └── ... any tool
```
- Every MEOKCLAW instance (web, mobile, desktop, ext) is an MCP client
- Backend runs MCP hub as a service for cloud-connected clients
- On-device clients can run local MCP servers (filesystem, shell)

### A2A Integration
```
MEOKCLAW Agent ──► A2A Protocol ──► Other Agents
                    ├── Google ADK agents
                    ├── Microsoft Copilot agents
                    ├── LangGraph agents
                    ├── Custom enterprise agents
                    └── ... any A2A-compliant agent
```
- MEOKCLAW exposes an Agent Card at `/.well-known/agent.json`
- Can delegate tasks to specialized agents (coding, research, design)
- Can receive tasks from external orchestrators

---

## 6. Performance Targets

| Metric | Target | How |
|--------|--------|-----|
| iOS app size | < 50MB | Gemma 4B Q4 + MLX |
| Android app size | < 60MB | Gemma 4B Q4 + MediaPipe |
| Windows installer | < 30MB | Tauri + WebView2 |
| Chrome extension | < 5MB | WebLLM lazy-loads models |
| Web bundle | < 500KB | Code-splitting, lazy model load |
| L1 inference latency | < 100ms | On-device NPU |
| L2 inference latency | < 500ms | Edge GPU or WebGPU |
| L3 inference latency | < 3s | Cloud API + streaming |
| Cold start (web) | < 2s | Service worker + IndexedDB cache |
| MCP tool discovery | < 1s | Cached registry + lazy loading |

---

## 7. Reverse-Engineering Opportunities

1. **Gemini Nano AICore IPC protocol** — Reverse the Android AICore binder interface to host our own models in a system-level process, enabling thermal-aware scheduling across all apps.

2. **Chrome's built-in AI (Gemini Nano in Chrome)** — Chrome is shipping Gemini Nano via Prompt API. We can polyfill this API and redirect to MEOKCLAW models.

3. **Apple Intelligence Private Cloud Compute** — Reverse the attestation protocol to understand how Apple routes between on-device and private cloud. Apply similar attestation to MEOKCLAW edge servers.

4. **Google's speculative decoding (EAGLE-3)** — Open-source implementations exist in vLLM. Port to WebGPU for browser-based speculative decoding.

5. **MoE routing visualization** — Reverse-engineer DeepSeek's router to build a task-aware router that sends "coding" queries to code-specialized experts, "creative" to creative experts.

---

*Document Owner:* JEEVES Strategic Architecture  
*Next Review:* Post-Phase-1 completion
