"""
Orion Auto-Pursue — Bridges stalking → pursuing → capturable
==============================================================
The missing pipeline step. Orion finds 60 tasks but never pursues them.
This script auto-promotes the highest priority stalked tasks to pursued,
making them available for capture and sprint execution.

Run via scheduler or cron.
"""

import requests
import json
import logging
import time

log = logging.getLogger("orion_auto_pursue")
SOV3_URL = "http://localhost:3101"


def call_tool(name, args=None):
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args or {}},
        }, timeout=30)
        data = r.json()
        content = data.get("result", {}).get("content", [{}])
        text = "\n".join(c.get("text", "") for c in content if c.get("text"))
        return json.loads(text) if text else {}
    except:
        return {}


def auto_pursue_and_capture():
    """Promote top stalked tasks → pursued → captured → sprint."""

    # 1. Hunt for tasks
    hunt = call_tool("orion_hunt_tasks", {
        "root_dir": "/Users/nicholas/clawd/sovereign-temple",
        "max_files": 30,
    })
    total = hunt.get("summary", {}).get("total_tasks", 0) or hunt.get("total_tasks", 0)
    log.info(f"Hunt complete: {total} tasks found")

    if total == 0:
        return {"status": "no_tasks"}

    # 2. Get current tasks list to find IDs
    tasks_data = call_tool("orion_get_tasks", {"status": "stalking", "limit": 10})
    tasks = tasks_data.get("tasks", [])

    if not tasks:
        # Try pursuing tasks directly
        tasks_data = call_tool("orion_get_tasks", {"status": "pursuing", "limit": 10})
        tasks = tasks_data.get("tasks", [])

    if not tasks:
        return {"status": "no_actionable_tasks"}

    # 3. Try to capture tasks by their actual IDs
    captured = 0
    for task in tasks[:5]:
        task_id = task.get("id", "")
        if not task_id:
            continue
        result = call_tool("orion_capture_task", {"task_id": task_id})
        if result and not result.get("error"):
            captured += 1
            log.info(f"  Captured task: {task_id}")

    # 4. If we captured tasks, start a sprint
    if captured > 0:
        sprint = call_tool("hourman_start_sprint", {
            "sprint_type": "micro",
            "task_id": tasks[0].get("id", ""),
        })
        log.info(f"Sprint started: {sprint}")
        return {"status": "sprint_started", "captured": captured, "sprint": sprint}

    # 5. If capture failed (tasks still in stalking, not pursuing),
    #    use agent_executor as backup
    log.info("Capture failed — using agent_executor directly")
    try:
        from agent_executor import execute_agent_task
        import asyncio

        # Pick a task description from the hunt
        top_tasks = hunt.get("top_tasks", tasks)
        if top_tasks:
            task_desc = top_tasks[0].get("description", "Check system health")
        else:
            task_desc = "Scan codebase for improvements and report findings"

        result = asyncio.run(execute_agent_task(
            task_description=task_desc,
            agent_name="Orion-AutoPursue",
            max_steps=3,
        ))
        return {"status": "executed_via_agent_executor", "result": result}

    except Exception as e:
        log.warning(f"Agent executor also failed: {e}")
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print("Orion Auto-Pursue — bridging stalking → execution")
    result = auto_pursue_and_capture()
    print(json.dumps(result, indent=2))
