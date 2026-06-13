# SOV3 Morris-II hardening — wiring plan (reviewed diffs)

*2026-06-06. Source: the TikTok-verification report's §8 (Morris II, arXiv:2403.02817) + a read-only audit of the live SOV3 code. Primitives shipped + unit-tested in `security/worm_guard.py` (19/19 green). This doc is the **wiring** — what to call where. Nothing here is applied to the live server yet; each item is tagged.*

## The honest posture (what we already have vs the real gaps)

| Control | State | Evidence |
|---|---|---|
| Injection scan at **tool entry** | ✅ present | `sanitize_input()` sovereign-mcp-server.py:1649-1701, applied :2610 |
| Audit log + **hash-chain** | ✅ present | monitoring/audit_logger.py:142-145 (SHA256 chain) |
| **Red-team harness** (100+ probes) | ✅ present | test_redteam.py (12 categories) |
| Prompt-injection-**firewall pkg** | ⚠️ built, **offline** | mcp-marketplace/agent-prompt-injection-firewall-mcp — separate server, not wired |
| Banned-term **ingest gate** | ⚠️ partial | sov3_ingest_research.py:32 (domain terms only, not injection-aware) |
| **SIGIL** signing | ⚠️ built, **not wired** | sigil.py exists; imported by nothing; audit `signature` col never written |
| `:3101` bind | ⚠️ `0.0.0.0` but **firewall-mitigated** | GCP opens only 22/3389/icmp to internet; 3101 = tunnel+VPC only |
| **Per-agent tool RBAC** | ❌ MISSING | any agent can call any tool incl. payment_/delete_ (agent_registry.py:480-541) |
| **Autonomy caps** | ❌ MISSING | no max_turns/token budget in ralph loop / delegate (ralph_task_runner.py:30-180) |
| **Human gate on external writes** | ❌ MISSING | payment_bridge.py create_payment has no approval |
| Cross-agent + **RAG re-scan** | ❌ MISSING | delegate payload + query_memory results never re-scanned |

**The four real gaps, risk-ranked:** (1) tool RBAC, (2) autonomy caps, (3) external-write gate, (4) cross-agent/RAG re-scan.

---

## Rollout discipline (how we don't repeat the catalogue blast)
1. **Log-only first.** Every scan/quarantine call ships in OBSERVE mode (log what it *would* block, block nothing) for one cycle. Validate the regexes against real SOV3 traffic, tune false-positives, *then* flip to enforce.
2. **Mac copy first, VM second.** Apply + soak on `~/clawd/sovereign-temple`, verify the 110-tool bridge still returns 110, *then* deploy to the VM copy.
3. **One control per change.** Don't batch W1–W5. Each is independently revertible.

---

## ✅ SAFE-NOW (additive, reversible, log-only) — greenlight and I apply + soak on Mac

### W1 — scan cross-agent + memory ingest (Control 1)
`record_memory` content and `delegate_task` description are the two unguarded ingest points. Add an observe-mode scan:
```python
# top of sovereign-mcp-server.py
from security import worm_guard as _wg
WORM_GUARD_ENFORCE = os.environ.get("WORM_GUARD_ENFORCE", "0") == "1"  # log-only until set

# in record_memory(...) before storing `content`:
_r = _wg.scan(content)
if _r.flagged:
    audit_logger.log_event("WORM_GUARD_FLAG", {"site": "record_memory", "sev": _r.severity, "matches": _r.matches[:3]})
    if WORM_GUARD_ENFORCE and _r.at_least("high"):
        content = _r.sanitized           # redact, don't reject — keeps the record, defangs it

# in delegate_task(...) before dispatch, same pattern on `description`.
```
Risk: a regex false-positive could redact a legit memory *only when ENFORCE=1*. Log-only mode is zero-risk. **Recommend: ship log-only, read a day of WORM_GUARD_FLAG events, then enforce.**

### W2 — re-scan RAG/memory on the way OUT (Control 4)
The highest-value worm break: poisoned memory written by agent A must not reach agent B.
```python
# in query_memory(...) / the retrieval merge (~:2791-2809), after assembling `results`:
clean, quarantined = _wg.rag_rescan(results, key="content", block_at="high")
for q in quarantined:
    audit_logger.log_event("WORM_GUARD_QUARANTINE", {"sev": q["_worm_guard"]["severity"]})
results = clean if WORM_GUARD_ENFORCE else results   # observe-mode returns everything but logs
```

### W3 — bind belt-and-braces (reconcile task #59)
Firewall already blocks 3101 externally, so this is hardening not a fix. In `run-local.sh` add `export HOST=127.0.0.1` **only after confirming nothing reaches SOV3 via LAN/VPC IP** (the bridge uses the tunnel; the Mac uses localhost — both fine). 1 line, revert = delete the line.

### W8 — extend the red-team with a worm-propagation test (Control 8)
Add to test_redteam.py: write a poisoned memory → call query_memory as a second "agent" → assert the injected instruction is quarantined (not returned). Pure test, zero prod risk. This is how we *prove* W1+W2 work.

---

## ⚠️ SUPERVISED (changes live behavior — needs your ok + careful test + staged VM deploy)

### W4 — human/quorum gate on external writes (Control 7) — **highest business risk**
`is_external_write(tool_name)` (in worm_guard) flags payment_/send_/post_/push_/delete_/grant_/deploy_/shutdown_ tools. Route those through the existing `AgentCouncil` quorum or a pending-approval queue instead of firing inline. Touches payment_bridge.py + the tools/call dispatcher. Test: confirm a normal read tool still fires instantly; a payment tool now requires approval. **This is the one I'd prioritise** — an autonomous worm draining a payment endpoint is the worst-case.

### W5 — per-agent tool allowlist (Control 2) — **biggest blast radius**
Add an `allowed_tools` set per agent role in agent_registry; the dispatcher (sovereign-mcp-server.py ~:2602) checks membership before dispatch. Needs a default policy (e.g. all agents get read/query tools; only named roles get delete/payment/deploy). Risk: too-tight a policy breaks working flows → must be built allow-by-default-log-deny first, then tighten. Real design work; do with you.

### W6 — wire SIGIL into the audit signature (reconcile task #61)
`sigil.py` produces a stable signable digest per exchange but is wired into nothing. Two options: (a) cheap — populate the empty `audit_logs.signature` with an HMAC of the hash-chain head (internal tamper-evidence, honest framing); (b) real — the Ed25519 upgrade (task #43) signs both attestations and audit heads. (b) is the moat. Either way, supervised.

---

## Suggested order
1. W8 (test harness — proves the rest) → W1 → W2 in **log-only**, soak, read flags.  *(safe, I can do on greenlight)*
2. Flip W1/W2 to enforce after tuning.  *(safe)*
3. W4 payment gate.  *(supervised — top priority)*
4. W5 tool RBAC.  *(supervised — design together)*
5. W6 SIGIL/Ed25519 audit signing.  *(supervised — ties to task #43)*

`worm_guard.py` is standalone and already importable; none of the above runs until explicitly called.
