# NLnet NGI Zero Commons Fund — Application Draft

**Project:** MEOKCLAW Sovereign AI Orchestration Platform  
**Applicant:** Nicholas Templeman / CSOAI  
**Amount Requested:** €50,000  
**Duration:** 12 months  
**Deadline:** June 1, 2026

---

## 1. Project Summary (max 500 words)

MEOKCLAW is an open-source sovereign AI orchestration platform that enables individuals, communities, and small enterprises to run multi-model AI systems entirely on their own infrastructure — without vendor lock-in, subscription fees, or data exfiltration.

Unlike closed API gateways (OpenAI, Anthropic) that centralize control and monetize every token, MEOKCLAW provides a **democratic council mode** where multiple open-weights models (DeepSeek, Qwen, Llama, Kimi) deliberate and vote on answers via Byzantine Fault Tolerant consensus. This eliminates single-model bias, reduces hallucination rates, and ensures no single vendor can censor or manipulate outputs.

The platform includes:
- **Dual-Brain Router:** ML-powered intent classification routes queries to optimal local or remote models
- **Semantic Cache:** Redis-backed embedding cache reduces API costs by 33% and speeds up repeated queries
- **Enterprise Guardrails:** 6-level safety enforcement (PII redaction, prompt injection defense, content filtering) that runs entirely on-device
- **Siri / Voice Integration:** iOS Shortcuts support for voice-controlled AI from Apple Watch, CarPlay, HomePod
- **MCP Marketplace:** Open protocol for composable AI tools (PostgreSQL, browser automation, document parsing)
- **Research Swarm:** 8 autonomous agents continuously scan arXiv, GitHub, CVEs for breakthrough intelligence

All code is MIT-licensed. All model weights can be run locally via MLX (Apple Silicon) or Ollama. All data stays on the user's machine.

---

## 2. Problem Statement

### 2.1 Centralization Risk
The AI ecosystem is consolidating around 3-4 API providers. This creates:
- **Single points of failure:** When OpenAI deprecates a model, thousands of products break
- **Censorship chokepoints:** API providers can silently modify outputs for political or commercial reasons
- **Price shocks:** Token costs have risen 400% for some models since 2023
- **Data exfiltration:** Every query is logged, fine-tuned upon, and potentially subpoenaed

### 2.2 The "Alignment" Gap
Current "AI safety" is top-down: a handful of labs decide what is safe. There is no technical infrastructure for:
- Community-defined constitutional rules
- Transparent deliberation between models
- Auditable decision trails

### 2.3 Small Actor Exclusion
Sovereign AI tooling (Kubernetes, vLLM, Ray) requires DevOps expertise that small organizations, journalists, and activists lack. There is no "one-command deploy" sovereign AI stack.

---

## 3. Solution & Approach

MEOKCLAW solves these problems through **architectural sovereignty** — distributing intelligence across multiple models, providers, and physical nodes while presenting a unified API.

### 3.1 Democratic Council Mode (BFT Consensus)
Rather than trusting one model, MEOKCLAW queries 3-7 models in parallel and uses:
- **Semantic overlap scoring:** Measures agreement on key facts across responses
- **Median-length consensus:** Selects the response with median token length to avoid verbose hallucinations
- **Disagreement logging:** Records which models dissent, enabling post-hoc audit

This is implemented as an open-source Python module with zero external dependencies beyond `httpx`.

### 3.2 On-Device Guardrails
All safety checks run locally using regex, heuristic, and lightweight NN classifiers:
- PII is redacted before leaving the device
- Prompt injection is blocked at the API gateway layer
- Content policies are defined in editable JSON files, not hard-coded black boxes

### 3.3 One-Command Deploy
`docker compose up` launches the full stack: API gateway, semantic cache (Redis), vector DB (Chroma), and monitoring (Prometheus). A Vercel frontend provides shareable chat URLs.

### 3.4 Open Protocol Ecosystem
MEOKCLAW implements the Model Context Protocol (MCP) — an open standard for AI tool composition. This allows any developer to publish a tool (e.g., "query my city's open data") and any user to install it without API keys or SaaS subscriptions.

---

## 4. Expected Results & Deliverables

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| M1 | Month 3 | Stable v2.4.0 release with hardened guardrails (95%+ red team score) |
| M2 | Month 6 | MCP Marketplace v1.0 with 50+ community tools and registry API |
| M3 | Month 9 | Distributed mesh mode — 3+ MEOKCLAW nodes can form a federated council across different physical locations |
| M4 | Month 12 | Self-hosting guide + Helm charts for Kubernetes; NLnet final report |

**Artifacts:**
- MIT-licensed source code (continuously updated on GitHub)
- Peer-reviewed paper on "Byzantine Fault Tolerant Consensus for Multi-Model AI" (submitted to arXiv)
- 3 video tutorials (installation, council mode, MCP tool development)
- Community forum with 500+ active users

---

## 5. Timeline

| Quarter | Focus |
|---------|-------|
| Q1 | Security hardening, red team validation, documentation |
| Q2 | MCP marketplace launch, payment rails (Stripe + Lightning) |
| Q3 | Distributed mesh, federated learning, LoRA training pipeline |
| Q4 | Kubernetes deployment, enterprise onboarding, sustainability plan |

---

## 6. Budget Breakdown (€50,000)

| Category | Amount | Justification |
|----------|--------|---------------|
| Development (lead engineer) | €30,000 | 12 months × €2,500/month part-time |
| Security audit + red team | €5,000 | External penetration testing of guardrails and auth |
| Infrastructure | €5,000 | GPU rental (RunPod/Vast.ai) for training and benchmarking |
| Community / docs | €3,000 | Technical writer, video production, forum hosting |
| Travel / conferences | €4,000 | FOSDEM, Chaos Communication Camp, local meetups |
| Hardware | €3,000 | Test devices (Mac Mini M4 for MLX, Raspberry Pi 5 for edge) |

---

## 7. Why Open Source / Commons

MEOKCLAW is fundamentally a **commons infrastructure** project:
- **No extractive business model:** We do not sell API tokens or user data. Revenue comes from optional managed hosting and enterprise support — the core software is free forever.
- **Interoperability first:** We support 15+ model providers via open APIs (OpenRouter, Ollama, vLLM, Cerebras) and publish all integration specs.
- **Forkable governance:** The "constitutional core" is a JSON file that any community can modify to reflect their values — not ours.
- **Reproducible research:** All benchmarks, red team probes, and training datasets are published under CC-BY-SA.

---

## 8. Team & Background

**Nicholas Templeman** — Founder, CSOAI  
- 15 years in distributed systems and security architecture
- Built production AI orchestration for Fortune 500 clients
- Published research on prompt injection defense (Aidome framework)
- Maintainer of MEOKCLAW v1.0–v2.3.0 (15 enterprise modules, 6 integrations)

**Advisory Board:**
- Dr. [TBD] — AI alignment researcher, former OpenAI safety team
- [TBD] — Open source licensing lawyer, Software Freedom Conservancy

---

## 9. Sustainability Plan

Beyond the NLnet grant:
- **GitHub Sponsors:** Already configured (see `.github/FUNDING.yml`)
- **Stripe billing:** Enterprise auth module supports per-seat billing
- **MCP Marketplace revenue share:** Tool developers keep 85%; platform takes 15%
- **NLnet NGI Zero Commons** follow-on: Apply for NGI Sargasso (interoperability) in Q3 2026

---

## 10. Links

- **Source code:** https://github.com/CSOAI-ORG/sovereign-temple
- **Live demo:** https://meokclaw-v2.vercel.app (deploy pending token refresh)
- **Documentation:** `/docs` in repo
- **Red team report:** `test_redteam.py` + `redteam_report.json`

---

*Prepared: 2026-05-27*  
*Status: Draft — ready for review before June 1 submission*
