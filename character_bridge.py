"""
Character Bridge — WebSocket bridge between SOV3 and the MEOK Desktop Character
==================================================================================
Provides real-time character control: speech, emotions, lip-sync, persona switching.

WebSocket endpoint: ws://localhost:3101/ws/character

Messages TO frontend:
  { "type": "speak", "text": "Hello Sir", "emotion": "neutral", "persona": "jarvis" }
  { "type": "emotion", "emotion": "excited", "intensity": 0.8 }
  { "type": "persona", "persona": "sophie" }
  { "type": "listening", "active": true }
  { "type": "thinking", "active": true }
  { "type": "tool_use", "tool": "web_search", "status": "executing" }

Messages FROM frontend:
  { "type": "user_input", "text": "Hello Jarvis" }
  { "type": "wake_word", "word": "hey jarvis" }
  { "type": "click", "action": "toggle_panel" }
"""

import asyncio
import json
import logging
import time
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger("character_bridge")

# Connected character clients
_clients: Set[WebSocket] = set()
_current_state = {
    "persona": "jarvis",
    "emotion": "neutral",
    "speaking": False,
    "listening": False,
    "thinking": False,
    "last_text": "",
    "consciousness_level": 0.625,
}


async def broadcast(message: dict):
    """Send message to all connected character clients."""
    dead = set()
    for ws in _clients:
        try:
            await ws.send_json(message)
        except:
            dead.add(ws)
    _clients -= dead


async def notify_speak(text: str, emotion: str = "neutral", persona: str = None):
    """Notify character to speak with lip-sync."""
    _current_state["speaking"] = True
    _current_state["last_text"] = text
    if emotion:
        _current_state["emotion"] = emotion
    if persona:
        _current_state["persona"] = persona
    await broadcast({
        "type": "speak",
        "text": text,
        "emotion": emotion,
        "persona": persona or _current_state["persona"],
        "timestamp": time.time(),
    })


async def notify_emotion(emotion: str, intensity: float = 0.7):
    """Update character emotion."""
    _current_state["emotion"] = emotion
    await broadcast({
        "type": "emotion",
        "emotion": emotion,
        "intensity": intensity,
    })


async def notify_listening(active: bool):
    """Show listening state on character."""
    _current_state["listening"] = active
    _current_state["speaking"] = False
    await broadcast({"type": "listening", "active": active})


async def notify_thinking(active: bool):
    """Show thinking animation on character."""
    _current_state["thinking"] = active
    await broadcast({"type": "thinking", "active": active})


async def notify_tool_use(tool: str, status: str = "executing"):
    """Show tool execution on character UI."""
    await broadcast({"type": "tool_use", "tool": tool, "status": status})


async def switch_persona(persona: str):
    """Switch between Jarvis and Sophie."""
    _current_state["persona"] = persona
    await broadcast({"type": "persona", "persona": persona})


def _generate_response(text: str) -> str:
    """Generate AI response (runs in thread pool to avoid blocking event loop)."""
    import requests
    try:
        r = requests.post("http://localhost:11434/api/chat", json={
            "model": "jarvis",
            "messages": [{"role": "user", "content": text}],
            "stream": False, "think": False,
            "options": {"num_predict": 200, "temperature": 0.7, "num_ctx": 4096},
            "keep_alive": "10m",
        }, timeout=30)
        answer = r.json().get("message", {}).get("content", "")
        if not answer:
            answer = r.json().get("message", {}).get("thinking", "")
        return answer or "I'm having trouble processing that, Sir."
    except Exception as e:
        log.error(f"Character response error: {e}")
        return f"Connection issue, Sir. {e}"


def register_routes(app):
    """Register WebSocket endpoint on FastAPI app."""

    @app.websocket("/ws/character")
    async def character_websocket(websocket: WebSocket):
        await websocket.accept()
        _clients.add(websocket)
        log.info(f"🎭 Character client connected ({len(_clients)} total)")

        # Send current state
        await websocket.send_json({"type": "state", **_current_state})

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "user_input":
                    text = data.get("text", "")
                    log.info(f"🎭 Character input: {text}")
                    try:
                        await websocket.send_json({"type": "thinking", "active": True})

                        import asyncio
                        loop = asyncio.get_event_loop()
                        answer = await loop.run_in_executor(None, _generate_response, text)

                        await websocket.send_json({"type": "thinking", "active": False})
                        await websocket.send_json({
                            "type": "speak",
                            "text": answer,
                            "emotion": "neutral",
                            "persona": _current_state["persona"],
                        })
                        log.info(f"🎭 Response sent: {answer[:60]}...")
                    except Exception as e:
                        log.error(f"🎭 Character response error: {e}")
                        try:
                            await websocket.send_json({
                                "type": "speak",
                                "text": f"Error generating response: {e}",
                                "emotion": "neutral",
                                "persona": "jarvis",
                            })
                        except:
                            pass

                elif msg_type == "wake_word":
                    log.info(f"🎭 Wake word detected: {data.get('word')}")

                elif msg_type == "click":
                    action = data.get("action", "")
                    log.info(f"🎭 Character click: {action}")

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            _clients.discard(websocket)
            log.info(f"🎭 Character client disconnected ({len(_clients)} total)")


def get_state():
    """Get current character state."""
    return _current_state.copy()
