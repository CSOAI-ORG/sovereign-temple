# MEOKCLAW Dual-Brain MCP Server

Sovereign AI orchestration via the [Model Context Protocol](https://modelcontextprotocol.io).

## Tools

| Tool | Description |
|------|-------------|
| `meokclaw_think` | Single-query dual-brain inference with automatic fallback |
| `meokclaw_council` | Multi-model Byzantine Council with BFT consensus |
| `meokclaw_quantman` | Nested dual-brain reasoning (HY3 convergence) |
| `meokclaw_guardrails_check` | Neural guardrails — injection, PII, content checks |
| `meokclaw_model_health` | Per-model latency/error health tracker |

## Install

```bash
pip install meokclaw-dualbrain-mcp
```

## Configure

Set the MEOKCLAW API endpoint:

```bash
export MEOK_API_URL="http://localhost:3201"  # or your deployed URL
```

## Run

```bash
# stdio (default for MCP clients)
meokclaw-dualbrain-mcp

# SSE (for remote access)
meokclaw-dualbrain-mcp --transport sse --port 8080
```

## Claude Desktop Config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "meokclaw": {
      "command": "meokclaw-dualbrain-mcp",
      "env": {
        "MEOK_API_URL": "http://localhost:3201"
      }
    }
  }
}
```

## License

MIT — MEOK AI Labs
