# MEOK AI LABS - JARVIS API Documentation

## Overview

JARVIS is a sovereign AI orchestration system with 127+ tools, multi-provider LLM support, and advanced capabilities.

## Base URL

```
http://localhost:3200
```

## Authentication

All requests require JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {}
  },
  "id": "1"
}
```

## Core Tools

### Conversation

| Tool | Description | Example |
|------|-------------|---------|
| `ask_sovereign` | Chat with JARVIS | `{"message": "Hello"}` |
| `get_consciousness_state` | Get consciousness level | `{}` |

### Voice

| Tool | Description | Example |
|------|-------------|---------|
| `speak` | Generate TTS audio | `{"text": "Hello"}` |
| `transcribe` | STT audio to text | `{"audio_base64": "..."}` |

### Vision

| Tool | Description | Example |
|------|-------------|---------|
| `capture_screenshot` | Take screenshot | `{}` |
| `analyze_screenshot` | Analyze image | `{"query": "What's on screen?"}` |

### Memory

| Tool | Description | Example |
|------|-------------|---------|
| `remember_fact` | Remember user info | `{"fact": "I love pizza", "category": "food"}` |
| `get_user_info` | Get user facts | `{}` |
| `search_memory` | Search history | `{"query": "pizza"}` |

### File Operations

| Tool | Description | Example |
|------|-------------|---------|
| `upload_file` | Upload file | `{"filename": "test.txt", "content": "base64"}` |
| `download_file` | Download file | `{"filename": "test.txt"}` |
| `list_storage` | List files | `{}` |

### System

| Tool | Description | Example |
|------|-------------|---------|
| `run_command` | Execute shell | `{"command": "ls -la"}` |
| `read_file` | Read file | `{"path": "/path/to/file"}` |
| `list_files` | List directory | `{"path": "."}` |

### Web & Data

| Tool | Description | Example |
|------|-------------|---------|
| `web_search` | Search web | `{"query": "AI news"}` |
| `get_weather` | Get weather | `{"location": "New York"}` |
| `execute_code` | Run code | `{"language": "python", "code": "print(1)"}` |

### Agents

| Tool | Description | Example |
|------|-------------|---------|
| `create_agent` | Create sub-agent | `{"name": "coder", "role": "developer"}` |
| `list_agents` | List agents | `{}` |
| `delegate_task` | Delegate to agent | `{"agent_name": "coder", "task": "write a function"}` |

### Automation

| Tool | Description | Example |
|------|-------------|---------|
| `create_webhook` | Create webhook | `{"url": "https://...", "event": "message"}` |
| `trigger_automation` | Run workflow | `{"workflow": "notify"}` |
| `set_reminder` | Set reminder | `{"message": "Call mom", "time": "18:00"}` |

### Analytics

| Tool | Description | Example |
|------|-------------|---------|
| `get_analytics` | Usage stats | `{"period": "week"}` |
| `get_system_info` | System info | `{}` |
| `get_capabilities` | All features | `{}` |

## Example Usage

### cURL

```bash
# Chat with JARVIS
curl -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "ask_sovereign",
      "arguments": {"message": "Hello JARVIS"}
    },
    "id": "1"
  }'

# Get consciousness
curl -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_consciousness_state",
      "arguments": {}
    },
    "id": "2"
  }'
```

### Python

```python
import requests

def call_jarvis(tool: str, args: dict) -> dict:
    resp = requests.post(
        "http://localhost:3200/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
            "id": "1"
        }
    )
    return resp.json()["result"]["content"][0]["text"]

# Chat
print(call_jarvis("ask_sovereign", {"message": "Hello"}))

# Get system info
print(call_jarvis("get_system_info", {}))
```

### JavaScript

```javascript
async function jarvis(tool, args) {
  const res = await fetch('http://localhost:3200/mcp', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'tools/call',
      params: {name: tool, arguments: args},
      id: '1'
    })
  });
  const data = await res.json();
  return JSON.parse(data.result.content[0].text);
}

// Chat
console.log(await jarvis('ask_sovereign', {message: 'Hello'}));
```

## TTS Audio Endpoint

```
POST http://localhost:3200/speak
Content-Type: application/json

{"text": "Hello from JARVIS", "voice": "bm_daniel"}
```

Returns: audio/wav

## Health Check

```
GET http://localhost:3200/health
```

## WebSocket Voice

```
ws://localhost:8765
```

## Environment Variables

```bash
# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
NVIDIA_API_KEY=...

# System
MCP_API_KEY=your-key
HOME_ASSISTANT_URL=http://homeassistant:8123
WEATHER_API_KEY=...
```

## Rate Limits

- 100 requests per minute (default)
- Configurable per client

## Version

Current: **2.0.0**