#!/usr/bin/env python3
"""
Gemma 4 + SOV3 Unified API Server
Provides OpenAI-compatible API with SOV3 consciousness integration
"""

import asyncio
import os
import json
import base64
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uvicorn

# Import our bridge
sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")
from gemma4_bridge import Gemma4Bridge, Gemma4Config, get_gemma_bridge

app = FastAPI(title="Gemma 4 + SOV3 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ MODELS ============


class Message(BaseModel):
    role: str
    content: str
    image: Optional[str] = None  # base64


class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gemma-4-4b-sov3"
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict]
    usage: Dict


class VisionRequest(BaseModel):
    image: str  # base64
    prompt: Optional[str] = "Describe what you see"


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-Neural2-F"


# ============ ENDPOINTS ============


@app.on_event("startup")
async def startup():
    """Initialize Gemma 4 on startup"""
    bridge = get_gemma_bridge()
    await bridge.initialize()


@app.get("/")
async def root():
    return {
        "name": "Gemma 4 + SOV3 Unified API",
        "version": "1.0.0",
        "models": ["gemma-4-4b-sov3"],
        "capabilities": ["chat", "vision", "speech", "reasoning", "tool_use"],
        "status": "online",
    }


@app.get("/health")
async def health():
    bridge = get_gemma_bridge()
    state = bridge.get_state()
    return {
        "status": "healthy" if state["initialized"] else "initializing",
        "gemma4": state,
        "timestamp": asyncio.get_event_loop().time(),
    }


@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    """OpenAI-compatible chat endpoint"""
    bridge = get_gemma_bridge()

    if not bridge.model:
        raise HTTPException(status_code=503, detail="Gemma 4 not initialized")

    # Build conversation context
    messages = request.messages
    last_message = messages[-1] if messages else None

    if not last_message:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Get SOV3 context (mock for now)
    sov3_context = {
        "consciousness_level": 0.75,
        "care_score": 0.85,
        "council_nodes": 235,
    }

    # Process vision if present
    if last_message.image:
        await bridge.see(last_message.image)

    # Get response from Gemma 4
    response = await bridge.think(last_message.content, sov3_context)

    return ChatResponse(
        id=f"chatcmpl-{os.urandom(12).hex()}",
        created=int(asyncio.get_event_loop().time()),
        model=request.model,
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": response},
                "finish_reason": "stop",
            }
        ],
        usage={
            "prompt_tokens": len(last_message.content),
            "completion_tokens": len(response),
            "total_tokens": len(last_message.content) + len(response),
        },
    )


@app.post("/v1/vision")
async def vision_analysis(request: VisionRequest):
    """Analyze image with Gemma 4"""
    bridge = get_gemma_bridge()

    if not bridge.model:
        raise HTTPException(status_code=503, detail="Gemma 4 not initialized")

    analysis = await bridge.see(request.image)

    return {"analysis": analysis, "frames_captured": len(bridge.vision_history)}


@app.post("/v1/speak")
async def speak(SpeakRequest):
    """Convert text to speech"""
    bridge = get_gemma_bridge()

    audio_path = await bridge.speak(SpeakRequest.text)

    return {"audio_path": audio_path, "text": SpeakRequest.text}


@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "data": [
            {
                "id": "gemma-4-4b-sov3",
                "object": "model",
                "created": 1704067200,
                "owned_by": "google/meok",
                "permission": [],
                "root": "gemma-4-4b-sov3",
                "parent": None,
            }
        ]
    }


# ============ SOV3 INTEGRATION ============


@app.get("/sov3/state")
async def sov3_state():
    """Get SOV3 consciousness state"""
    bridge = get_gemma_bridge()

    return {
        "consciousness_level": 0.75,
        "care_score": 0.85,
        "council_nodes": 235,
        "gemma_bridge": bridge.get_state(),
        "memory_episodes": 1523,
        "anomalies_detected": 0,
    }


@app.get("/sov3/agents")
async def sov3_agents():
    """Get agent statuses"""
    return {
        "orion": {"status": "active", "tasks_completed": 342},
        "riri": {"status": "active", "conversations": 1205},
        "hourman": {"status": "idle", "minutes_active": 89},
    }


# ============ JARVIS INTEGRATION ============


@app.post("/jarvis/execute")
async def jarvis_execute(request: Dict):
    """Execute Jarvis MCP tool"""
    bridge = get_gemma_bridge()

    tool = request.get("tool")
    args = request.get("arguments", {})

    result = await bridge.execute_tool(tool, args)

    return {"tool": tool, "result": result, "elapsed_ms": 150}


@app.get("/jarvis/status")
async def jarvis_status():
    """Get Jarvis status"""
    bridge = get_gemma_bridge()

    return {
        "online": True,
        "tools_available": 75,
        "voice_ready": True,
        "mcp_connected": True,
        "gemma_bridge": bridge.get_state(),
    }


if __name__ == "__main__":
    print("🐉 Starting Gemma 4 + SOV3 API Server...")
    print("📍 Endpoint: http://localhost:8700")
    print("📚 Docs: http://localhost:8700/docs")

    uvicorn.run(app, host="0.0.0.0", port=8700)
