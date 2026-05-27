#!/usr/bin/env python3
"""
Legion Penta-Mesh GPU Agent
Runs on each GPU node — accepts tasks from Redis, executes locally
Usage: python gpu_agent.py <node_name>
node_name: speed-demon | forge | archive
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

NODE_NAME = sys.argv[1] if len(sys.argv) > 1 else "forge"

# Ollama is always localhost on each node
LOCAL_OLLAMA = "http://localhost:11434"

# Redis config — set password via env
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASS = os.environ.get("REDIS_PASS", "")

LOG_FILE = Path(f"/tmp/agent_{NODE_NAME}.log")


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][{NODE_NAME}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def call_ollama(prompt: str, model: str = "qwen3.5:9b", max_tokens: int = 2000) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3}
    }).encode()
    try:
        req = urllib.request.Request(
            f"{LOCAL_OLLAMA}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def get_embed(text: str) -> list:
    payload = json.dumps({"model": "nomic-embed-text", "prompt": text[:2000]}).encode()
    try:
        req = urllib.request.Request(
            f"{LOCAL_OLLAMA}/api/embeddings",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("embedding", [])
    except Exception:
        return []


def check_health() -> dict:
    try:
        with urllib.request.urlopen(f"{LOCAL_OLLAMA}/api/tags", timeout=5) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
            return {"status": "online", "models": models, "node": NODE_NAME}
    except Exception as e:
        return {"status": "offline", "error": str(e), "node": NODE_NAME}


def execute_task(task: dict) -> dict:
    task_type = task.get("type", "inference")
    payload = task.get("payload", {})

    if task_type == "inference":
        model = payload.get("model", "qwen3.5:9b")
        prompt = payload.get("prompt", "")
        result = call_ollama(prompt, model=model)
        return {"status": "success", "result": result, "node": NODE_NAME}

    elif task_type == "embed":
        text = payload.get("text", "")
        embedding = get_embed(text)
        return {"status": "success", "dims": len(embedding), "node": NODE_NAME,
                "embedding": embedding[:10]}  # truncate for logging

    elif task_type == "health":
        return check_health()

    elif task_type == "evoskill_train":
        # Queue training for later (heavy ops)
        skill_name = payload.get("skill", "unknown")
        log(f"Queued EvoSkill training: {skill_name}")
        return {"status": "queued", "skill": skill_name, "node": NODE_NAME}

    elif task_type == "mars_reflection":
        episodes = payload.get("episodes", [])
        prompt = f"MARS reflection on {len(episodes)} episodes: {json.dumps(episodes[:3])[:500]}"
        result = call_ollama(prompt, model="qwen3.5:9b", max_tokens=500)
        return {"status": "success", "reflection": result, "node": NODE_NAME}

    else:
        return {"status": "error", "error": f"Unknown task type: {task_type}", "node": NODE_NAME}


def get_redis():
    try:
        import redis
        kwargs = {"host": REDIS_HOST, "port": REDIS_PORT, "decode_responses": True}
        if REDIS_PASS:
            kwargs["password"] = REDIS_PASS
        r = redis.Redis(**kwargs)
        r.ping()
        return r
    except ImportError:
        return None
    except Exception:
        return None


def run_agent_no_redis():
    """Fallback: poll via API gateway health checks"""
    log("Redis not available — running in health-check mode")
    while True:
        health = check_health()
        log(f"Health: {health['status']} | Models: {len(health.get('models', []))}")
        time.sleep(60)


def run_agent():
    log(f"GPU Agent starting — node: {NODE_NAME}")
    log(f"Local Ollama: {LOCAL_OLLAMA}")

    health = check_health()
    log(f"Ollama status: {health['status']} | Models: {health.get('models', [])}")

    r = get_redis()
    if not r:
        log("No Redis — running standalone mode")
        run_agent_no_redis()
        return

    queue_key = f"tasks:{NODE_NAME}"
    results_key = f"results:{NODE_NAME}"
    log(f"Listening on Redis queue: {queue_key}")

    while True:
        try:
            # Block-pop with 30s timeout
            item = r.blpop(queue_key, timeout=30)
            if not item:
                # Heartbeat
                r.set(f"agent:{NODE_NAME}:alive", int(time.time()), ex=120)
                continue

            _, raw = item
            task = json.loads(raw)
            task_id = task.get("id", f"task_{int(time.time())}")
            log(f"Task {task_id}: {task.get('type', '?')}")

            result = execute_task(task)
            result["task_id"] = task_id
            result["timestamp"] = time.time()

            r.lpush(results_key, json.dumps(result))
            r.ltrim(results_key, 0, 999)  # Keep last 1000 results
            r.set(f"agent:{NODE_NAME}:alive", int(time.time()), ex=120)

            log(f"Done: {result.get('status', '?')}")

        except KeyboardInterrupt:
            log("Agent stopped")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_agent()
