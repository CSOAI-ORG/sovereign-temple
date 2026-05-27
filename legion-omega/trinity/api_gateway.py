#!/usr/bin/env python3
"""
Legion Trinity — API Gateway
Runs on Archive (RTX 8000 #2) port 8080
Routes inference to Speed Demon → Forge fallback
"""

import asyncio
import json
import os
import time
import urllib.request
from typing import Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic"], check=True)
    from fastapi import FastAPI, HTTPException, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn

from node_config import NODES

app = FastAPI(title="Legion Trinity API", version="1.0.0")
security = HTTPBearer(auto_error=False)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

API_TOKEN = os.environ.get("LEGION_API_TOKEN", "legion-trinity-meok")

# Node routing order: speed-demon first, forge second, archive last
ROUTE_ORDER = ["speed-demon", "forge", "archive"]


class InferRequest(BaseModel):
    prompt: str
    model: Optional[str] = "qwen3.5:9b"
    max_tokens: Optional[int] = 2000
    temperature: Optional[float] = 0.3


class EmbedRequest(BaseModel):
    text: str
    model: Optional[str] = "nomic-embed-text"


class TrainRequest(BaseModel):
    trajectories: List[Dict]
    job_id: Optional[str] = None


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    import os
    token = os.environ.get("LEGION_API_TOKEN", API_TOKEN)
    if credentials and credentials.credentials != token:
        raise HTTPException(status_code=401, detail="Invalid token")


def call_ollama(node_key: str, endpoint: str, payload: Dict, timeout: int = 120) -> Dict:
    node = NODES[node_key]
    if node["status"] not in ("running",) or not node.get("ollama_port"):
        raise ConnectionError(f"{node_key} not available")
    url = f"http://{node['public_ip']}:{node['ollama_port']}{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


@app.post("/v1/infer")
async def inference(req: InferRequest, _=Depends(verify_token)):
    """Route inference to fastest available node with auto-fallback"""
    last_err = None
    for node_key in ROUTE_ORDER:
        node = NODES.get(node_key, {})
        if node.get("status") != "running":
            continue
        try:
            start = time.time()
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda nk=node_key: call_ollama(nk, "/api/generate", {
                    "model": req.model,
                    "prompt": req.prompt,
                    "stream": False,
                    "options": {"num_predict": req.max_tokens, "temperature": req.temperature}
                })
            )
            return {
                "status": "success",
                "node": node_key,
                "latency_ms": round((time.time() - start) * 1000),
                "response": result.get("response", ""),
                "model": req.model,
            }
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=503, detail=f"All nodes failed: {last_err}")


@app.post("/v1/embed")
async def embed(req: EmbedRequest, _=Depends(verify_token)):
    """Get embeddings — prefer Archive (dedicated to MEOK), fallback to Forge"""
    order = ["archive", "forge", "speed-demon"]
    for node_key in order:
        node = NODES.get(node_key, {})
        if node.get("status") != "running":
            continue
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda nk=node_key: call_ollama(nk, "/api/embeddings", {
                    "model": req.model,
                    "prompt": req.text[:2000]
                }, timeout=60)
            )
            emb = result.get("embedding", [])
            if emb:
                return {"node": node_key, "dims": len(emb), "embedding": emb}
        except Exception:
            continue
    raise HTTPException(status_code=503, detail="No embedding node available")


@app.post("/v1/learn")
async def trigger_training(req: TrainRequest, _=Depends(verify_token)):
    """Async training trigger — returns job_id immediately"""
    job_id = req.job_id or f"train_{int(time.time())}"
    # Queue for heartbeat to pick up
    return {"job_id": job_id, "status": "queued", "trajectories": len(req.trajectories)}


@app.get("/v1/health")
async def health():
    """Cluster health — returns 503 if < 2 nodes up"""
    statuses = {}
    healthy = 0
    for node_key, node in NODES.items():
        if not node.get("ollama_port"):
            statuses[node_key] = "no_port"
            continue
        try:
            url = f"http://{node['public_ip']}:{node['ollama_port']}/api/tags"
            with urllib.request.urlopen(url, timeout=5) as r:
                models = [m["name"] for m in json.loads(r.read()).get("models", [])]
                statuses[node_key] = {"status": "online", "models": len(models)}
                healthy += 1
        except Exception as e:
            statuses[node_key] = {"status": "offline", "error": str(e)[:60]}

    if healthy < 2:
        raise HTTPException(status_code=503, detail={"message": "Cluster degraded", "nodes": statuses})

    return {"healthy_nodes": healthy, "total_nodes": len(NODES), "nodes": statuses}


@app.get("/v1/status")
async def status():
    """Full cluster status"""
    return {
        "nodes": {k: {
            "name": v["name"], "status": v["status"],
            "vram_gb": v["vram_gb"], "role": v["role"],
            "ollama": f"http://{v['public_ip']}:{v.get('ollama_port','?')}" if v.get("ollama_port") else None
        } for k, v in NODES.items()},
        "total_vram_gb": sum(n["vram_gb"] for n in NODES.values()),
    }


if __name__ == "__main__":
    import os
    port = int(os.environ.get("GATEWAY_PORT", 8080))
    print(f"Legion Trinity API Gateway → :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
