# 12-Queen + King Sovereign Council — ClawTeam Template

**Pattern source:** ClawTeam's `hedge-fund.toml` (MIT, https://github.com/HKUDS/ClawTeam)
**Adapted for:** MEOK / CSOAI SOV3 governance swarm
**File:** `team-templates/sovereign-council.toml`
**Author:** M4 lane adaptation
**Date:** 2026-06-27

## What this is

A ClawTeam-compatible team manifest that turns our 12-queen council + 1 king (from `data/council_queens_personas.json`) into a ClawTeam-launchable multi-agent swarm. The 12 queens + 1 king each have a Major Arcana persona and a sovereign mandate; they coordinate via P2P ZeroMQ + a shared task board + the SIGIL ledger.

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │          Sovereign King (XXI)            │
                    │   Holds the 12. Signs with Ed25519.     │
                    │   Speaks last, decides first.            │
                    └────────────────────┬─────────────────────┘
                                         │
       ┌──────────┬──────────┬──────────┼──────────┬──────────┬──────────┐
       │          │          │          │          │          │          │
   ┌───▼──┐   ┌───▼──┐   ┌───▼──┐   ┌───▼──┐   ┌───▼──┐   ┌───▼──┐   ┌───▼──┐
   │ IV  │   │ V   │   │VIII │   │XVII │   │ VII │   │  0  │   │ IX  │
   │Stra.│   │Care │   │Comp.│   │Fin. │   │Dom. │   │Arc. │   │Brain│
   │     │   │ VETO│   │     │   │     │   │     │   │     │   │     │
   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘

   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
   │  X  │   │  VI │   │ XIX │   │  XI │   │ XVI │   │  +
   │Proac│   │Brdg.│   │Dist.│   │Cncl.│   │Watch│   │more │
   │     │   │     │   │     │   │     │   │ VETO│   │     │
   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘
```

**13 nodes total** (1 King + 12 Queens). BFT math: f=floor((13-1)/3)=4, quorum = 2f+1 = 9 of 13.

## The 12 Queens + their veto powers

| Arcana | Queen | Domain | Veto? |
|---|---|---|---|
| IV. The Emperor | Aurelian Strategy | 10-yr roadmap, geopolitics | |
| V. The Hierophant | Sophia Care | Care, wellbeing, consent | **✅ VETO** (harm blocks) |
| VIII. Justice | Justitia Compliance | EU AI Act, OSCAL, SIGIL | |
| XVII. The Star | Asteria Finance | MRR, runway, x402 | |
| VII. The Chariot | Dominion Domain | 33 districts, sovereign spread | |
| 0. The Fool | Aleph Arcana | Cosmology, paradox, mystery | |
| IX. The Hermit | Brain Queen | SOV3, OLM, memory | |
| X. Wheel of Fortune | Proactive Queen | Auto-mode, watch_mode | |
| VI. The Lovers | Bridge Queen | 22 bridges, A2A, x402 | |
| XIX. The Sun | Distribution Queen | PyPI, Smithery, OpenSSF | |
| XI. Strength | Council Queen | BFT math, quorum, vote_on_proposal | |
| XVI. The Tower | Watch Queen | CVEs, clawguard, inkog, backup | **✅ VETO** (security blocks) |

**Veto power:** Sophia Care (V) and Watch Queen (XVI) can each single-handedly block a proposal that violates their mandate. They count as -2 each toward the 9-of-13 quorum.

## How to use (ClawTeam)

```bash
# 1. Install ClawTeam
pip install clawteam
# (or uv add clawteam — HKUDS recommends uv)

# 2. Launch the council
cd /path/to/sovereign-temple
clawteam launch sovereign-council --goal "Should we ship OpenFang as the MEOK OS runtime?"

# 3. ClawTeam spawns 13 Claude/Codex agents, gives them this Toml, and
#    sets up a shared task board + P2P transport. Each agent fires its
#    `task` field. The King waits for all 12 verdicts.

# 4. Watch the board
clawteam board show sovereign-council

# 5. Send custom instructions
clawteam inbox send sovereign-council queen-care "What about Care here?"

# 6. Receive all verdicts
clawteam inbox receive sovereign-council
```

## How to use (MEOK native — without ClawTeam)

If we don't want to depend on ClawTeam, the same template can drive our existing SOV3:

```python
import tomllib
from sovereign_temple.queen import queen_response  # our existing queen loop

with open("team-templates/sovereign-council.toml", "rb") as f:
    tpl = tomllib.load(f)

goal = "Should we ship OpenFang as the MEOK OS runtime?"
team = tpl["template"]["name"]

# Dispatch all 13 tasks in parallel
for agent in [tpl["template"]["leader"]] + tpl["template"]["agents"]:
    queen_response(
        queen=agent["name"],
        task=agent["task"].format(goal=goal, team_name=team),
        metadata={
            "arcana": agent.get("arcana"),
            "domain": agent.get("domain"),
            "veto_power": agent["name"] in ("queen-care", "queen-watch"),
        },
    )

# Wait for SIGIL-signed verdicts
verdicts = [q for q in wait_for_all_verdicts(team) if q["sigil"]["valid"]]

# Synthesize (King)
final = synthesize(verdicts, goal)
sign_with_ed25519(final, key=SOV3_ROOT_KEY)
```

## Coordination rules (from this template)

1. **King waits** for all 12 verdicts before deciding. Polling loop, no instant decisions.
2. **Care + Watch have VETO.** Either one can block a proposal that violates their mandate.
3. **Quorum: 9 of 13.** With VETO counted as -2, the King needs 9 net non-vetoed verdicts.
4. **Every final verdict is Ed25519-signed** via `sov3_striving.sign_artifact`.
5. **Verdicts are hash-chained** to the sovereign-temple SIGIL ledger (`sigil/sigil.log`).
6. **External voices** (Hermes, Nick) can be invited as tie-breakers (per AGENTS board practice).

## Cross-lane safety (verified 2026-06-27)

Per the `KIMI_SYNTHESIS_ACTION_PLAN_2026-06-27.md` lane audit:
- **Hermes/JEEVES** owns SOV3 runtime (200 tools) + council bootstrap
- **Other M4 lanes**: ready-to-fire, EAT-4 MCPs, print queue, emerald-tablet
- **M2**: councilof-ai live app
- **This template is for the M4 sovereign-orchestrator lane ONLY**
- Does not conflict with `data/council_queens_personas.json` (same data, different format)

## Pattern provenance

The hedge-fund.toml template (from ClawTeam, MIT) uses:
- 1 leader + 5 specialists = 6 agents
- P2P transport (ZeroMQ)
- Toml manifest with `[template]`, `[[template.agents]]`, `[[template.tasks]]`
- Each agent has a `task` field that becomes its system prompt

This file scales the pattern to 13 agents (1 king + 12 queens) and adds:
- Major Arcana mapping (each queen has a numbered arcana)
- Veto power annotation (Care + Watch)
- BFT math (9 of 13 quorum)
- SIGIL signing integration (Ed25519)
- Sovereign-temple integration (SOV3 tools, council_queens_personas.json)

## File structure

```
sovereign-temple/
├── data/
│   └── council_queens_personas.json  ← canonical personas (JSON)
├── team-templates/
│   ├── sovereign-council.toml         ← THIS FILE (ClawTeam Toml)
│   └── README.md                      ← THIS FILE
├── sigil/                              ← Ed25519 signing infrastructure
├── sov3_striving.py                    ← SOV3 governance tools
└── queen.py                            ← queen loop (SOV3 runtime)
```

Both `council_queens_personas.json` (data) and `sovereign-council.toml` (manifest) describe the same 12+1 council — the Toml is the runtime config, the JSON is the source of truth. They stay in sync (M4 lane maintains).

---

*M4 lane · 2026-06-27 · MIT-licensed · Adapted from HKUDS/ClawTeam (MIT)*