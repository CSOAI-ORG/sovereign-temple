# MEOKCLAW 12-Hour Overnight Execution Plan
**Date:** 2026-05-27 16:05 → 2026-05-28 04:05
**Objective:** Deep research, testing, auditing, processing, SME tuning — fully unattended

---

## HOUR 0-1: Infrastructure Validation & Baseline Capture (16:05-17:05)
**Manual trigger now, then auto-pilot**

1. **Service Health Matrix** — Full connectivity audit:
   - M4: Dual-Brain API :3201, SOV3 :3101, Web UI :3000, Ollama :11434
   - M2: Ollama :11434 (ssh check + model list)
   - Vast: Ollama :11436 (tunnel check)
   - MEOKBRIDGE :3205 (8/8 node health)
   - Document all PIDs, ports, response times

2. **Disk & Resource Baseline**:
   - `df -h`, memory pressure, load average
   - Ollama VRAM usage per model
   - Log rotation status (`/tmp/dual_brain.log`, `/tmp/sov3-error.log`)

3. **Code State Snapshot**:
   - `git diff --stat` (uncommitted changes)
   - Module checksums for drift detection
   - Backup critical configs

---

## HOUR 1-3: Neural Model Retraining & SOV3 Alignment (17:05-19:05)
**Long-running background tasks — CPU-intensive**

### 3A. Retrain SOV3 Neural Models with Real Data
- **Source:** `data/reflection_store.db` (3MB, ~months of interactions)
- **Target models:**
  - `threat_detection_nn` — retrain with latest injection patterns + red team logs
  - `care_validation_nn` — retrain with reflectionStore care scores
  - `partnership_detection_ml` — CRITICAL: currently missing from `/neural/predict` endpoint
  - `emotion_recognition_nn` — calibrate with recent conversation data
- **Pipeline:** `retrain_all_models.py` (exists, uses sklearn MLP + TruncatedSVD)
- **Validation:** Hold-out test from `data/valid.jsonl`
- **Output:** New `.pkl` files in `models/`, metadata JSON with accuracy/MSE/MAE

### 3B. SOV3 Endpoint Registration Audit
- Verify each model loads correctly in `sovereign-mcp-server.py`
- Add missing `partnership_detection` to the `/neural/predict` router
- Test all model endpoints with synthetic + real samples
- Document which models return `{"error":"Unknown model"}` vs actual scores

### 3C. Model Drift Detection
- Compare current model predictions against baseline (6 hours ago)
- Flag any model whose accuracy dropped >5% on validation set
- Generate drift report

---

## HOUR 3-5: Comprehensive Benchmark & Performance Audit (19:05-21:05)
**Automated benchmark suite — API-intensive**

### 5A. Run Full Benchmark Suite
Execute `benchmark_sovereign.py` with extended iterations:
- **Dual-Brain API:** P50/P95/P99 latency per mode (Auto, QuantMan, Council, Twin)
- **Local Ollama:** TTFT, tokens/sec for each loaded model (Qwen3:8b, DeepSeek-R1 1.5b)
- **Guardrails:** 100 red-team probes (injection, PII exfiltration, unicode attacks)
- **Council Mode:** Consensus accuracy with 3/5/7 model configurations
- **Cost Tracking:** Verify cost estimates match actual OpenRouter billing

### 5B. Load Testing (Light)
- 10 concurrent requests to `/api/dual-brain` for 5 minutes
- Track error rate, circuit breaker trips, semantic cache hit rate
- Monitor memory growth (leak detection)

### 5C. i18n Stress Test
- Run QuantMan E2E (`test_quantman_e2e.py`) 20 iterations per language
- Record flakiness rate per language
- Identify which models are inconsistent under load

---

## HOUR 5-7: Security Audit & Red Team (21:05-23:05)
**Critical for NLnet grant and production readiness**

### 7A. Automated Red Team Probing
- **Prompt Injection:** 200 crafted payloads against all endpoints
  - Direct: `ignore previous instructions`, `DAN mode`, delimiter injection
  - Indirect: document poisoning, email PS injection, code comment injection
  - Encoding: base64, rot13, leetspeak, unicode homoglyphs
- **PII Exfiltration:** Test guardrails with fake SSNs, credit cards, API keys
- **Adversarial Unicode:** Bidi overrides, zero-width joiners, homoglyph attacks
- **Rate Limit Bypass:** Burst testing, slowloris-style connections

### 7B. Endpoint Security Audit
- Review all FastAPI endpoints for missing auth, input validation gaps
- Check for SQL injection in reflection_store.db queries
- Verify CORS policies aren't overly permissive
- Audit file upload endpoints (if any) for path traversal

### 7C. Dependency Vulnerability Scan
- `pip-audit` or `safety check` on `.venv`
- Check for known CVEs in FastAPI, httpx, sklearn, numpy
- Flag any critical/high severity findings

---

## HOUR 7-9: Data Processing & Knowledge Base Tuning (23:05-01:05)
**Batch processing — reflection analysis, embedding backfill**

### 9A. Reflection Store Analysis
- Query `data/reflection_store.db` for patterns:
  - Most common task types and their success rates
  - Models with highest error rates
  - Care score trends over time
  - Skill extraction yield (how many skills generated per 100 tasks)
- Generate `reflection_analytics_report.json`

### 9B. Semantic Cache Optimization
- Analyze cache hit patterns from `data/reflection_store.db` or observability logs
- Identify high-value cache entries (frequent queries with high latency)
- Tune `SIMILARITY_THRESHOLD` (currently 0.92) based on false-positive rate
- Backfill missing embeddings for uncached historical queries

### 9C. Training Data Curation
- Merge `data/train.jsonl` + `data/synthetic_training.jsonl` + `data/finetune_jarvis.jsonl`
- Deduplicate, quality-filter (remove empty/short entries)
- Split into train/validation/test (80/10/10)
- Export curated dataset to `data/training_curated_YYYY-MM-DD.jsonl`

### 9D. Embedding Backfill
- Run `backfill_embeddings.py` on all unembedded reflections
- Ensure nomic-embed-text covers 100% of reflection store

---

## HOUR 9-10: Documentation & Grant Finalization (01:05-02:05)
**Writing tasks — lower compute, high value**

### 10A. Auto-Generate Technical Documentation
- API endpoint documentation from `dual_brain_api.py` (extract docstrings + request/response models)
- Neural model cards for each `.pkl` in `models/` (architecture, training data, accuracy)
- Architecture diagram text (Mermaid format) of QuantMan data flow
- Security controls inventory (guardrails layers, circuit breaker configs, auth mechanisms)

### 10B. NLnet Grant Final Review
- Review `grants/final/NLNET_APPLICATION_COMPLETE.md` against submission checklist
- Verify all attachments present in `grants/final/attachments/`
- Check word counts against limits
- Generate final PDF (if pandoc available)
- Prepare submission command for manual execution tomorrow

---

## HOUR 10-11: Cross-Module Integration Audit (02:05-03:05)
**Code review — find orphaned/broken integrations**

### 11A. Import Graph Analysis
- Parse all Python files for imports
- Identify modules that import non-existent files
- Find circular dependencies
- Flag modules with >50% dead code (imports not used)

### 11B. Integration Status Report
- For each major subsystem, verify all advertised features work:
  - Siri integration (`siri_integration.py`) → test iOS Shortcut payload
  - OpenRouter integration (`openrouter_integration.py`) → verify key rotation
  - Batch processor (`batch_processor.py`) → test with sample batch
  - Structured output (`structured_output.py`) → validate schema enforcement
  - Voice pipeline (`voice_pipeline/`) → check TTS/STT health
- Document which integrations are live vs placeholder

### 11C. Frontend-Backend Contract Verification
- Compare Next.js API calls against actual FastAPI endpoints
- Identify missing CORS headers or broken routes
- Check WebSocket connections (if any) for stability

---

## HOUR 11-12: Monitoring, Alerting & Handoff Preparation (03:05-04:05)
**Wrap-up — ensure clean state for morning**

### 12A. Overnight Report Generation
Compile all outputs into `overnight_report_2026-05-27.md`:
- Executive summary (what ran, what passed, what failed)
- Benchmark results with before/after comparison
- Security audit findings (critical/high/medium/low)
- Retrained model metrics (accuracy delta)
- Data processing stats (records processed, embeddings backfilled)
- Integration health matrix (green/yellow/red per subsystem)
- Recommendations for morning work

### 12B. Log Aggregation
- Concatenate all run logs into `logs/overnight/`
- Rotate oversized logs (`>100MB`)
- Compress old logs

### 12C. Service Validation
- Final health check on all 5 services
- Verify no memory leaks (compare to Hour 0 baseline)
- Ensure no zombie processes from benchmarks

### 12D. Morning Handoff
- Write `HANDOFF.md` with:
  - Top 3 priorities for tomorrow
  - Any critical issues requiring immediate attention
  - Files modified during overnight run
  - Commands to resume any interrupted tasks

---

## Background Task Queue

| Task | Script/Command | Duration | Priority |
|------|---------------|----------|----------|
| Neural retraining | `retrain_all_models.py` | 2-3h | P0 |
| Full benchmark | `benchmark_sovereign.py --extended` | 1-2h | P0 |
| Red team probes | `test_redteam.py` + custom probes | 1-2h | P0 |
| Dependency audit | `pip-audit` / `safety check` | 15m | P1 |
| Reflection analysis | SQL queries + Python analysis | 1h | P1 |
| Embedding backfill | `backfill_embeddings.py` | 30m | P1 |
| Training data curation | Python dedupe script | 30m | P1 |
| Integration audit | Import graph + endpoint tests | 1h | P2 |
| Doc generation | Docstring extraction | 30m | P2 |
| Grant review | Markdown lint + checklist | 30m | P2 |

---

## Risk Mitigation

- **API rate limits:** Benchmark uses local Ollama primarily; OpenRouter calls throttled to 5 RPM overnight
- **Memory exhaustion:** Monitor swap usage; kill benchmark if RAM >90%
- **Disk full:** 11GB free → purge `/tmp/` logs if <2GB remains
- **Model training failure:** Fallback to synthetic data generation if real data insufficient
- **Service crash:** Auto-restart via existing `nohup` scripts; document any restarts in report

---

## Success Criteria (Morning Check)

- [ ] All 6 languages pass QuantMan E2E (≥90% success rate)
- [ ] SOV3 `/neural/predict` returns scores for all 3 core models (threat, care, partnership)
- [ ] Benchmark report generated with P50/P95/P99 latencies
- [ ] Security audit: 0 critical vulnerabilities, <5 high-severity findings
- [ ] Reflection analytics report present
- [ ] Overnight report + handoff document ready
- [ ] All services healthy after 12h continuous operation
