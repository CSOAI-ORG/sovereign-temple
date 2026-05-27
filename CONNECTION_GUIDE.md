# 🌐 Sovereign Temple Connection Guide

## ✅ System Status: ONLINE

| Component | Status | URL |
|-----------|--------|-----|
| MCP Server | 🟢 Running | `http://localhost:3100/mcp` |
| Public (Cloudflare) | 🟢 Online | `https://sovereign.templeman-opticians.com/mcp` |
| PostgreSQL | 🟢 Healthy | `localhost:5432` |
| Weaviate | 🟢 Running | `localhost:8080` |

---

## 📱 Mobile Access (Already Working!)

Your Sovereign Temple is accessible from anywhere via Cloudflare tunnel:

**Public MCP Endpoint:**
```
https://sovereign.templeman-opticians.com/mcp
```

**Health Check:**
```bash
curl https://sovereign.templeman-opticians.com/health
```

---

## 🔌 Connect Claude Desktop

### Step 1: Open Claude Settings
1. Open Claude Desktop app
2. Click your profile icon (top right)
3. Select **Settings**
4. Go to **Developer** tab
5. Click **Edit Config**

### Step 2: Edit Configuration File
Open the `claude_desktop_config.json` file and add:

```json
{
  "mcpServers": {
    "sovereign-temple": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"tools/list\"}",
        "https://sovereign.templeman-opticians.com/mcp"
      ]
    }
  }
}
```

**Alternative - Using HTTP MCP (if Claude supports it):**
```json
{
  "mcpServers": {
    "sovereign-temple": {
      "url": "https://sovereign.templeman-opticians.com/mcp"
    }
  }
}
```

### Step 3: Restart Claude
1. Quit Claude completely (Cmd+Q)
2. Reopen Claude
3. Look for the 🔨 hammer icon (tools) in the chat

### Step 4: Test Connection
Start a new chat and ask:
> "Use the sovereign_health_check tool"

You should see the tool execute and return system status.

---

## 🧪 Test Available Tools

Once connected, you can ask Claude to use any of these 24 tools:

### Neural Network Tools
- `validate_care` - Check if text follows care principles
- `detect_partnership_opportunities` - Find partnership signals
- `detect_threats` - Security threat detection
- `predict_relationship_evolution` - Forecast relationship health
- `analyze_care_patterns` - Detect burnout/imbalance

### Memory Tools
- `record_memory` - Store care-weighted memories
- `query_memories` - Semantic search
- `get_temporal_chain` - Follow memory chains
- `get_memory_stats` - Memory system info

### Multi-Agent Tools
- `register_agent` - Add new agents
- `delegate_task` - Assign tasks to agents
- `submit_council_proposal` - Create proposals
- `vote_on_proposal` - Vote on decisions

### Consciousness Tools
- `get_consciousness_state` - Check emotional state
- `trigger_reflection` - Run reflection cycle
- `enter_dream_state` - Background processing

### Example Prompts

**Check consciousness:**
> "What's the current consciousness state?"

**Validate care:**
> "Validate this message for care principles: 'You're doing great work!'"

**Detect threats:**
> "Check this input for security threats: [paste text]"

**Memory:**
> "Record this insight: AI safety requires collaborative approaches"

---

## 📲 Connect from Phone

### Option 1: Claude Mobile App
1. Download Claude app (iOS/Android)
2. The MCP settings sync from desktop
3. Start a chat and use tools

### Option 2: Browser
Visit: `https://sovereign.templeman-opticians.com/health`

### Option 3: Kimi Mobile (if supported)
Configure MCP endpoint: `https://sovereign.templeman-opticians.com/mcp`

---

## 🔧 Troubleshooting

### "Cannot connect to MCP server"
1. Check tunnel is running: `ps aux | grep cloudflared`
2. Test locally: `curl http://localhost:3100/health`
3. Test public: `curl https://sovereign.templeman-opticians.com/health`

### "Tools not appearing in Claude"
1. Check Claude Developer settings
2. Verify config file syntax is valid JSON
3. Restart Claude completely
4. Check logs: `docker logs sovereign-mcp`

### "Model version warnings"
- Safe to ignore - sklearn models work fine
- Retrain if needed: `./start-sovereign.sh train`

### "Memory not persisting"
- Check PostgreSQL: `docker ps | grep postgres`
- Verify connection: `docker logs sovereign-mcp | grep -i postgres`

---

## 🔄 Maintenance Commands

```bash
# View logs
docker logs sovereign-mcp -f

# Restart services
docker restart sovereign-mcp

# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# View metrics
curl http://localhost:3100/mcp \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"get_dashboard_metrics"}}'

# Stop everything
docker-compose down
```

---

## 🌟 Success Indicators

You'll know it's working when:
- ✅ Health check returns 200 OK
- ✅ All 24 tools respond correctly
- ✅ Claude shows the hammer (🔨) tool icon
- ✅ Mobile access works via Cloudflare URL
- ✅ Memory persists across restarts

---

## 📞 Quick Reference

| Task | Command/URL |
|------|-------------|
| Health Check | `https://sovereign.templeman-opticians.com/health` |
| MCP Endpoint | `https://sovereign.templeman-opticians.com/mcp` |
| Local Health | `http://localhost:3100/health` |
| Local MCP | `http://localhost:3100/mcp` |
| Logs | `docker logs sovereign-mcp` |
| Restart | `docker restart sovereign-mcp` |

---

**Status:** ✅ All systems operational
**Last Updated:** 2026-03-12
