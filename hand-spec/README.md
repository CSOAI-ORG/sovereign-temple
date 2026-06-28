# SOV3 HAND.toml Spec — Sovereign capability manifest

**Source adaptation:** [RightNow-AI/openfang](https://github.com/RightNow-AI/openfang) `crates/openfang-hands/src/lib.rs` (MIT, 17.9k★)
**SOV3 spec file:** `sov3-hand-manifest.spec.toml` (this repo, `hand-spec/`)
**Author:** M4 lane (M4@sovereign.local)
**Date:** 2026-06-27
**License:** MIT (mirrors OpenFang)

## What this is

The SOV3 adaptation of OpenFang's `HAND.toml` pattern. Every autonomous capability that runs 24/7 on the MEOK sovereign hive is described by one of these manifests. The schema covers everything OpenFang's does, plus 3 sovereign extensions: compliance, OSCAL evidence, and SIGIL audit.

## Why we adapted OpenFang (per Kimi synthesis Phase 3)

> "Port your 313 MCPs into OpenFang's 'Hands' architecture — each MCP becomes a `HAND.toml` manifest."

OpenFang's `HAND.toml` is the **industry's most mature** capability manifest:
- **17.9k★** community + Rust-based kernel (sovereign-friendly)
- **180ms cold start** vs LangGraph 2.5s
- **16 security systems** with sandboxing + approval gates
- **40 channels** (Slack, Telegram, Discord, etc.) + **38 tools** + **30 agents** wired
- **7 bundled Hands** already shipping (twitter, clip, trader, researcher, lead, browser, collector)

Adopting the pattern = our 313+ MCPs gain a battle-tested runtime + we don't reinvent the manifest schema.

## What's the same (we kept OpenFang's)

| Field | Type | Purpose |
|---|---|---|
| `id`, `name`, `description`, `category`, `icon` | header | The Hand's identity |
| `tools` | array of slugs | Which MCP tools this Hand can call |
| `[[requires]]` | array | External API keys / binaries / env vars |
| `[requires.install]` | nested | Install instructions per platform |
| `[[settings]]` | array | User-configurable settings (text, number, select, multiselect, toggle, secret) |
| `[agent]` | nested | LLM config (name, model, max_tokens, temperature, system_prompt) |
| `[dashboard]` + `[[dashboard.metrics]]` | nested | What to show in the UI |

## What's different (SOV3 sovereign extensions)

| Field | Why we added it |
|---|---|
| `[sovereign].compliance_frameworks` | Which EU AI Act / GDPR / ISO 42001 articles this Hand addresses (auto-mapped to our compliance MCPs) |
| `[sovereign].oscal_components` | Which OSCAL Component Definitions this Hand produces (signed by `oscal-generator-mcp` Ed25519) |
| `[sovereign].sigil_chain` | Path to the SIGIL chain this Hand appends to (Ed25519 audit trail) |
| `[sovereign].data_residency` | "uk" / "eu" / "us" / "apac" — where the data lives |
| `[sovereign].access_control` | "council_oversight" — every action is reviewed by N queens |
| `[[settings]] x402_price_usd` | Pay-per-call monetization (wires to `meok-x402-paywall-mcp`) |
| `[[settings]] council_oversight` | Which queens must approve this Hand's actions |
| `[[settings]] sovereign_mode` | "sovereign_only" / "hybrid" / "local_first" |
| `[agent].module = "builtin:sov3"` | Default to our sovereign model (vs OpenFang's `builtin:chat` raw LLM) |

## How to use

### 1. Author a Hand for one of our MCPs

```bash
mkdir -p hand-spec/examples/compliance-hand
cat > hand-spec/examples/compliance-hand/HAND.toml <<'EOF'
id = "compliance-hand"
name = "EU AI Act Compliance Hand"
description = "Autonomous compliance scanner — runs every 6h, scans all MCPs, generates OSCAL pack"
category = "security"
icon = "🛡️"
tools = [
  "mcp__eu_ai_act_compliance__scan",
  "mcp__oscal_generator__generate",
  "mcp__agent_audit_logger__emit",
  "mcp__memory_recall",
  "mcp__memory_store",
]

[[requires]]
key = "MEOK_HIVE_API_KEY"
label = "MEOK Hive API Key"
requirement_type = "api_key"
check_value = "MEOK_HIVE_API_KEY"

[requires.install]
signup_url = "https://meok.ai/dashboard/api-keys"
env_example = "MEOK_HIVE_API_KEY=hk_..."

[[settings]]
key = "scan_interval_hours"
label = "Scan Interval (hours)"
setting_type = "number"
default = 6

[agent]
name = "compliance-hand"
module = "builtin:sov3"
model = "sov3-base-7b"
max_tokens = 32768
temperature = 0.3
max_iterations = 100
system_prompt = "You are the EU AI Act Compliance Hand..."

[sovereign]
compliance_frameworks = ["EU AI Act", "ISO 42001"]
oscal_components = ["compliance-hand-component"]
sigil_chain = "meok-backend:/var/lib/sigil/compliance.chain"
data_residency = "uk"
access_control = "council_oversight"

[dashboard]
[[dashboard.metrics]]
label = "Scans Completed"
memory_key = "compliance_hand_scans"
format = "number"

[[dashboard.metrics]]
label = "Critical Findings"
memory_key = "compliance_hand_critical"
format = "number"
EOF
```

### 2. Validate it

```bash
# The bundled validator (in this folder) checks structural soundness
python3 validate_hand_toml.py hand-spec/examples/compliance-hand/HAND.toml
```

### 3. Ship it to the hive

```bash
# Push to the sovereign-temple repo
git add hand-spec/examples/compliance-hand/
git commit -m "feat(hand): add compliance-hand manifest"
git push origin fix/silent-noop-metrics-comparison

# Then on the hive VM (manually or via CI):
# 1. ssh meok-backend
# 2. git pull
# 3. sov3 hand activate hand-spec/examples/compliance-hand/HAND.toml
# 4. sov3 hand start compliance-hand
```

### 4. The Hand runs 24/7 on the hive

- Every action → SIGIL-signed → audit chain
- Every action → council_oversight reviewed → VETOed if it violates Care/Watch
- Every action → OSCAL evidence generated → Art. 12 audit trail
- Every action → x402-priced → pay-per-call monetization (or free for internal)

## Cross-lane safety

Per the M4 lane audit in `KIMI_SYNTHESIS_ACTION_PLAN_2026-06-27.md`:
- **Hermes/JEEVES** owns SOV3 runtime + queen persona bootstrap
- **Other M4 lanes**: ready-to-fire, EAT-4 MCPs, print queue
- **M2**: councilof-ai live app (the user-facing version of SOV3)
- **This spec is for the M4 sovereign-orchestrator lane ONLY**
- Does not conflict with `data/council_queens_personas.json` (different concept — that's personas, this is capability manifest schema)
- Does not conflict with `team-templates/sovereign-council.toml` (that's the council Toml, this is the capability manifest spec)

## OpenFang attribution

This spec is an ADAPTATION of OpenFang's `HAND.toml` pattern. The original schema is from:
- **Repo:** https://github.com/RightNow-AI/openfang
- **File:** `crates/openfang-hands/src/lib.rs` (the `HandManifest` struct)
- **License:** MIT
- **Stars:** 17,900+ (as of 2026-06-27)

We extend it with 3 sovereign extensions (compliance/OSCAL/SIGIL) that OpenFang doesn't have. The extensions are marked in the spec file with comments explaining they're MEOK-specific.

## File structure

```
sovereign-temple/
├── hand-spec/
│   ├── sov3-hand-manifest.spec.toml    ← THIS SPEC (the example/template)
│   ├── README.md                       ← THIS FILE
│   └── validate_hand_toml.py           ← structural validator
├── team-templates/
│   ├── sovereign-council.toml          ← 12-Queen + King council (Phase 3)
│   ├── validate_council_toml.py
│   └── test_validate_council_toml.py
└── data/
    └── council_queens_personas.json    ← canonical queen personas
```

The 3 M4 deliverables in this lane:
1. **spec** (this file) — the manifest schema
2. **council** (team-templates/) — the 12-Queen governance
3. **examples** (future) — concrete HAND.toml files for our 313+ MCPs

---

*M4 lane · 2026-06-27 · MIT-licensed · Adapted from RightNow-AI/openfang (MIT)*