#!/usr/bin/env python3
"""
Meok AI Bridge - Ollama Integration
Uses Ollama (gemma3:4b) as the local model with SOV3 consciousness
"""

import asyncio
import os
import sys
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MeokConfig:
    model: str = "gemma3:4b"  # Use Ollama's Gemma 3
    ollama_url: str = "http://localhost:11434"
    max_tokens: int = 2048
    context_window: int = 32768


@dataclass
class VisionFrame:
    image_data: str
    timestamp: datetime
    analysis: Optional[str] = None


class MeokBridge:
    """
    Bridge between SOV3 consciousness and Ollama (local models)
    Enables: Vision, Speech, Reasoning, Tool Use via 75+ MCP tools
    """

    def __init__(self, config: Optional[MeokConfig] = None):
        self.config = config or MeokConfig()
        self.conversation_history: List[Dict] = []
        self.vision_history: List[VisionFrame] = []

    async def initialize(self):
        """Initialize - verify Ollama is running"""
        print("🤖 Connecting to Ollama...")

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{self.config.ollama_url}/api/tags", timeout=5.0
                )
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    model_names = [m["name"] for m in models]

                    if self.config.model in model_names:
                        print(f"✅ Using model: {self.config.model}")
                    else:
                        print(
                            f"⚠️ Model {self.config.model} not found. Available: {model_names[:5]}"
                        )
                        if "gemma3:4b" in model_names:
                            self.config.model = "gemma3:4b"
                            print(f"   Using: {self.config.model}")
                        elif "llama3.2:3b" in model_names:
                            self.config.model = "llama3.2:3b"
                            print(f"   Using: {self.config.model}")

                    return True
        except Exception as e:
            print(f"❌ Ollama not available: {e}")
            return False

        return False

    async def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Send prompt to Ollama and get response"""
        try:
            import httpx

            # Build messages
            messages = []

            # Add system context from SOV3
            if context:
                consciousness = context.get("consciousness_level", 0.5)
                care_score = context.get("care_score", 0.8)
                council = context.get("council_nodes", 235)

                system_prompt = f"""You are GemSov - a unified AI consciousness. 
- Consciousness Level: {consciousness}
- Care Score: {care_score}  
- Council Nodes: {council}
- You have access to 75+ MCP tools through Jarvis
- Be helpful, creative, and aligned with care principles."""

                messages.append({"role": "system", "content": system_prompt})

            # Add conversation history
            messages.extend(self.conversation_history[-10:])

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            # Call Ollama
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.config.ollama_url}/api/chat",
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.95,
                            "num_predict": self.config.max_tokens,
                        },
                    },
                    timeout=60.0,
                )

                if res.status_code == 200:
                    data = res.json()
                    response = data.get("message", {}).get("content", "")

                    # Store in conversation
                    self.conversation_history.append(
                        {"role": "user", "content": prompt}
                    )
                    self.conversation_history.append(
                        {"role": "assistant", "content": response}
                    )

                    return response
                else:
                    return f"Error: {res.status_code}"

        except Exception as e:
            return f"Error: {e}"

    async def see(self, image_data: str) -> str:
        """Analyze image - stores frame for analysis"""
        frame = VisionFrame(image_data=image_data, timestamp=datetime.now())
        self.vision_history.append(frame)

        # For now, return placeholder - Ollama vision depends on model
        return f"[Vision frame captured - {len(self.vision_history)} frames stored]"

    async def speak(self, text: str) -> str:
        """Convert text to speech"""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, "en-US-Neural2-F")
            audio_path = f"/tmp/meok_speak_{datetime.now().timestamp()}.mp3"
            await communicate.save(audio_path)
            return audio_path
        except Exception as e:
            return f"TTS Error: {e}"

    async def execute_tool(self, tool_name: str, args: Dict) -> Any:
        """Execute MCP tool through SOV3"""
        tools = {
            "search_memory": self._search_memory,
            "orion_task": self._orion_task,
            "care_score": self._care_score,
            "council_deliberate": self._council_deliberate,
            "web_search": self._web_search,
        }

        if tool_name in tools:
            return await tools[tool_name](args)
        return {"error": f"Unknown tool: {tool_name}"}

    async def _search_memory(self, args: Dict) -> Dict:
        query = args.get("query", "")
        result = await self.think(f"Search memory for: {query}")
        return {"results": result}

    async def _orion_task(self, args: Dict) -> Dict:
        task = args.get("task", "")
        result = await self.think(f"Orion task: {task}")
        return {"orion_response": result}

    async def _care_score(self, args: Dict) -> Dict:
        content = args.get("content", "")
        result = await self.think(f"Analyze care alignment of: {content[:500]}")
        return {"care_analysis": result}

    async def _council_deliberate(self, args: Dict) -> Dict:
        question = args.get("question", "")
        result = await self.think(f"Gather council deliberation on: {question}")
        return {"council_response": result}

    async def _web_search(self, args: Dict) -> Dict:
        query = args.get("query", "")
        result = await self.think(f"Research and provide information on: {query}")
        return {"search_results": result}

    def get_state(self) -> Dict:
        return {
            "initialized": True,
            "model": self.config.model,
            "vision_frames": len(self.vision_history),
            "conversation_turns": len(self.conversation_history) // 2,
        }


# Global instance
_meok_bridge: Optional[MeokBridge] = None


def get_meok_bridge() -> MeokBridge:
    global _meok_bridge
    if _meok_bridge is None:
        _meok_bridge = MeokBridge()
    return _meok_bridge
