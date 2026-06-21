# MEOKCLAW Dual-Brain v2.1 — Complete System Documentation

## Architecture

```
Frontend (Next.js 14)          localhost:3001
    ↓ POST /api/dual-brain
Dual-Brain API (FastAPI)       localhost:3201
    ↓
Corpus Callosum Router         0.02ms classification
    ↓
LEFT  → DeepSeek V4 Flash      (OpenRouter, ~$0.0001)
RIGHT → DeepSeek V4 Pro        (OpenRouter, ~$0.002-0.004)
BOTH  → Pro + Flash parallel   (OpenRouter, ~$0.004)
CARE  → Samaritans 116 123     (immediate override)
    ↓
Fallback → Llama 3.1 8B        (Vast.ai RTX 4070 SUPER)
Ultimate → Gemma 4 4B          (Local CPU)
    ↓
Reflection Engine → SQLite     (2,231 reflections, 1,241 skills)
```

## Files

| File | Purpose |
|---|---|
| `dual_brain_api.py` | FastAPI server (v2.1.0) with cache, rate limiting, live metrics |
| `dual_brain_router.py` | Corpus Callosum Router — keyword + learned triggers |
| `dual_brain_orchestrator.py` | Full pipeline: Router → API → Response → Reflection |
| `openrouter_client.py` | Paid OpenRouter client with key rotation, cost tracking |
| `ollama_client.py` | Async Ollama client for Vast.ai + local fallback |
| `reflection_engine.py` | SQLite skill library with FTS5 search |
| `train_router.py` | Train keyword classifier from decision logs |
| `router_ml.py` | Sklearn TF-IDF + LogisticRegression classifier (auto-generated) |
| `test_e2e.py` | Full E2E test suite (17 tests) |
| `benchmark_sweet_spot.py` | Endpoint benchmarking |
| `ingest_all_memory.py` | Master memory ingestion pipeline |
| `prep_finetune_dataset.py` | Dataset preparation for LoRA |
| `train_lora.py` | QLoRA fine-tuning script (unsloth/trl) |
| `runpod_train_handler.py` | RunPod serverless handler for training |
| `vast_ai_upgrade.sh` | Script to provision bigger GPU instance |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health, model status |
| `/api/dual-brain` | POST | Main chat endpoint |
| `/api/router-stats` | GET | Router decision statistics |
| `/api/reflection-stats` | GET | Reflection engine stats |
| `/api/live-metrics` | GET | Combined metrics for war room |

## Environment Variables

```bash
export OPENROUTER_API_KEY="your_key"
export OPENROUTER_API_KEY_2="backup_key"  # Optional
export DUAL_BRAIN_PORT=3201  # Optional
```

## Quick Start

```bash
cd ~/clawd/sovereign-temple

# Start API
python3 dual_brain_api.py

# Start frontend
cd meokclaw-v2 && npm run dev

# Run E2E tests
python3 test_e2e.py

# Train router
python3 train_router.py

# Ingest memories
python3 ingest_all_memory.py

# Prepare fine-tune
python3 prep_finetune_dataset.py
```

## GPU Strategy

**Current:** Vast.ai RTX 4070 SUPER @ $0.0826/hr (~$60/mo)
- 12GB VRAM, 20GB disk
- Runs Llama 3.1 8B reliably

**For training bursts:** Use RunPod Serverless
- $0 idle cost
- ~$0.50/hr when training
- No disk space limits

**To upgrade:** Run `./vast_ai_upgrade.sh <ip> <port>`

## Cost Burn Rate

With $25 OpenRouter credits:
- Greetings: $0 (Vast.ai)
- Coding tasks: ~$0.00015 each
- Reasoning: ~$0.002 each
- Governance (both): ~$0.004 each
- **Projected lifespan:** 6,000-8,000 tasks

## Caching

Identical queries are cached for 5 minutes (100 entry LRU).
Second identical request returns instantly with `cached: true`.

## Rate Limiting

30 requests per 60 seconds per IP.

## War Room Dashboard

Navigate to `http://localhost:3001/war-room` for real-time:
- Hemisphere activity
- Model node health
- Cost burn rate
- Router latency sparkline
- Recent task log

---
Built 2026-05-26 | MEOKCLAW v2.1.0
