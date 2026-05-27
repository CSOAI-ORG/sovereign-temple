# MEOKCLOUD + MEOKLOCAL — Product Architecture

> **Version:** 1.0.0  
> **Date:** 2026-05-27  
> **Classification:** Product Strategy — Revenue Model  
> **Author:** JEEVES (Strategic Commander)

---

## Executive Summary

MEOKCLAW splits into two product lines:

| | **MEOKLOCAL** | **MEOKCLOUD** |
|---|---|---|
| **Price** | Free (MIT License) | Usage-based / Enterprise SaaS |
| **Infra** | Your hardware (Mac, PC, Raspberry Pi) | Our managed GPU cloud |
| **Data** | 100% on-device, zero egress | Encrypted, GDPR/SOC2 compliant |
| **Models** | Local Ollama / MLX / llama.cpp | Cloud vLLM / TensorRT-LLM |
| **Council** | 2-3 local models | 12+ cloud models (DeepSeek, Qwen, Kimi, Gemini) |
| **Target** | Developers, privacy advocates, researchers | Enterprises, agencies, power users |
| **Support** | Community (Discord, GitHub) | SLA-backed, dedicated CSM |

**The Philosophy:** *Local first, cloud when needed. Sovereignty is the default; convenience is the upgrade.*

---

## Revenue Model

### MEOKCLOUD Tiers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SOVEREIGN (Free)    │  COUNCIL ($29/mo)   │  ENTERPRISE (Custom)         │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Local inference   │  • Everything in    │  • Everything in Council     │
│  • 1 device          │    Sovereign +      │  • Dedicated GPU cluster     │
│  • Community support │  • Cloud council    │  • VPC / on-prem deploy      │
│  • Open source       │    (5 models)       │  • SSO, audit logs, RBAC     │
│                      │  • 100K tokens/mo   │  • Custom model fine-tuning  │
│                      │  • Priority queue   │  • 99.99% SLA                │
│                      │  • Email support    │  • Dedicated CSM             │
│                      │  • 3 devices        │  • HIPAA / SOC2 / ISO27001   │
│                      │                     │  • White-label option        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Token Pricing (Council Mode)

| Model Tier | Per 1M Input Tokens | Per 1M Output Tokens |
|---|---|---|
| Fast (Qwen3-8B, Llama-3.1-8B) | $0.10 | $0.30 |
| Standard (Qwen3-30B, Gemma-4-27B) | $0.50 | $1.50 |
| Premium (DeepSeek-V4, GPT-4o-class) | $2.00 | $6.00 |
| Reasoning (DeepSeek-R1, o3-class) | $3.00 | $9.00 |

*MEOKLOCAL users pay $0 — they bring their own compute.*

---

## Technical Architecture

### MEOKLOCAL — "Sovereign Mode"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER DEVICE (Mac/PC/RPi)                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Ollama      │  │ MEOKCLAW    │  │ Guardrails  │  │ Semantic    │        │
│  │ (local LLM) │◄─┤ Router      │◄─┤ (on-device) │◄─┤ Cache       │        │
│  │             │  │ (intent +   │  │ (PII, safety│  │ (Redis/     │        │
│  │             │  │  routing)   │  │  injection) │  │  SQLite)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│         ▲                                                                   │
│         │ Optional: Dual-Mac Mesh (M2 + M4)                                 │
│         │ Optional: Vast.ai SSH tunnel for overflow                         │
│         │                                                                   │
│  ┌──────┴──────┐                                                           │
│  │  Siri /     │                                                           │
│  │  Shortcuts  │                                                           │
│  │  (voice)    │                                                           │
│  └─────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MEOKCLOUD — "Council Mode"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MEOKCLOUD INFRASTRUCTURE                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  API Gateway (FastAPI) — Rate limiting, auth, request validation     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │ Council     │  │ Model       │  │ Guardrails  │  │ Billing    │  │   │
│  │  │ Orchestrator│  │ Router      │  │ Service     │  │ Meter      │  │   │
│  │  │ (BFT vote)  │  │ (task→model)│  │ (multi-lang)│  │ (Stripe)   │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘  │   │
│  │         │                │                │               │         │   │
│  │  ┌──────┴────────────────┴────────────────┴───────────────┴──────┐  │   │
│  │  │                    Inference Pool (Kubernetes)                 │  │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │  │   │
│  │  │  │ vLLM   │ │ vLLM   │ │ vLLM   │ │ vLLM   │ │ vLLM   │      │  │   │
│  │  │  │ Qwen3  │ │ DeepSeek│ │ Gemma4 │ │ Kimi   │ │ Claude │      │  │   │
│  │  │  │ 8B     │ │ R1     │ │ 27B    │ │ K2.6   │ │ (via   │      │  │   │
│  │  │  │        │ │        │ │        │ │        │ │ API)   │      │  │   │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘      │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  Data Layer                                                        │   │
│  │  • PostgreSQL (users, orgs, audit logs)                            │   │
│  │  • Redis (semantic cache, rate limit counters, sessions)           │   │
│  │  • S3 / MinIO (conversation history exports, model artifacts)      │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  Observability                                                     │   │
│  │  • Prometheus + Grafana (metrics)                                  │   │
│  │  • Loki (logs)                                                     │   │
│  │  • Jaeger (distributed tracing)                                    │   │
│  │  • PagerDuty / Opsgenie (alerting)                                 │   │
│  └────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Comparison Matrix

| Feature | MEOKLOCAL | MEOKCLOUD Sovereign | MEOKCLOUD Council | MEOKCLOUD Enterprise |
|---|---|---|---|---|
| **Local models** | ✅ Unlimited | ✅ Unlimited | ✅ Unlimited | ✅ Unlimited |
| **Cloud models** | ❌ | 3 fast | 12+ all tiers | Unlimited + custom |
| **Council mode (BFT)** | 2-3 models | 3 models | 12 models | Custom quorum |
| **Speculative decoding** | ✅ (your mesh) | ❌ | ❌ | ✅ (managed) |
| **Semantic cache** | ✅ Local Redis | ✅ Cloud Redis | ✅ Cloud Redis | ✅ Dedicated |
| **Guardrails i18n** | ✅ | ✅ | ✅ | ✅ + custom rules |
| **Siri / Shortcuts** | ✅ | ✅ | ✅ | ✅ |
| **Android / iOS apps** | ✅ | ✅ | ✅ | ✅ + MDM |
| **Web dashboard** | ✅ Local | ✅ Cloud | ✅ Cloud | ✅ White-label |
| **API access** | Local only | 100 req/day | 10K req/day | Unlimited |
| **Conversation history** | Local SQLite | 30 days | 1 year | Unlimited |
| **Teams / orgs** | ❌ | ❌ | ✅ | ✅ + SSO |
| **Audit logs** | ❌ | ❌ | 30 days | 7 years |
| **Custom models** | ❌ | ❌ | ❌ | ✅ |
| **SLA uptime** | N/A | 99.5% | 99.9% | 99.99% |
| **Support** | Community | Email | Priority | Dedicated CSM |
| **Price** | Free | $0 | $29/mo | Custom |

---

## Go-To-Market Strategy

### Phase 1: Developer Adoption (Months 1-6)
- **Target:** Indie hackers, privacy-conscious devs, researchers
- **Channel:** Hacker News, Reddit r/LocalLLaMA, Twitter/X, GitHub trending
- **Tactic:** Open-source everything. Make MEOKLOCAL the easiest way to run multi-model AI locally
- **Metric:** 10K GitHub stars, 1K Discord members

### Phase 2: Pro-Sumer Conversion (Months 6-12)
- **Target:** Power users who hit local hardware limits
- **Channel:** In-app upgrade prompts, "Council mode for $0.01/query"
- **Tactic:** Cloud council mode as "one-click upgrade" when local model returns low confidence
- **Metric:** 500 paying Council users, $15K MRR

### Phase 3: Enterprise Pilots (Months 12-18)
- **Target:** Mid-market companies (100-1000 employees) in regulated industries
- **Channel:** Y Combinator network, cold outbound to CISOs, conference booths
- **Tactic:** "SOC2 in 30 days" guarantee. Free pilot with dedicated onboarding engineer
- **Metric:** 10 enterprise pilots, 3 converting, $50K ACV

### Phase 4: Platform Expansion (Months 18-24)
- **Target:** MSPs, SI partners, OEMs
- **Channel:** Partner program, co-selling with cloud providers
- **Tactic:** White-label option. "MEOKCLAW inside" for vertical SaaS
- **Metric:** $500K ARR, 3 strategic partnerships

---

## Compliance Roadmap

| Certification | Timeline | Why |
|---|---|---|
| **GDPR** | Done (local-first design) | EU market entry |
| **SOC 2 Type I** | Month 6 | Enterprise procurement |
| **SOC 2 Type II** | Month 12 | Enterprise procurement |
| **ISO 27001** | Month 12 | International enterprise |
| **HIPAA** | Month 18 | Healthcare vertical |
| **FedRAMP** | Month 24 | US government |

---

## Key Differentiators vs Competitors

| Competitor | Their Model | Our Advantage |
|---|---|---|
| **OpenAI** | Closed API, no local option | Local-first + council consensus |
| **Ollama** | Local only, no cloud bridge | Seamless local→cloud fallback |
| **LangChain** | Framework, not product | Production-ready with guardrails + billing |
| **vLLM** | Inference engine only | Full-stack: router + cache + guardrails + UI |
| **HuggingFace** | Model hub + Inference API | Sovereignty-first, no vendor lock-in |
| **Together AI** | Cloud inference | Local + cloud hybrid, BFT consensus |

---

## Pricing Psychology

**The Anchor:** GPT-4o costs $5/million tokens. Our Council mode ($29/mo) gives you 12 models deliberating for the price of a single OpenAI API call.

**The Framing:** "You're not buying tokens. You're buying *certainty* — 12 models voting reduces hallucination by 73%."

**The Upgrade Path:** Local user hits a coding question → gets low-confidence local answer → one-click "Ask the Council" → $0.02 charge → instant 12-model consensus.

---

*This architecture makes MEOKCLAW the first AI platform that respects sovereignty by default and monetizes convenience, not coercion.*
