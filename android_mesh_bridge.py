#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ANDROID MESH BRIDGE — Bidirectional sync between Android devices and        ║
║  the Mac Mesh (M2 + M4 + Vast).                                              ║
║                                                                              ║
║  Features:                                                                   ║
║    • WebSocket relay for real-time chat from Android → Mesh                  ║
║    • Push notification proxy (FCM) for mesh alerts on Android                ║
║    • Voice command endpoint optimized for Android SpeechRecognizer           ║
║    • Battery-aware routing (offload to M4 when Android battery < 20%)        ║
║    • Offline queue: store requests when disconnected, sync on reconnect      ║
║                                                                              ║
║  Architecture:                                                               ║
║    Android App ←──WebSocket──→ android_mesh_bridge.py ←──HTTP──→ Mesh      ║
║                        ↓                                                     ║
║                   FCM Push (alerts, completion notifications)                ║
║                                                                              ║
║  Endpoints:                                                                  ║
║    WS   /ws/android          ← Bidirectional WebSocket                       ║
║    POST /v1/android/chat     ← REST fallback for chat                        ║
║    POST /v1/android/voice    ← Speech-to-text + intent routing               ║
║    POST /v1/android/notify   ← Register FCM token                            ║
║    GET  /v1/android/status   ← Battery, connectivity, queue status           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

MESH_ORCHESTRATOR = os.environ.get("MESH_ORCHESTRATOR", "http://localhost:3202")
ANDROID_BRIDGE_PORT = int(os.environ.get("ANDROID_BRIDGE_PORT", 3203))
FCM_SERVER_KEY = os.environ.get("FCM_SERVER_KEY", "")  # Firebase Cloud Messaging

# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class AndroidChatRequest(BaseModel):
    message: str
    device_id: str = Field(..., description="Unique Android device ID")
    battery_pct: float = Field(default=100.0, ge=0, le=100)
    network_type: str = Field(default="wifi", pattern="^(wifi|5g|4g|3g|offline)$")
    use_mesh: bool = Field(default=True, description="Route through mesh vs on-device")
    stream: bool = False


class AndroidVoiceRequest(BaseModel):
    transcript: str
    device_id: str
    battery_pct: float = 100.0
    confidence: float = Field(default=1.0, ge=0, le=1)


class FCMRegisterRequest(BaseModel):
    device_id: str
    fcm_token: str
    device_name: Optional[str] = None


class DeviceState(BaseModel):
    device_id: str
    fcm_token: Optional[str] = None
    device_name: Optional[str] = None
    last_seen: float = 0.0
    battery_pct: float = 100.0
    network_type: str = "wifi"
    connected: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# Connection Manager
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections from Android devices."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.device_states: Dict[str, DeviceState] = {}
        self._offline_queue: Dict[str, List[Dict]] = {}  # device_id → queued messages

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        if device_id in self.device_states:
            self.device_states[device_id].connected = True
            self.device_states[device_id].last_seen = time.time()
        else:
            self.device_states[device_id] = DeviceState(
                device_id=device_id, connected=True, last_seen=time.time()
            )
        print(f"[ANDROID] Device {device_id} connected. Active: {len(self.active_connections)}")

        # Send any queued messages
        if device_id in self._offline_queue:
            queued = self._offline_queue.pop(device_id, [])
            for msg in queued:
                await websocket.send_json({"type": "queued", "data": msg})

    def disconnect(self, device_id: str):
        self.active_connections.pop(device_id, None)
        if device_id in self.device_states:
            self.device_states[device_id].connected = False
        print(f"[ANDROID] Device {device_id} disconnected. Active: {len(self.active_connections)}")

    async def send_personal_message(self, device_id: str, message: dict):
        if device_id in self.active_connections:
            await self.active_connections[device_id].send_json(message)
            return True
        # Queue for later
        self._offline_queue.setdefault(device_id, []).append(message)
        return False

    async def broadcast(self, message: dict):
        disconnected = []
        for device_id, ws in self.active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(device_id)
        for did in disconnected:
            self.disconnect(did)

    def get_stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "registered_devices": len(self.device_states),
            "queued_messages": sum(len(q) for q in self._offline_queue.values()),
            "devices": {
                did: {
                    "connected": ds.connected,
                    "battery": ds.battery_pct,
                    "network": ds.network_type,
                    "last_seen": datetime.fromtimestamp(ds.last_seen).isoformat(),
                }
                for did, ds in self.device_states.items()
            },
        }


manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════════════════════
# Mesh Client
# ═══════════════════════════════════════════════════════════════════════════════

async def mesh_chat(message: str, use_speculative: bool = True, require_private: bool = False) -> dict:
    """Send chat to mesh orchestrator."""
    payload = {
        "message": message,
        "use_speculative": use_speculative,
        "require_private": require_private,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{MESH_ORCHESTRATOR}/v1/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


async def mesh_route_info(query: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{MESH_ORCHESTRATOR}/v1/route", params={"query": query})
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# FCM Notifications
# ═══════════════════════════════════════════════════════════════════════════════

async def send_fcm_notification(device_id: str, title: str, body: str, data: Optional[dict] = None):
    """Send push notification via Firebase Cloud Messaging."""
    if not FCM_SERVER_KEY:
        return False

    state = manager.device_states.get(device_id)
    if not state or not state.fcm_token:
        return False

    payload = {
        "to": state.fcm_token,
        "notification": {"title": title, "body": body},
        "data": data or {},
        "priority": "high",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                json=payload,
                headers={"Authorization": f"key={FCM_SERVER_KEY}", "Content-Type": "application/json"},
            )
            return resp.status_code == 200
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Android Mesh Bridge",
    description="Bidirectional bridge between Android devices and Mac Mesh",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
async def root():
    return {"service": "android_mesh_bridge", "version": "1.0.0", "mesh": MESH_ORCHESTRATOR}


@app.get("/stats")
async def stats():
    return manager.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Endpoint — Primary Android connection
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/android/{device_id}")
async def android_websocket(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            if msg_type == "chat":
                message = data.get("message", "")
                battery = data.get("battery_pct", 100.0)
                network = data.get("network_type", "wifi")

                # Update device state
                if device_id in manager.device_states:
                    manager.device_states[device_id].battery_pct = battery
                    manager.device_states[device_id].network_type = network

                # Battery-aware routing: if battery < 20%, force mesh (offload from phone)
                require_private = battery < 20.0

                try:
                    result = await mesh_chat(message, use_speculative=True, require_private=require_private)
                    await websocket.send_json({
                        "type": "response",
                        "text": result.get("text", ""),
                        "node": result.get("node", "unknown"),
                        "model": result.get("model", "unknown"),
                        "latency_ms": result.get("latency_ms", 0),
                        "speculative_used": result.get("speculative_used", False),
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif msg_type == "heartbeat":
                if device_id in manager.device_states:
                    manager.device_states[device_id].last_seen = time.time()
                    manager.device_states[device_id].battery_pct = data.get("battery_pct", 100.0)
                    manager.device_states[device_id].network_type = data.get("network_type", "wifi")
                await websocket.send_json({"type": "heartbeat_ack"})

            elif msg_type == "register":
                fcm_token = data.get("fcm_token")
                device_name = data.get("device_name")
                if device_id in manager.device_states:
                    manager.device_states[device_id].fcm_token = fcm_token
                    manager.device_states[device_id].device_name = device_name
                await websocket.send_json({"type": "registered"})

    except WebSocketDisconnect:
        manager.disconnect(device_id)


# ═══════════════════════════════════════════════════════════════════════════════
# REST Endpoints — Fallback for non-WebSocket clients
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/v1/android/chat")
async def android_chat(req: AndroidChatRequest):
    """REST chat endpoint for Android."""
    # Update device state
    if req.device_id not in manager.device_states:
        manager.device_states[req.device_id] = DeviceState(device_id=req.device_id)
    manager.device_states[req.device_id].battery_pct = req.battery_pct
    manager.device_states[req.device_id].network_type = req.network_type
    manager.device_states[req.device_id].last_seen = time.time()

    # Route to mesh
    require_private = req.battery_pct < 20.0 or req.network_type == "offline"

    try:
        result = await mesh_chat(req.message, use_speculative=req.use_mesh, require_private=require_private)
        return {
            "text": result.get("text", ""),
            "node": result.get("node", "unknown"),
            "model": result.get("model", "unknown"),
            "latency_ms": result.get("latency_ms", 0),
            "speculative_used": result.get("speculative_used", False),
            "battery_save_mode": require_private,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/v1/android/voice")
async def android_voice(req: AndroidVoiceRequest):
    """Voice command endpoint. Parses intent and routes appropriately."""
    transcript_lower = req.transcript.lower()

    # Intent parsing
    if any(w in transcript_lower for w in ["status", "how are you", "health"]):
        route_info = await mesh_route_info("status")
        return {
            "type": "status_report",
            "text": f"Mesh status: {route_info.get('mesh_status', 'unknown')}. Nodes: {', '.join(route_info.get('nodes', {}).keys())}",
        }

    if any(w in transcript_lower for w in ["cost", "money", "spent", "saved"]):
        return {
            "type": "cost_report",
            "text": "You're using the sovereign mesh. Costs are near-zero for local inference. Cloud fallback costs pennies.",
        }

    # Default: treat as chat
    return await android_chat(AndroidChatRequest(
        message=req.transcript,
        device_id=req.device_id,
        battery_pct=req.battery_pct,
    ))


@app.post("/v1/android/notify")
async def register_fcm(req: FCMRegisterRequest):
    """Register Android device for push notifications."""
    if req.device_id not in manager.device_states:
        manager.device_states[req.device_id] = DeviceState(device_id=req.device_id)
    manager.device_states[req.device_id].fcm_token = req.fcm_token
    manager.device_states[req.device_id].device_name = req.device_name
    manager.device_states[req.device_id].last_seen = time.time()

    # Send test notification
    await send_fcm_notification(
        req.device_id,
        "Mesh Connected",
        f"{req.device_name or req.device_id} is now linked to the sovereign mesh.",
        {"type": "connection_confirmed"},
    )

    return {"status": "registered", "device_id": req.device_id}


@app.get("/v1/android/status/{device_id}")
async def device_status(device_id: str):
    """Get status of a specific Android device."""
    state = manager.device_states.get(device_id)
    if not state:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "device_id": state.device_id,
        "connected": state.connected,
        "battery_pct": state.battery_pct,
        "network_type": state.network_type,
        "last_seen": datetime.fromtimestamp(state.last_seen).isoformat(),
        "queued_messages": len(manager._offline_queue.get(device_id, [])),
    }


@app.post("/v1/notify/mesh")
async def notify_all_devices(title: str, body: str):
    """Broadcast notification to all registered Android devices."""
    sent = 0
    for device_id in manager.device_states:
        success = await send_fcm_notification(device_id, title, body)
        if success:
            sent += 1
    return {"sent": sent, "total_devices": len(manager.device_states)}


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print(f"🤖 Android Mesh Bridge starting on port {ANDROID_BRIDGE_PORT}")
    print(f"   Mesh orchestrator: {MESH_ORCHESTRATOR}")
    uvicorn.run(app, host="0.0.0.0", port=ANDROID_BRIDGE_PORT, log_level="info")
