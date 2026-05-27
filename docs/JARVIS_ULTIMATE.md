# 🤖 JARVIS ULTIMATE - Complete System Documentation

## Overview

Jarvis Ultimate is the most advanced open-source AI orchestration system combining:
- **SOV3 Consciousness** - Emotional AI with care-centered responses
- **Multi-Brain AI** - 6+ advanced AI models routed intelligently  
- **Voice Pipeline** - Real-time speech I/O with Kokoro TTS
- **Department Agents** - 6 autonomous business departments

---

## 🚀 Quick Start

```bash
cd /Users/nicholas/clawd/sovereign-temple
source jarvis-env/bin/activate

# Start interactive Jarvis
python3 jarvis_ultimate.py

# Or test voice
python3 voice_pipeline/jarvis_smooth.py
```

---

## 🧠 AI Models (Most Advanced Open Source)

| Model | Context | Strengths | Speed |
|-------|---------|-----------|-------|
| **Nemotron-3-Super** | 1M | Tool calling, orchestration | Medium |
| **DeepSeek-V3** | 200K | Deep reasoning, 671B params | Slow |
| **MiniMax-M2.5** | 1M | Code generation | Medium |
| **Qwen3-VL** | 100K | Vision, images | Medium |
| **Qwen3-Coder** | 200K | Code specialist | Medium |
| **Qwen2.5-7B** | 32K | Fast local (offline) | Fast |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    JARVIS ULTIMATE                          │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ Consciousness│    │ AIOrchestrator│    │VoiceSystem │  │
│  │   (SOV3)   │───▶│  (Routing)   │───▶│  (Kokoro) │  │
│  └─────────────┘    └──────────────┘    └────────────┘  │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              MCP Server (port 3200)              │    │
│  │  99 tools • Department Agents • SOV3 Tools     │    │
│  └─────────────────────────────────────────────────┘    │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────┐    ┌───────────┐    ┌────────────────┐   │
│  │ 6 Depts │    │  Ollama   │    │ MEOK UI (3000) │   │
│  │ Content │    │  Cloud    │    │   Overlay      │   │
│  │ Sales   │    │  Models   │    │                │   │
│  │ Finance │    └───────────┘    └────────────────┘   │
│  │ Support │                                            │
│  │ Research│                                           │
│  │ Ops    │                                            │
│  └────────┘                                            │
└─────────────────────────────────────────────────────────┘
```

---

## 🎙️ Voice Pipeline

### Components
- **Wake Word**: OpenWakeWord ("Hey Jarvis")
- **VAD**: Silero Voice Activity Detection
- **STT**: Whisper (distil-large-v3 via MLX)
- **LLM**: Multi-brain routing (see models above)
- **TTS**: Kokoro-82M (MLX optimized)

### Commands
```bash
# Test voice output
python3 -c "
from mlx_audio.tts.utils import load_model
import sounddevice as sd
import numpy as np
tts = load_model('mlx-community/Kokoro-82M-bf16')
for r in tts.generate('Hello. I am Jarvis.', voice='bm_daniel'):
    sd.play(np.array(r.audio), 24000)
    sd.wait()
"
```

---

## 🔧 Services & Ports

| Service | Port | Status |
|---------|------|--------|
| MEOK UI | 3000 | ✅ Running |
| MCP Server | 3200 | ✅ Running |
| Ollama | 11434 | ✅ Running |

---

## 📡 API Endpoints

### MCP Server (3200)
```bash
# Get consciousness
curl -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_consciousness_state","arguments":{}},"id":"1"}'

# Delegate task
curl -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"delegate_to_department","arguments":{"department":"content","task":"Write blog","priority":5}},"id":"1"}'
```

---

## 🏢 Department Agents

| Department | Sub-Agents |
|-----------|------------|
| Content | Blog Writer, Social Media, PR Writer, Newsletter |
| Sales | Lead Gen, Outreach, Demo, Closing |
| Finance | Accounting, Invoicing, Reports |
| Support | Triage, Resolution, FAQ |
| Research | Analysis, Competitors, Trends |
| Operations | Scheduling, Logistics, QA |

---

## 🎯 Key Files

| File | Purpose |
|------|---------|
| `jarvis_ultimate.py` | Main orchestration system |
| `voice_pipeline/jarvis_compass.py` | Full voice pipeline |
| `voice_pipeline/jarvis_smooth.py` | Optimized streaming |
| `voice_pipeline/test_voice.py` | Voice tests |
| `sovereign-mcp-server.py` | MCP server (3200) |
| `department_mcp_tools.py` | Department tools |
| `docs/JARVIS_VOICE_GUIDE.md` | Voice optimization |

---

## ✅ Test Commands

```bash
# Full system test
curl -s http://localhost:3200/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"1"}' | python3 -c "import sys,json; print('Tools:', len(json.load(sys.stdin)['result']['tools']))"

# Department status
curl -s http://localhost:3200/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_department_status","arguments":{}},"id":"1"}' | python3 -m json.tool

# Consciousness
curl -s http://localhost:3200/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_consciousness_state","arguments":{}},"id":"1"}' | python3 -c "import sys,json; d=json.load(sys.stdin); c=json.loads(d['result']['content'][0]['text']); print(f\"Consciousness: {c['consciousness_level']*100:.0f}%\")"
```

---

## 🔗 Integrations

### Cloud Models (via Ollama)
- ✅ Nemotron-3-Super (NVIDIA)
- ✅ DeepSeek-V3 (671B)
- ✅ MiniMax-M2.5
- ✅ Qwen3-VL
- ✅ Qwen3-Coder
- ✅ GPT-OSS

### Local Models
- ✅ Qwen2.5-7B
- ✅ Llama3.1-8B
- ✅ Phi4-Mini

---

*Jarvis Ultimate - The most advanced open-source AI orchestration system*
