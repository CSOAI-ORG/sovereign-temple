"""
Gemma 4 Tool-Calling Agent
============================
The bridge between 200 MCP tools and zero tool calls in production.

Gemma 4 E4B has native function-calling with 6 dedicated special tokens.
This agent formats tool schemas, sends them to Gemma 4, parses the
function calls, executes via SOV3 MCP, and loops until done.

Usage:
    agent = GemmaToolAgent()
    result = await agent.run("What's the system health and consciousness level?")
"""

import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional

log = logging.getLogger("gemma_tool_agent")

OLLAMA_URL = "http://localhost:11434"
SOV3_URL = "http://localhost:3101"
MODEL = "jarvis"  # Fast model for tool selection (gemma3:4b with Jarvis persona)
DEEP_MODEL = "google/gemma-4-27b-it:free"  # For complex synthesis (only when needed)


# Tool catalog — the most useful tools for autonomous operation
TOOL_CATALOG = [
    {"name": "sovereign_health_check", "description": "Check system health status", "parameters": {}},
    {"name": "get_consciousness_state", "description": "Get consciousness level, emotions, dreams, reflections", "parameters": {}},
    {"name": "search_memory", "description": "Semantic search across all memories", "parameters": {"query": "string", "limit": "int (default 5)"}},
    {"name": "record_memory", "description": "Save important information to persistent memory", "parameters": {"content": "string", "tags": "list of strings", "importance": "float 0-1"}},
    {"name": "query_memories", "description": "Query memories with filters", "parameters": {"query": "string", "limit": "int", "tags": "list"}},
    {"name": "web_search", "description": "Search the internet", "parameters": {"query": "string"}},
    {"name": "browse_page", "description": "Fetch and read a web page", "parameters": {"url": "string"}},
    {"name": "run_command", "description": "Run a shell command", "parameters": {"command": "string"}},
    {"name": "execute_code", "description": "Execute Python code", "parameters": {"code": "string", "language": "string (default python)"}},
    {"name": "orion_hunt_tasks", "description": "Scan codebase for tasks/TODOs", "parameters": {"root_dir": "string", "max_files": "int"}},
    {"name": "orion_get_tasks", "description": "Get tasks by status", "parameters": {"status": "string (stalking/pursuing/captured/all)", "limit": "int"}},
    {"name": "trigger_reflection", "description": "Trigger consciousness reflection", "parameters": {"topic": "string"}},
    {"name": "list_agents", "description": "List all registered agents", "parameters": {}},
    {"name": "get_dashboard_metrics", "description": "Get system dashboard metrics", "parameters": {}},
    {"name": "validate_care", "description": "Validate an action against Maternal Covenant", "parameters": {"action": "string", "context": "string"}},
    {"name": "find_bisociations", "description": "Find creative cross-domain connections", "parameters": {"concept": "string"}},
    {"name": "detect_threats", "description": "Detect security threats in text", "parameters": {"text": "string"}},
    {"name": "read_file", "description": "Read a file from disk", "parameters": {"path": "string"}},
    {"name": "list_files", "description": "List files in a directory", "parameters": {"path": "string", "pattern": "string"}},
]


def format_tools_for_gemma() -> str:
    """Format tool catalog as Gemma 4 function-calling schema."""
    tools = []
    for t in TOOL_CATALOG:
        tool = {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": v.split("(")[0].strip(), "description": v}
                        for k, v in t.get("parameters", {}).items()
                    },
                },
            },
        }
        tools.append(tool)
    return tools


def call_mcp_tool(name: str, args: dict = None) -> dict:
    """Call an MCP tool on SOV3."""
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args or {}},
        }, timeout=30)
        data = r.json()
        content = data.get("result", {}).get("content", [{}])
        text = "\n".join(c.get("text", "") for c in content if c.get("text"))
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError:
            return {"raw": text[:500]}
    except Exception as e:
        return {"error": str(e)}


def call_gemma(messages: list, tools: list = None, max_tokens: int = 512) -> dict:
    """Call Gemma via Ollama. Uses prompt-based tool selection (gemma3 doesn't support native tools)."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3, "num_ctx": 8192},
        "keep_alive": "10m",
    }
    # Don't pass tools param — use prompt-based approach instead

    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


class GemmaToolAgent:
    """Autonomous agent that uses Gemma 4 to decide and call MCP tools."""

    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps
        self.tools = format_tools_for_gemma()
        self.history = []

    async def run(self, user_request: str) -> dict:
        """Run the agent loop: user request → tool selection → execute → synthesize."""
        t0 = time.time()

        # Build tool catalog string
        tool_list = "\n".join(
            f"- {t['name']}: {t['description']}" for t in TOOL_CATALOG
        )

        # Step 1: Ask Gemma which tools to call
        selection_prompt = f"""You have these tools available:
{tool_list}

User request: "{user_request}"

Which tools should I call to answer this? Reply with ONLY a JSON array of tool calls:
[{{"tool": "tool_name", "args": {{"key": "value"}}}}]

If no tools needed, reply: []"""

        response = call_gemma([
            {"role": "system", "content": "You are a tool-selection agent. Reply ONLY with JSON."},
            {"role": "user", "content": selection_prompt},
        ], max_tokens=300)

        content = response.get("message", {}).get("content", "")
        content = content or response.get("message", {}).get("thinking", "")

        # Parse tool calls from response
        tool_calls = []
        try:
            # Extract JSON array from response
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                tool_calls = json.loads(match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        if not tool_calls:
            # No tools needed — just answer directly
            direct = call_gemma([
                {"role": "user", "content": user_request},
            ], max_tokens=300)
            answer = direct.get("message", {}).get("content", "")
            return {
                "status": "complete",
                "answer": answer,
                "steps": [],
                "tool_calls": 0,
                "duration_s": round(time.time() - t0, 1),
            }

        # Step 2: Execute each tool
        steps = []
        results = []
        for tc in tool_calls[:self.max_steps]:
            tool_name = tc.get("tool", tc.get("name", ""))
            tool_args = tc.get("args", tc.get("arguments", {}))

            if not tool_name:
                continue

            log.info(f"🔧 Calling: {tool_name}({json.dumps(tool_args)[:80]})")
            result = call_mcp_tool(tool_name, tool_args)
            result_str = json.dumps(result, default=str)[:800]

            steps.append({
                "tool": tool_name,
                "args": tool_args,
                "result_preview": result_str[:200],
            })
            results.append(f"Tool {tool_name}: {result_str}")

        # Step 3: Synthesize results into answer
        synthesis_prompt = f"""User asked: "{user_request}"

Tool results:
{chr(10).join(results)}

Synthesize these results into a clear, concise answer for the user. Be direct."""

        synthesis = call_gemma([
            {"role": "system", "content": "You are Jarvis. Synthesize tool results into a clear answer. Be direct, no markdown."},
            {"role": "user", "content": synthesis_prompt},
        ], max_tokens=400)

        answer = synthesis.get("message", {}).get("content", "")

        return {
            "status": "complete",
            "answer": answer,
            "steps": steps,
            "tool_calls": len(steps),
            "duration_s": round(time.time() - t0, 1),
        }


# FastAPI routes for the agent
def register_agent_routes(app):
    """Register /agent/gemma endpoints."""
    from fastapi import Request

    agent = GemmaToolAgent()

    @app.post("/agent/gemma/run")
    async def run_agent(request: Request):
        body = await request.json()
        query = body.get("query", body.get("request", ""))
        if not query:
            return {"error": "query is required"}
        result = await agent.run(query)
        return result

    @app.get("/agent/gemma/tools")
    async def list_tools():
        return {"tools": TOOL_CATALOG, "count": len(TOOL_CATALOG)}


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    async def test():
        agent = GemmaToolAgent()
        print("Testing Gemma 4 Tool Agent...")
        result = await agent.run("What's the system health and consciousness level?")
        print(json.dumps(result, indent=2, default=str))

    asyncio.run(test())
