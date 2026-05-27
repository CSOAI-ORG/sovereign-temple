# MEOKCLAW v2 — Viral Roadmap & SOV3 Gap Audit

## 🔴 CRITICAL GAPS (Fix These First)

### 1. Safety: CARE Override Verification
- **Status:** ✅ Fixed in `router_ml.py` — crisis queries route directly to care membrane
- **Action:** Add automated safety tests to CI/CD

### 2. Vercel Deployment Token
- **Status:** ❌ `VERCEL_TOKEN` invalid — war room deployed but API env var not set
- **Fix:** Run `vercel login` then `vercel --prod -e NEXT_PUBLIC_API_BASE=https://api.meok.ai`

### 3. GPU Training Disk Space
- **Status:** ❌ Vast.ai 20GB overlay too small for Qwen2.5-7B download (~4GB)
- **Fix:** Use RunPod Serverless for training OR rent bigger Vast.ai instance

### 4. MCP Integration Down
- **Status:** ❌ MEOK_MCP (port 3102) is offline per SOV3 dashboard
- **Fix:** Restart MCP proxy or migrate to direct API calls

---

## 🟡 SOV3 WIRING GAPS

| System | Port | Status | Gap |
|---|---|---|---|
| SOV3 Coordination | 3101 | ✅ Healthy | No direct integration with dual-brain router |
| MEOK_MCP Proxy | 3102 | ❌ Down | No tool execution pipeline |
| MEOK_API | 3200 | ✅ Healthy | Legacy API, not using dual-brain |
| MEOK_UI | 3000 | ✅ Healthy | Old frontend, v2 is on 3001 |
| Farm_Vision | 8888 | ✅ Healthy | No computer vision in dual-brain |

**What's missing:**
1. **Unified health dashboard** — SOV3 sees old services, not new dual-brain
2. **Agent task routing** — 63 active agents don't use the Corpus Callosum Router
3. **Cross-service reflection** — Reflection Engine only sees API calls, not SOV3 tasks
4. **Shared knowledge sync** — 49 intel files in `~/.clawdbot/shared-knowledge/` not ingested

---

## 🟢 WHAT'S WORKING (Ship It)

| Component | Status | Metric |
|---|---|---|
| Dual-Brain API | ✅ v2.1.0 | 17/17 E2E tests |
| Corpus Callosum Router | ✅ | 0.02ms routing, 99.35% ML accuracy |
| Reflection Engine | ✅ | 2,381 reflections, 1,241 skills |
| OpenRouter Client | ✅ | $25 paid tier, cost tracking |
| Ollama Fallback | ✅ | Vast.ai RTX 4070 SUPER |
| War Room | ✅ | Deployed to Vercel |
| Model Cost Arena | ✅ | 694-line component, shareable |
| E2E Test Suite | ✅ | `test_e2e.py` |

---

## 🚀 VIRAL STRATEGY: From 0 to #1

### Phase 1: The "Holy Shit" Moment (Week 1)

**Build: The Cost Transparency Feature**
- Every response shows: "This cost $0.0003. GPT-4 would cost $0.04. You saved 99.3%."
- This is the shareable stat. People screenshot it.

**Build: The Council Mode**
- Actually run 5 models in parallel on EVERY ambiguous query
- Show them debating each other in real-time
- Winner gets a crown emoji
- This is the "magic" feature nobody else has

### Phase 2: Open Router Submission (Week 2)

**Submit to OpenRouter Apps:**
1. Create `openrouter_integration.py` — exposes `/v1/chat/completions` compatible endpoint
2. Add to OpenRouter's "App Directory" as "MEOKCLAW — Sovereign Dual-Brain OS"
3. Tagline: "The only router that learns from every conversation"

### Phase 3: GitHub Launch (Week 3)

**Create `meokclaw` GitHub repo:**
```
meokclaw/
├── README.md          # The manifesto
├── docker-compose.yml # One-command setup
├── docs/
│   ├── architecture.md
│   ├── cost-analysis.md
│   └── viral-demo.gif
├── src/
│   ├── router/        # Corpus Callosum
│   ├── api/           # FastAPI server
│   └── frontend/      # Next.js app
└── benchmarks/
    ├── vs-gpt4.md
    ├── vs-claude.md
    └── cost-per-1k.md
```

**README must include:**
- Architecture diagram (SVG)
- Cost comparison table
- 30-second demo GIF
- Docker one-liner: `docker compose up`
- Badges: tests passing, version, license

### Phase 4: Content Blitz (Week 4)

**Hacker News post:**
"Show HN: I built a $0.0003/query AI router that learns from every conversation"
- Focus on cost savings + learning
- Link to GitHub + live demo

**Twitter/X thread:**
- Screenshot the cost arena
- "GPT-4: $0.04 | MEOKCLAW: $0.0003 | Same quality"
- Show the war room dashboard

**Reddit r/LocalLLaMA:**
- "Dual-Brain Architecture: Left=Flash, Right=Pro, Both=Fusion"
- Technical deep-dive

### Phase 5: Ecosystem (Month 2)

**Plugins:**
- VS Code extension (route code questions to dual-brain)
- Discord bot (guild-wide model arena)
- Slack app (team cost tracking)

**Monetization:**
- Hosted API: $5/mo for 10K requests
- Enterprise: Self-hosted + support
- Skill marketplace: Sell custom router configs

---

## 🎯 THE MAGIC FEATURES

### 1. Live Cost Arena (BUILT ✅)
- Side-by-side model comparison
- Real $/1K token rates
- Shareable links

### 2. The Council (Build Next)
- 5-model parallel execution
- Real-time debate visualization
- BFT voting consensus

### 3. Skill Library API (Build Next)
- REST API: `GET /skills?q=drainage`
- Returns learned patterns from 2,381 reflections
- "Wikipedia of AI domain knowledge"

### 4. Sovereign Scorecard (Build Next)
- Public leaderboard: Who's saving the most money?
- Monthly rankings
- Badges: "Frugal King", "Speed Demon", "Quality Guru"

---

## 📋 IMMEDIATE ACTION ITEMS

| Priority | Task | Owner | ETA |
|---|---|---|---|
| P0 | Fix Vercel token & redeploy | User | 5 min |
| P0 | Restart MEOK_MCP (3102) | User | 10 min |
| P1 | Build Council Mode (5-model debate) | Dev | 2 hours |
| P1 | Create GitHub repo + README | Dev | 3 hours |
| P1 | Run LoRA on RunPod serverless | User | 30 min setup |
| P2 | Add cost-savings badge to every response | Dev | 1 hour |
| P2 | Build Skill Library API endpoint | Dev | 2 hours |
| P2 | Ingest 49 SOV3 intel files | Dev | 1 hour |
| P3 | VS Code extension | Dev | 1 day |
| P3 | Discord bot | Dev | 1 day |

---

## 💰 COST PROJECTIONS

Current burn: ~$60/mo (Vast.ai) + $25 OpenRouter credits
At viral scale (10K users):
- Inference: Vast.ai cluster ~$500/mo
- API: OpenRouter ~$2,000/mo
- Revenue (hosted): $5 × 1,000 users = $5,000/mo
- **Net: +$2,500/mo profit**

---

*Document version: 2026-05-26*
*Next review: 2026-06-02*
