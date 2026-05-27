#!/usr/bin/env python3
"""
Legion OS — War Room UI
FastAPI + WebSocket + Three.js 3D topology
Run: uvicorn ui.legion_os:app --host 0.0.0.0 --port 8080
"""

import asyncio
import json
import time
import urllib.request
from pathlib import Path
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from characters.council import Council

app = FastAPI(title="Legion OS", version="2.0")
council = Council()

# ─── WebSocket Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.connections -= dead

manager = ConnectionManager()

# ─── Node Health Check ────────────────────────────────────────────────────────

def ping_ollama(host: str, port: int, timeout: int = 3) -> bool:
    if port == 0:
        return False
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False

def get_topology():
    char_map = {
        "archimedes": {"x": 0,   "y": 2,   "z": 0},
        "valkyrie":   {"x": -3,  "y": 0,   "z": 2},
        "mercury":    {"x": 3,   "y": 0,   "z": 2},
        "hephaestus": {"x": -2,  "y": -1,  "z": -1},
        "chronus":    {"x": 0,   "y": -2,  "z": -2},
        "argus":      {"x": 2,   "y": -1,  "z": -1},
        "odyssey":    {"x": 0,   "y": 1,   "z": -3},
        "hermes":     {"x": 0,   "y": -1,  "z": 3},
    }
    nodes = []
    for cid, char in council.members.items():
        if cid == "jarvis":
            continue
        online = ping_ollama(char.host, char.ollama_port) or char.host == "localhost"
        nodes.append({
            "id": cid,
            "name": char.name,
            "color": int(char.color.lstrip("#"), 16),
            "emoji": char.emoji,
            "online": online,
            "vram": char.vram_gb,
            **char_map.get(cid, {"x": 0, "y": 0, "z": 0}),
        })
    return nodes

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    with open(Path(__file__).parent / "legion_os.html") as f:
        return f.read()

@app.get("/api/status")
async def status():
    return {"council": council.status(), "time": time.time()}

@app.get("/api/leaderboard")
async def leaderboard():
    return council.leaderboard()

@app.get("/api/topology")
async def topology():
    return get_topology()

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send welcome
    await websocket.send_json({
        "type": "init",
        "council": council.status(),
        "topology": get_topology(),
        "message": "Legion OS v2.0 — Council assembled."
    })
    try:
        while True:
            data = await websocket.receive_json()
            await handle_command(data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def handle_command(data: dict, ws: WebSocket):
    cmd = data.get("type")

    if cmd == "command":
        target = data.get("target", "jarvis")
        message = data.get("message", "")
        char = council.members.get(target)
        if char:
            response = char.respond(message)
            await ws.send_json({
                "type": "chat",
                "character": target,
                "name": char.name,
                "emoji": char.emoji,
                "color": char.color,
                "message": response,
            })
            # Award XP for interaction
            level_up = char.stats.add_xp(10)
            if level_up:
                await manager.broadcast({
                    "type": "achievement",
                    "title": f"{char.name} Level Up!",
                    "description": f"{char.emoji} {char.name} reached {level_up}",
                })
            char.save()

    elif cmd == "meeting":
        topic = data.get("topic", "No topic")
        responses = council.meeting(topic)
        for r in responses:
            await manager.broadcast({"type": "chat", **r})
            await asyncio.sleep(0.4)

    elif cmd == "assign":
        char_id = data.get("character", "odyssey")
        task = data.get("task", "")
        result = council.assign_task(char_id, task)
        await manager.broadcast({"type": "task_assigned", "result": result})

    elif cmd == "complete":
        char_id = data.get("character")
        task = data.get("task", "")
        char = council.members.get(char_id)
        if char:
            result = char.complete_task(task, xp=100)
            await manager.broadcast({"type": "task_complete", **result})

    elif cmd == "topology_refresh":
        await ws.send_json({"type": "topology", "nodes": get_topology()})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
