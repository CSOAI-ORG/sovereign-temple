#!/usr/bin/env python3
"""
M2 Air 8GB — Claude Code Sidekick
Runs 3B model locally for instant code completion
Uses Ollama (no transformers needed) - simpler setup
Install: ollama pull phi3 (3.8B fits in 8GB)
"""

import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path
from datetime import datetime

LOCAL_OLLAMA = "http://localhost:11434"
M4_REDIS_HOST = os.environ.get("M4_REDIS_HOST", "localhost")

LOG_PATH = Path.home() / "clawd" / "memory" / "m2_sidekick.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][M2] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def call_ollama(prompt: str, model: str = "phi3", max_tokens: int = 512) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.1}
    }).encode()
    try:
        req = urllib.request.Request(
            f"{LOCAL_OLLAMA}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def get_models() -> list:
    try:
        with urllib.request.urlopen(f"{LOCAL_OLLAMA}/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def code_complete(code: str, language: str = "python") -> str:
    return call_ollama(
        f"Complete this {language} code. Return ONLY the completion, no explanation:\n{code}",
        model="phi3", max_tokens=256
    )


def explain_error(error: str, code: str = "") -> str:
    prompt = f"Explain this error briefly and suggest a fix:\nError: {error}"
    if code:
        prompt += f"\nCode: {code[:500]}"
    return call_ollama(prompt, model="phi3", max_tokens=300)


def quick_review(code: str) -> str:
    return call_ollama(
        f"Find obvious bugs/security issues in 3 bullet points:\n{code[:800]}",
        model="phi3", max_tokens=200
    )


async def serve():
    """Simple HTTP server for M4 to call"""
    import http.server
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))

            task_type = body.get("type", "complete")
            result = ""

            if task_type == "code_complete":
                result = code_complete(body.get("code", ""), body.get("language", "python"))
            elif task_type == "explain_error":
                result = explain_error(body.get("error", ""), body.get("code", ""))
            elif task_type == "review":
                result = quick_review(body.get("code", ""))
            else:
                result = call_ollama(body.get("prompt", ""), max_tokens=512)

            response = json.dumps({"result": result, "node": "m2-sidekick"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            pass  # Suppress default logs

    port = int(os.environ.get("M2_PORT", 8080))
    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    log(f"M2 Sidekick serving on :{port}")
    log(f"Models: {get_models()}")
    server.serve_forever()


if __name__ == "__main__":
    asyncio.run(serve())
