# Sovereign Temple — Public Release v3

> **Sovereign AI Infrastructure for Multi-Agent Governance**
> 
> Built by MEOK AI Labs (CSOAI Ltd) | Open Source | MIT License

## What This Is

Sovereign Temple is the core infrastructure stack for running governed, multi-agent AI systems. It provides:

- **Sigil Bus** — Ed25519-signed attestation chain for every agent action
- **BFT Council** — Byzantine Fault Tolerant consensus for agent governance
- **Multi-Agent Swarm** — Coordinated agent execution with role-based permissions
- **A2A Protocol** — Agent-to-agent communication via Google A2A spec
- **MCP Server Layer** — 290+ Model Context Protocol tools for compliance
- **Bridge Architecture** — Cross-platform agent coordination (Mac, VM, GCP)

## Architecture

```
┌─────────────────────────────────────────┐
│           SOV3 KING ORCHESTRATOR         │
│         (Consensus + Routing)           │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
┌───v───┐ ┌──v───┐ ┌────v───┐ ┌───v───┐
│Finance│ │Gov   │ │Security│ │Innov  │
│Hive   │ │Hive  │ │Hive    │ │Hive  │
└───┬───┘ └──┬───┘ └────┬───┘ └───┬───┘
    │        │          │         │
    └────────┴──────────┴─────────┘
               │
        ┌──────v──────┐
        │ SIGIL CHAIN │  ← Ed25519 attested
        │  (Ledger)   │    every action
        └─────────────┘
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Sigil Bus | `multi_agent/sigil_bus.py` | Attestation + event bus |
| Sigil Ed25519 | `multi_agent/sigil_ed25519.py` | Cryptographic signing |
| Swarm Coordinator | `multi_agent/swarm_coordinator.py` | Agent task delegation |
| A2A Server | `a2a-protocol/server.py` | Agent-to-agent protocol |
| Meok Bridge | `meokbridge/` | Cross-platform MCP bridge |
| Legion Omega | `legion-omega/` | Production orchestration |

## Stats

- 290+ MCP tools
- 47 agent hives
- 6,471+ attestation certs (and growing)
- 173 BFT council rounds
- 49 GB data moat
- 28 active verticals

## License

MIT — See LICENSE file

## Contact

CSOAI.org | MEOK AI Labs
