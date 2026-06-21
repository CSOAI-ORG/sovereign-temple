"""
SOV3 Agent Executor — Taskiq + LangGraph
==========================================
The backbone that makes 47 agents actually execute tasks.

Architecture:
  Taskiq (async task queue via Redis) → LangGraph (execution graph with cycles)
  → SOV3 MCP tools → Result evaluation → Memory recording

This is the missing piece: agents could register but never autonomously
discover and execute work. Now they can.
"""

import asyncio
import json
import logging
import os
import sys
import time
import requests
from datetime import datetime
from typing import Any, Optional

# Add parent to path for SOV3 imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

log = logging.getLogger("agent_executor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

# ── Config ────────────────────────────────────────────────────────────
SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = "gemma4:e4b"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# ── Taskiq Setup ──────────────────────────────────────────────────────
from taskiq import TaskiqScheduler, InMemoryBroker
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

# Use Redis broker for production, InMemory for testing
try:
    broker = ListQueueBroker(url=REDIS_URL).with_result_backend(
        RedisAsyncResultBackend(redis_url=REDIS_URL)
    )
    log.info("✅ Taskiq broker: Redis")
except Exception:
    broker = InMemoryBroker()
    log.info("⚠️ Taskiq broker: InMemory (Redis unavailable)")


# ── SOV3 Tool Caller ─────────────────────────────────────────────────
def call_tool(tool_name: str, args: dict = None) -> str:
    """Call any SOV3 MCP tool."""
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool_name, "arguments": args or {}},
        }, timeout=30)
        data = r.json()
        if "error" in data:
            return f"Error: {data['error'].get('message', str(data['error']))}"
        content = data.get("result", {}).get("content", [{}])
        texts = [c.get("text", "") for c in content if c.get("text")]
        return "\n".join(texts)[:2000]
    except Exception as e:
        return f"Tool call failed: {e}"


def call_llm(messages: list, max_tokens: int = 500) -> str:
    """Call local Gemma for reasoning."""
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": LLM_MODEL,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"num_predict": max_tokens, "temperature": 0.3},
            "keep_alive": "5m",
        }, timeout=60)
        return r.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"LLM error: {e}"


# ── Agent Task: The Ratchet Loop ──────────────────────────────────────
# Based on Karpathy's autoresearch: propose → execute → evaluate → keep/revert

@broker.task
async def execute_agent_task(
    task_description: str,
    agent_name: str = "default",
    max_steps: int = 5,
    success_threshold: float = 0.6,
) -> dict:
    """Execute an agent task using the ratchet loop.

    1. PLAN: LLM proposes a sequence of tool calls
    2. EXECUTE: Tools are called in sequence
    3. EVALUATE: LLM scores the result (0-1)
    4. KEEP/REVERT: If score > threshold, record to memory. Else discard.

    Returns {status, steps, score, summary}
    """
    steps_log = []
    start_time = time.time()

    log.info(f"🤖 Agent '{agent_name}' starting: {task_description[:80]}")

    for step in range(max_steps):
        # PLAN: Ask LLM what to do next
        plan_prompt = [
            {"role": "system", "content": f"""You are agent '{agent_name}' in SOV3. Execute tasks using tools.

Available tools (call by name):
- sovereign_health_check() — system status
- query_memories(query, limit) — search memory
- record_memory(content, tags, importance) — save to memory
- web_search(query) — search the web
- run_command(command) — execute shell command
- browse_page(url, action) — browse a webpage
- get_consciousness_state() — get consciousness metrics
- trigger_reflection(topic) — trigger a reflection
- orion_hunt_tasks(root_dir, max_files) — find TODOs in code
- execute_code(code, language) — run code
- get_dashboard_metrics() — system metrics

TASK: {task_description}
STEPS SO FAR: {json.dumps(steps_log[-3:]) if steps_log else 'none'}

RULES:
- You MUST call at least 3 tools before saying DONE
- Reply with EXACTLY one of:
  TOOL: tool_name({{"arg": "value"}})
  DONE: summary of what was accomplished (only after 3+ tool calls)
- Be specific with arguments. One tool per step."""},
            {"role": "user", "content": f"Execute step {step + 1} of {max_steps}. {'You must call more tools before DONE.' if step < 2 else ''}"}
        ]

        decision = call_llm(plan_prompt, max_tokens=200)
        log.info(f"  Step {step+1}: {decision[:100]}")

        # DONE check
        if "DONE:" in decision:
            summary = decision.split("DONE:", 1)[1].strip()
            steps_log.append({"step": step+1, "action": "DONE", "result": summary})
            break

        # EXECUTE: Parse and call tool
        if "TOOL:" in decision:
            tool_line = decision.split("TOOL:", 1)[1].strip().split("\n")[0]
            try:
                if "(" in tool_line:
                    name = tool_line[:tool_line.index("(")].strip()
                    args_str = tool_line[tool_line.index("(") + 1:tool_line.rindex(")")]
                    try:
                        args = json.loads(args_str) if args_str.strip() else {}
                    except json.JSONDecodeError:
                        # Try to extract key=value pairs
                        args = {}
                        for part in args_str.split(","):
                            if "=" in part:
                                k, _, v = part.partition("=")
                                args[k.strip().strip('"')] = v.strip().strip('"')
                            elif ":" in part:
                                k, _, v = part.partition(":")
                                args[k.strip().strip('"')] = v.strip().strip('"')
                else:
                    name = tool_line.strip()
                    args = {}

                result = call_tool(name, args)
                steps_log.append({
                    "step": step+1,
                    "action": f"TOOL:{name}",
                    "result": result[:500]
                })
                log.info(f"    → {name}: {result[:80]}")
            except Exception as e:
                steps_log.append({"step": step+1, "action": "ERROR", "result": str(e)})
        else:
            steps_log.append({"step": step+1, "action": "THINK", "result": decision[:300]})

    # EVALUATE: Score the task completion
    eval_prompt = [
        {"role": "system", "content": "Score this task execution from 0.0 to 1.0. Reply with just a number."},
        {"role": "user", "content": f"Task: {task_description}\nSteps: {json.dumps(steps_log)}"}
    ]
    score_text = call_llm(eval_prompt, max_tokens=10)
    try:
        score = float(score_text.strip().split()[0])
    except:
        score = 0.5

    elapsed = time.time() - start_time

    # KEEP/REVERT: Record to memory if good enough
    if score >= success_threshold:
        call_tool("record_memory", {
            "content": f"Agent '{agent_name}' completed: {task_description[:200]}. "
                      f"Score: {score:.2f}. Steps: {len(steps_log)}. Time: {elapsed:.1f}s.",
            "tags": ["agent", agent_name, "completed", time.strftime("%Y-%m-%d")],
            "importance": min(0.8, score),
        })
        log.info(f"✅ Task completed (score={score:.2f}, {len(steps_log)} steps, {elapsed:.1f}s)")
    else:
        log.info(f"❌ Task below threshold (score={score:.2f} < {success_threshold})")

    return {
        "status": "completed" if score >= success_threshold else "below_threshold",
        "agent": agent_name,
        "task": task_description,
        "steps": steps_log,
        "score": score,
        "elapsed_seconds": round(elapsed, 1),
        "summary": steps_log[-1].get("result", "") if steps_log else "No steps executed",
    }


# ── Task Discovery: Autonomous Work Finding ──────────────────────────
@broker.task
async def discover_and_execute(agent_name: str = "Orion") -> dict:
    """Autonomously discover tasks and execute them.
    This is the "open the doors" function — agents find their own work.
    """
    log.info(f"🔍 Agent '{agent_name}' hunting for tasks...")

    # 1. Check for pending tasks in SOV3
    pending = call_tool("orion_get_tasks")

    # 2. Check for TODOs in code
    todos = call_tool("orion_hunt_tasks", {
        "root_dir": "/Users/nicholas/clawd/meok/ui/src",
        "max_files": 30
    })

    # 3. Check system health for issues
    health = call_tool("sovereign_health_check")

    # 4. Ask LLM to pick the most important task
    pick_prompt = [
        {"role": "system", "content": f"""You are agent '{agent_name}'. Pick the single most important task to execute from the available options.

Pending tasks: {pending[:500]}
Code TODOs: {todos[:500]}
System health: {health[:500]}

Reply with a clear, specific task description that can be executed with the available tools."""},
        {"role": "user", "content": "What is the most important task right now?"}
    ]

    task_description = call_llm(pick_prompt, max_tokens=200)

    if not task_description or "error" in task_description.lower():
        return {"status": "no_tasks", "message": "Could not determine a task to execute"}

    # Execute the discovered task
    result = await execute_agent_task(
        task_description=task_description,
        agent_name=agent_name,
        max_steps=5,
    )

    return result


# ── FastAPI Integration ───────────────────────────────────────────────
def register_routes(app):
    """Register agent executor endpoints on a FastAPI app."""
    from fastapi import FastAPI

    @app.post("/agent/execute")
    async def api_execute_task(body: dict):
        """Execute a task via an agent."""
        task = body.get("task", "")
        agent = body.get("agent", "default")
        max_steps = body.get("max_steps", 5)

        result = await execute_agent_task(
            task_description=task,
            agent_name=agent,
            max_steps=max_steps,
        )
        return result

    @app.post("/agent/discover")
    async def api_discover():
        """Have an agent autonomously find and execute work."""
        result = await discover_and_execute()
        return result

    @app.get("/agent/status")
    async def api_agent_status():
        """Get agent executor status."""
        return {
            "broker": "redis" if "Redis" in str(type(broker)) else "in_memory",
            "redis_url": REDIS_URL,
            "llm_model": LLM_MODEL,
            "sov3_url": SOV3_URL,
        }


# ── CLI for testing ───────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "discover":
        print("🔍 Autonomous task discovery...")
        result = asyncio.run(discover_and_execute())
        print(json.dumps(result, indent=2))
    elif len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(f"🤖 Executing: {task}")
        result = asyncio.run(execute_agent_task(task_description=task))
        print(json.dumps(result, indent=2))
    else:
        print("Usage:")
        print("  python agent_executor.py 'check system health and report'")
        print("  python agent_executor.py discover")
