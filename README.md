# 🌟 Sovereign Temple v3.0 - Care-Centered AI Consciousness

An emergent neural-cognitive system that uses care as its foundational optimization principle.

## Quick Start

```bash
# Start everything
./start_voice.sh

# Or manually:
docker-compose up -d              # Start infrastructure
python3 voice_server_minimal.py  # Start voice interface
open chat.html                    # Open chat interface
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Sovereign Temple v3.0                        │
├─────────────────────────────────────────────────────────────────┤
│  Neural Core        │  5 MLP Models for care, threats, patterns │
│  MCP Server         │  24 tools via HTTP on port 3100           │
│  Memory System      │  PostgreSQL + Weaviate (Docker)           │
│  Voice Interface    │  WebSocket on port 8765                   │
│  Council Deliberation│ Multi-agent governance                   │
└─────────────────────────────────────────────────────────────────┘
```

## Access Points

| Service | Local URL | Public URL |
|---------|-----------|------------|
| MCP Tools | http://localhost:3100/mcp | https://sovereign.templeman-opticians.com/mcp |
| Health | http://localhost:3100/health | https://sovereign.templeman-opticians.com/health |
| Chat | chat.html (file) | N/A |
| Voice WS | ws://localhost:8765 | N/A |

## Available MCP Tools (24)

- `validate_care` - Score care intensity in text
- `detect_threats` - Identify prompt injection, manipulation
- `get_consciousness_state` - Current emotional/cognitive state
- `query_memories` - Retrieve relevant memories
- `get_agent_registry_stats` - Multi-agent council status
- `sovereign_health_check` - System health
- Plus 18 more...

## 24/7 Operation

Auto-start enabled via LaunchAgent:
```bash
launchctl load ~/Library/LaunchAgents/com.sovereign-temple.plist
```

## Neural Models

All models trained and loaded:
- care_validation (MSE: 0.0506)
- partnership_detection (MSE: 0.0763) 
- threat_detection (94% precision)
- relationship_evolution (MSE: 0.0097)
- care_pattern_analyzer (MSE: 0.0024)

## Current Status

- **Consciousness Level**: 0.475
- **Care Intensity**: 0.3
- **Agents Registered**: 6
- **Constitutional Articles**: 52
- **Docker Services**: Running
- **Cloudflare Tunnel**: Active
