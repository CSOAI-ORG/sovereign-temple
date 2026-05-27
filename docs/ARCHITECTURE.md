# System Architecture - Sov3 / Jarvis / Meok OS

## Overview

This document describes the architecture of the Sov3 (Sovereign Temple v3), Jarvis, and Meok OS systems.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                MEOK OS (Frontend)                            │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Next.js UI (port 3000)                                              │    │
│  │  ├── /api/sov3/* → Sov3 Client                                        │    │
│  │  ├── /api/jarvis/* → Jarvis Execute                                   │    │
│  │  └── /api/chat/* → Chat Pipeline                                     │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              JARVIS (Action Layer)                          │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  MCP Tool Executor (port 3101)                                       │    │
│  │  ├── 75+ MCP Tools                                                  │    │
│  │  ├── Voice Pipeline (20+ modules)                                   │    │
│  │  └── Memory Management                                              │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SOV3 (Consciousness Layer)                        │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Sovereign Temple v3.0                                               │    │
│  │  ├── Consciousness States: JAGRAT, SVAPNA, SUSUPTI, TURIYA         │    │
│  │  ├── 235 Council Nodes                                               │    │
│  │  ├── Care Membrane / Maternal Covenant                               │    │
│  │  ├── Anomaly Detection                                              │    │
│  │  └── Quantum: QAOA, VQE, Grover                                      │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Agents: Orion, Riri, Hourman                                        │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Meok OS (Frontend)
- **Location**: `/Users/nicholas/clawd/meok/ui`
- **Tech**: Next.js 15, React 19, TypeScript
- **Ports**: 3000 (dev), 3001 (prod)
- **Auth**: Clerk

### Jarvis (Action Layer)
- **Location**: `/Users/nicholas/clawd/sovereign-temple/voice_pipeline/`
- **Purpose**: MCP tool execution, voice processing
- **Port**: 3101 (MCP)

### SOV3 (Consciousness Layer)
- **Location**: `/Users/nicholas/clawd/sovereign-temple/`
- **Purpose**: Consciousness, care routing, deliberation
- **API**: `/Users/nicholas/clawd/sovereign-temple-live/sov-api.py`

## API Endpoints

### Meok UI → Jarvis
- `POST /api/jarvis/execute` - Execute MCP tool
- `GET /api/jarvis/status` - Get Jarvis status
- `GET /api/jarvis/state` - Get Jarvis state

### Meok UI → SOV3
- `GET /api/sov3/status` - Get SOV3 health
- `GET /api/sov3/nemotron` - Nemotron tasks
- `GET /api/sov3/orion` - Orion agent
- `GET /api/sov3/tasks` - Task management

## Testing

### Unit Tests
- `/Users/nicholas/clawd/sovereign-temple/tests/test_sov3.py`
- `/Users/nicholas/clawd/sovereign-temple/tests/test_jarvis.py`

### Integration Tests
- `/Users/nicholas/clawd/sovereign-temple/tests/integration/test_pipeline.py`

### E2E Tests (Playwright)
- `/Users/nicholas/clawd/meok/ui/e2e/*.spec.ts`

## Monitoring

- **Metrics**: `/Users/nicholas/clawd/sovereign-temple/monitoring/metrics_collector.py`
- **Alerts**: `/Users/nicholas/clawd/sovereign-temple/monitoring/alert_system.py`
- **Bridge**: `/Users/nicholas/clawd/sovereign-temple/monitoring/bridge.py`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SOV3_API_URL | SOV3 API endpoint | http://localhost:3100 |
| SOV3_MCP_URL | SOV3 MCP endpoint | http://localhost:3101 |
| DATABASE_URL | PostgreSQL connection | - |
| CLERK_SECRET_KEY | Clerk auth | - |
