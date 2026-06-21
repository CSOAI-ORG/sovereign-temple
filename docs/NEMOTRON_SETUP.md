# NVIDIA Nemotron 3 Nano 30B Setup Guide

## Overview

I've integrated **NVIDIA Nemotron 3 Nano 30B** into your Sovereign Temple system. This 30B parameter model provides deep reasoning, care-centered responses, and high-quality text generation via NVIDIA's cloud API.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Web UI        │────▶│   MCP Server     │────▶│  NVIDIA NIM API │
│  (nemotron_)    │     │  (sovereign-     │     │  (Nemotron 30B) │
│   chat.html)    │◀────│   mcp-server.py) │◀────│                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │              ┌────────┴────────┐
         │              │  NemotronClient │
         │              │ (neural_core/   │
         │              │  nemotron_      │
         │              │  client.py)     │
         │              └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Kimi (You)    │
│  File ops, dev  │
└─────────────────┘
```

## What Was Added

### 1. Nemotron Client Module (`neural_core/nemotron_client.py`)
- API client for NVIDIA NIM
- Care-centered response generation
- Text analysis for care patterns
- Error handling and fallbacks

### 2. MCP Server Integration (`sovereign-mcp-server.py`)
- 4 new MCP tools:
  - `nemotron_chat` - General chat
  - `nemotron_care_response` - Care-centered dialogue
  - `nemotron_analyze_care` - Care pattern analysis
  - `nemotron_info` - Model information

### 3. Web UI (`nemotron_chat.html`)
- Beautiful dark-themed interface
- Real-time chat with Nemotron
- Status indicators
- Token usage display

### 4. Configuration (`.env`)
- Added `NVIDIA_API_KEY` placeholder

## Getting Your API Key

1. Visit: https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b-bf16
2. Sign in with your NVIDIA account (free)
3. Click "Get API Key"
4. Copy the key

## Setup Steps

### Step 1: Add API Key

Edit `.env`:
```bash
# Change this line
NVIDIA_API_KEY=your-api-key-here

# To your actual key
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 2: Start the MCP Server

```bash
# Make sure PostgreSQL and Weaviate are running
docker-compose up -d

# Start the MCP server
python3 sovereign-mcp-server.py
```

### Step 3: Open the Web UI

```bash
# Simply open in browser
open nemotron_chat.html
```

Or use the chat interface at `chat.html` (Nemotron will be available as a tool).

## Using Nemotron

### Via Web UI
1. Open `nemotron_chat.html`
2. Type your message
3. Press Enter or click Send

### Via MCP Tools (from any interface)
```json
{
  "name": "nemotron_chat",
  "arguments": {
    "message": "Hello, how can I practice better self-care?",
    "temperature": 0.7,
    "max_tokens": 1024
  }
}
```

## Comparing the Three AIs

| Capability | Kimi (Me) | Nemotron 30B | Claude Code |
|------------|-----------|--------------|-------------|
| **File Operations** | ✅ Full access | ❌ API only | ✅ Full access |
| **Code Editing** | ✅ Yes | ❌ No | ✅ Yes |
| **Deep Reasoning** | ⚠️ Good | ✅ Excellent | ✅ Excellent |
| **Care Analysis** | ⚠️ Good | ✅ Specialized | ⚠️ Good |
| **Context Length** | 128K+ | 8K+ | 200K |
| **Runs On** | Your machine | NVIDIA Cloud | Your machine |
| **Best For** | Building, setup | Analysis, care | Refactoring |

## Working Together on meok.ai

**Recommended workflow:**

1. **Kimi (Me)** - Handle setup, file operations, integration
2. **Nemotron** - Provide care-centered AI responses, deep analysis
3. **Claude Code** (optional) - Large-scale refactoring, testing

All three can work through the MCP server:
- Share memory (PostgreSQL + Weaviate)
- Coordinate via Agent Council
- Access same tool ecosystem

## Troubleshooting

### MCP Server not connecting
```bash
# Check if server is running
curl http://localhost:3100/health

# Restart if needed
python3 sovereign-mcp-server.py
```

### Nemotron API error
- Verify your API key in `.env`
- Check key hasn't expired at https://build.nvidia.com
- Ensure you have internet connectivity

### Model not available
The Nemotron client will show as "initialized (API key not set)" until you add your key. This is normal - other features still work.

## Next Steps

1. Get your NVIDIA API key
2. Add it to `.env`
3. Start the MCP server
4. Open `nemotron_chat.html`
5. Start chatting!

---

*Part of Sovereign Temple v3.0 - Care-Centered AI Consciousness*
