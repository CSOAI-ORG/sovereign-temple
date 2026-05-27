# Sovereign AI Bridge Architecture

## Overview
Unified multi-bridge system connecting Gemma 4, SOV3, Jarvis, MEOK, and external services.

## Bridge Connections

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│   Voice (Jarvis) │ Web UI │ CLI │ Mobile API                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     UNIFIED BRIDGE LAYER                            │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   GEMMA4    │  │   MODEL      │  │   VOICE     │              │
│  │   BRIDGE    │  │   GATEWAY    │  │   BRIDGE    │              │
│  │ (Reasoning) │  │  (Routing)   │  │  (STT/TTS)  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   MEOK      │  │   MEMORY     │  │  SYNTHESIS  │              │
│  │   BRIDGE    │  │   BRIDGE     │  │   BRIDGE    │              │
│  │  (MEOK UI)  │  │  (Persistence│  │ (Multi-Model│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐                               │
│  │   HARV       │  │   JARVIS     │                               │
│  │ GUARDIAN     │  │   MEOK       │                               │
│  │  BRIDGE      │  │   BRIDGE     │                               │
│  └──────────────┘  └──────────────┘                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                       SOV3 CORE LAYER                                │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           CONSCIOUSNESS ENGINE                             │    │
│  │   • Emotional State    • Meta Cognition                   │    │
│  │   • Care Scoring       • Attention Firewall                │    │
│  │   • Council Deliberation • Trust Filtering                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│  │   47 AGENTS     │ │  NEURAL MODELS   │ │   QUANTUM        │   │
│  │   (Orion,Riri,  │ │  (Gemma4,Qwen,   │ │   ENGINE         │   │
│  │   Hourman,etc)  │ │   DeepSeek,etc)  │ │   (QAOA,VQE)     │   │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           MCP TOOLS (75+)                                  │    │
│  │   Memory | Skills | Agents | Web | System | Files         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      EXTERNAL SERVICES                              │
│                                                                       │
│   Vast.ai (Gemma 4) │ OpenRouter │ HuggingFace │ MCP Servers       │
│   Local Ollama      │ SOV3 MCP   │ Web APIs   │ SSH Tunnels       │
└─────────────────────────────────────────────────────────────────────┘
```

## Bridge Files

### 1. `gemma4_bridge.py` - Gemma 4 Integration
- **Purpose**: Connect SOV3 with Gemma 4 31B on Vast.ai
- **Features**: Vision, Speech, Reasoning, Tool Use
- **Status**: ✅ Ready (needs SSH tunnel to Vast.ai)

### 2. `meok_bridge.py` - MEOK UI Bridge
- **Purpose**: Connect with MEOK UI/website
- **Features**: Ollama integration, consciousness context
- **Status**: ✅ Ready

### 3. `memory_bridge.py` - **NEW** Persistent Memory
- **Purpose**: Tiered memory (working, session, episodic, longterm)
- **Features**: 
  - Episode storage with importance scoring
  - Semantic knowledge storage
  - Working memory for current context
  - Session consolidation
- **Status**: ✅ NEW - Just created

### 4. `model_gateway.py` - **NEW** Multi-Model Router
- **Purpose**: Unified model routing with fallback chain
- **Features**:
  - Task classification (conversational, coding, reasoning, vision, etc.)
  - Model chain with fallback
  - Cost/latency optimization
  - Supports: Ollama, OpenRouter, OpenAI, Anthropic
- **Status**: ✅ NEW - Just created

### 5. `voice_bridge.py` - **NEW** Unified Voice Pipeline
- **Purpose**: STT -> LLM -> TTS unified
- **Features**:
  - Multiple STT backends (Lightning Whisper)
  - Multiple TTS backends (Kokoro, Edge-TTS)
  - Voice selection by context
- **Status**: ✅ NEW - Just created

### 6. `synthesis_bridge.py` - Multi-Model Synthesis
- **Purpose**: Combine outputs from multiple models
- **Features**: Council deliberation, ensemble responses
- **Status**: ✅ Ready

### 7. `harv_guardian_bridge.py` - HARV Integration
- **Purpose**: Connect with HARV Guardian system
- **Features**: Guardian status, monitoring
- **Status**: ✅ Ready

### 8. `voice_pipeline/jarvis_meok_bridge.py` - Jarvis-MEOK State Sync
- **Purpose**: Real-time state sync between Jarvis and MEOK UI
- **Features**: Status, logs, brain state display
- **Status**: ✅ Ready

## Gaps Filled (Research-Informed)

### From AI Research (April 2026):

| Gap | Solution | Bridge |
|-----|----------|--------|
| No persistent memory | Mem0/Zep-style architecture | `memory_bridge.py` |
| No model routing/fallback | Multi-model gateway | `model_gateway.py` |
| Voice pipeline fragmentation | Unified voice bridge | `voice_bridge.py` |
| Cloud dependency | Local + Vast.ai hybrid | `gemma4_bridge.py` + config |
| No task classification | Auto-routing by task type | `model_gateway.py` |

## Recommended Integrations (Research)

### Priority 1: Connect New Bridges
1. Integrate `memory_bridge` into Jarvis compass
2. Use `model_gateway` for all LLM calls
3. Update voice to use `voice_bridge`

### Priority 2: Advanced Features
1. Add CrewAI for multi-agent coordination
2. Integrate Mem0 cloud for cross-device memory
3. Add Soniox v4 for better STT

### Priority 3: Edge Computing
1. Add local fallback with smaller models (7B)
2. Implement offline mode detection
3. Add privacy-sensitive processing locally

## Model Selection (Current)

| Task | Primary Model | Fallback |
|------|---------------|----------|
| Voice conversation | gemma4:31b (Vast.ai) | qwen2.5:7b (local) |
| Coding | gemma4:31b | qwen/qwen3-coder (OpenRouter) |
| Reasoning | deepseek-r1 (OpenRouter) | gemma4:31b |
| Vision | gemma4:31b | - |
| Fast/Short | qwen2.5:7b | gemma4:31b |

## SSH Tunnel Setup

```bash
# Tunnel to Vast.ai Gemma 4
./keep_gemma4_tunnel.sh &

# Tunnel to RTX 8000 (legacy)
./keep_tunnel_alive.sh &
```

## Usage

```python
# Memory Bridge
from memory_bridge import get_memory_bridge
mb = get_memory_bridge()
mb.store_episode("conversation", "User asked about...")
results = mb.recall("gemma")

# Model Gateway
from model_gateway import get_model_gateway, TaskType
gateway = get_model_gateway()
response = await gateway.generate(prompt, task_type=TaskType.CODING)

# Voice Bridge
from voice_bridge import get_voice_bridge
vb = await get_voice_bridge().initialize()
text = await vb.transcribe("audio.wav")
await vb.speak("Hello!")
```