# MEOKBRIDGE

> **Universal Compute & Service Connector** — One bridge to connect your MacBooks, PCs, GPUs, MCPs, A2A agents, and APIs.

---

## What is MEOKBRIDGE?

MEOKBRIDGE is the universal abstraction layer that makes connecting any AI compute or service as simple as one command.

**Before MEOKBRIDGE:**
- Configure Ollama on your MacBook
- Set up SSH tunnel to Vast.ai
- Write custom code for OpenRouter API
- Figure out MCP server connections
- Manage different auth methods for each

**After MEOKBRIDGE:**
```bash
meokbridge scan          # Auto-discover everything
meokbridge chat          # Talk to the best available model
```

---

## Supported Backends

| Backend | Type | Discovery | Status |
|---------|------|-----------|--------|
| **Ollama** | Local LLM | mDNS, LAN scan, manual | ✅ Ready |
| **MLX** | Apple Silicon | Manual | ✅ Ready |
| **llama.cpp** | Local LLM | LAN scan, manual | ✅ Ready |
| **vLLM** | Local/Cloud | Manual | ✅ Ready |
| **OpenAI-compatible** | Cloud API | Manual | ✅ Ready |
| **MCP** | Tools | Manual | ✅ Ready |
| **A2A** | Agents | mDNS, manual | ✅ Ready |
| **WebLLM** | Browser | Manual | ✅ Ready |

---

## Quick Start

### 1. Install

```bash
pip install pyyaml httpx fastapi uvicorn
# Or if in sovereign-temple repo:
export PYTHONPATH=/Users/nicholas/clawd/sovereign-temple:$PYTHONPATH
```

### 2. Auto-Discover Your Network

```bash
python -m meokbridge.cli scan
```

This finds:
- Ollama on your MacBook M4 (localhost:11434)
- Ollama on your MacBook Air M2 (m2-air.local:11434)
- Vast.ai SSH tunnel (localhost:11436)
- Any other Ollama/llama.cpp on your LAN

### 3. Chat

```bash
python -m meokbridge.cli chat
```

Auto-routes to the best available node. Prefers local, falls back to cloud.

### 4. Council Mode

```bash
python -m meokbridge.cli council "Explain quantum computing"
```

Queries ALL your nodes and returns consensus.

---

## Python API

```python
import asyncio
from meokbridge import MeokBridge, Node, NodeType

bridge = MeokBridge()

# Add nodes
bridge.add_node(Node(id="m4", name="MacBook M4", node_type=NodeType.OLLAMA, url="http://localhost:11434", priority=10))
bridge.add_node(Node(id="vast", name="Vast GPU", node_type=NodeType.OLLAMA, url="http://localhost:11436", priority=5))
bridge.add_node(Node(id="openrouter", name="OpenRouter", node_type=NodeType.OPENAI_API, url="https://openrouter.ai/api/v1", api_key="...", priority=1))

# Chat (auto-routed)
result = await bridge.chat("Hello world")
print(result.text, result.node_id, result.latency_ms)

# Council mode
consensus = await bridge.council_chat("Is this code secure?")
print(consensus["consensus_text"], consensus["consensus_score"])

# Embeddings
embeddings = await bridge.embed(["Hello", "World"])
```

---

## Config File

`~/.meokbridge/config.yaml`:

```yaml
nodes:
  - id: m4-local
    name: MacBook M4
    type: ollama
    url: http://localhost:11434
    priority: 10
    tags: [local, primary]

  - id: m2-sidekick
    name: MacBook Air M2
    type: ollama
    url: http://m2-air.local:11434
    priority: 5
    tags: [local, mesh]

  - id: vast-cloud
    name: Vast.ai GPU
    type: ollama
    url: http://localhost:11436
    priority: 3
    tags: [cloud, heavy]

  - id: openrouter
    name: OpenRouter
    type: openai_api
    url: https://openrouter.ai/api/v1
    api_key: ${OPENROUTER_API_KEY}
    priority: 1
    tags: [cloud, api, fallback]

  - id: postgres-mcp
    name: PostgreSQL MCP
    type: mcp
    transport: stdio
    command: npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb
    tags: [tool, database]

settings:
  health_check_interval: 30
  default_temperature: 0.7
  prefer_local: true
```

---

## REST API

Start the server:
```bash
python -m meokbridge.api
# → http://localhost:3205
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Bridge status |
| `/nodes` | GET | List all nodes |
| `/nodes` | POST | Add a node |
| `/nodes/{id}` | DELETE | Remove a node |
| `/v1/chat` | POST | Chat (auto-routed) |
| `/v1/council` | POST | Council mode |
| `/v1/embed` | POST | Embeddings |

### Example

```bash
curl -X POST http://localhost:3205/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "prefer_local": true}'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEOKBRIDGE                                │
├─────────────────────────────────────────────────────────────────┤
│  CLI  │  Python API  │  REST API  │  Config (YAML)             │
├───────┴──────────────┴────────────┴─────────────────────────────┤
│                      Core Orchestrator                           │
│  • Node registry  • Health checks  • Auto-routing  • Council    │
├─────────────────────────────────────────────────────────────────┤
│                     Protocol Adapters                            │
│  Ollama  │  OpenAI  │  MCP  │  A2A  │  llama.cpp  │  vLLM     │
├─────────────────────────────────────────────────────────────────┤
│                      Discovery Layer                             │
│  mDNS/Bonjour  │  LAN Scan  │  Tunnel Detection  │  Manual    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Roadmap

- [ ] WebSocket streaming support
- [ ] Automatic failover with retry logic
- [ ] Cost tracking and budget alerts
- [ ] Prometheus metrics export
- [ ] Kubernetes operator for cloud deploy
- [ ] Plugin system for custom adapters
- [ ] GUI dashboard (web)

---

*MEOKBRIDGE: Connect everything. Control nothing (except your own infrastructure).*
