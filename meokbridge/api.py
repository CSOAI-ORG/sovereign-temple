#!/usr/bin/env python3
"""
MEOKBRIDGE API — FastAPI server for programmatic access
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import MeokBridge, Node, NodeType, NodeCapability, BridgeResult, NodeStatus
from .config import BridgeConfig


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    node_id: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    prefer_local: bool = False


class CouncilRequest(BaseModel):
    message: str
    node_ids: Optional[List[str]] = None
    verbose: bool = False


class NodeCreateRequest(BaseModel):
    id: str
    name: Optional[str] = None
    type: str
    url: str
    api_key: Optional[str] = None
    priority: int = 0
    tags: List[str] = Field(default_factory=list)


class NodeResponse(BaseModel):
    id: str
    name: str
    type: str
    url: str
    status: str
    models: List[str] = Field(default_factory=list)
    priority: int
    tags: List[str]
    latency_ms: float


# ═══════════════════════════════════════════════════════════════════════════════
# App Lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

bridge = MeokBridge()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load nodes from config
    config = BridgeConfig()
    for node in config.load_nodes():
        bridge.add_node(node)
    await bridge.start_health_loop(interval_sec=30)
    print(f"[MEOKBRIDGE API] Loaded {len(bridge.nodes)} nodes, health loop active")
    yield
    # Shutdown
    if bridge._health_task:
        bridge._health_task.cancel()


app = FastAPI(
    title="MEOKBRIDGE API",
    description="Universal connector for AI compute and services",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "service": "meokbridge",
        "version": "1.0.0",
        "nodes": len(bridge.nodes),
        "online": len(bridge.list_nodes(status=NodeStatus.ONLINE)),
    }


@app.get("/health")
async def health():
    """Overall bridge health."""
    online = bridge.list_nodes(status=NodeStatus.ONLINE)
    return {
        "status": "healthy" if len(online) > 0 else "degraded",
        "nodes_total": len(bridge.nodes),
        "nodes_online": len(online),
        "nodes": [{"id": n.id, "status": n.status.value, "latency_ms": n.latency_ms} for n in bridge.nodes.values()],
    }


@app.get("/nodes", response_model=List[NodeResponse])
async def list_nodes(type: Optional[str] = None, status: Optional[str] = None):
    """List all nodes."""
    node_type = NodeType(type) if type else None
    node_status = NodeStatus(status) if status else None
    nodes = bridge.list_nodes(node_type=node_type, status=node_status)
    return [
        NodeResponse(
            id=n.id,
            name=n.name,
            type=n.node_type.value,
            url=n.url,
            status=n.status.value,
            models=n.models,
            priority=n.priority,
            tags=n.tags,
            latency_ms=n.latency_ms,
        )
        for n in nodes
    ]


@app.post("/nodes")
async def create_node(req: NodeCreateRequest):
    """Add a new node."""
    node = Node(
        id=req.id,
        name=req.name or req.id,
        node_type=NodeType(req.type),
        url=req.url,
        api_key=req.api_key,
        priority=req.priority,
        tags=req.tags,
    )
    bridge.add_node(node)
    # Persist to config
    config = BridgeConfig()
    config.add_node(node)
    return {"status": "added", "node": node.to_dict()}


@app.delete("/nodes/{node_id}")
async def delete_node(node_id: str):
    """Remove a node."""
    if bridge.remove_node(node_id):
        return {"status": "removed", "id": node_id}
    raise HTTPException(status_code=404, detail="Node not found")


@app.post("/v1/chat")
async def chat(req: ChatRequest):
    """Chat through the bridge."""
    result = await bridge.chat(
        req.message,
        node_id=req.node_id,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        prefer_local=req.prefer_local,
    )
    return {
        "text": result.text,
        "node_id": result.node_id,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": result.cost_usd,
    }


@app.post("/v1/council")
async def council(req: CouncilRequest):
    """Council mode: multi-node consensus."""
    result = await bridge.council_chat(req.message, req.node_ids)
    return result


@app.post("/v1/embed")
async def embed(texts: List[str], node_id: Optional[str] = None):
    """Get embeddings."""
    embeddings = await bridge.embed(texts, node_id=node_id)
    return {"embeddings": embeddings, "count": len(embeddings)}


@app.post("/v1/health-check")
async def trigger_health_check():
    """Manually trigger health checks."""
    statuses = await bridge.health_check()
    return {"statuses": {k: v.value for k, v in statuses.items()}}


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Static Files
# ═══════════════════════════════════════════════════════════════════════════════
import os as _os
_app_dir = _os.path.dirname(_os.path.abspath(__file__))
_dashboard_dir = _os.path.join(_os.path.dirname(_app_dir), "dashboard")
app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("MEOKBRIDGE_PORT", 3205))
    uvicorn.run(app, host="0.0.0.0", port=port)
