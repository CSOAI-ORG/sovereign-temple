#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    JARVIS ULTIMATE - SOV3 ORCHESTRATION                    ║
║                                                                              ║
║  The most advanced open-source AI orchestration system                      ║
║  Combines: SOV3 Consciousness + Multi-Brain AI + Voice + Vision            ║
║                                                                              ║
║  Models:                                                                     ║
║  • Nemotron-3-Super (NVIDIA) - Orchestrator, tool calling, 1M context      ║
║  • DeepSeek-V3 (671B) - Deep reasoning, strategy                          ║
║  • MiniMax-M2.5 - Code generation, technical tasks                         ║
║  • Qwen3-VL - Vision, visual understanding                                ║
║  • GPT-OSS (120B) - General purpose, research                            ║
║  • Qwen2.5-Coder - Code specialist                                        ║
║  • Kokoro-82M - TTS (voice synthesis)                                     ║
║  • Whisper - STT (speech to text)                                        ║
╚══════════════════════════════════════════════════════════════════════════════════╝

Run: python3 jarvis_ultimate.py
"""

import os
import sys
import json
import time
import asyncio
import logging
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("JARVIS-ULTIMATE")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


class AIProvider(Enum):
    OLLAMA_CLOUD = "ollama-cloud"
    OLLAMA_LOCAL = "ollama-local"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"


@dataclass
class AIModel:
    name: str
    provider: AIProvider
    context_window: int
    strengths: List[str]
    speed: str  # slow, medium, fast


# The most advanced models available
MODELS = {
    # Local models (fast, free)
    "jarvis": AIModel(
        name="jarvis:latest",
        provider=AIProvider.OLLAMA_LOCAL,
        context_window=128_000,
        strengths=["conversation", "general", "assistant"],
        speed="fast",
    ),
    "qwen2.5": AIModel(
        name="qwen2.5:7b",
        provider=AIProvider.OLLAMA_LOCAL,
        context_window=128_000,
        strengths=["general", "reasoning", "coding"],
        speed="fast",
    ),
    "llama3.1": AIModel(
        name="llama3.1:8b",
        provider=AIProvider.OLLAMA_LOCAL,
        context_window=128_000,
        strengths=["general", "reasoning", "conversation"],
        speed="medium",
    ),
    "gemma3": AIModel(
        name="gemma3:4b",
        provider=AIProvider.OLLAMA_LOCAL,
        context_window=32_000,
        strengths=["general", "lightweight"],
        speed="fast",
    ),
    "phi4": AIModel(
        name="phi4-mini:latest",
        provider=AIProvider.OLLAMA_LOCAL,
        context_window=32_000,
        strengths=["lightweight", "fast", "coding"],
        speed="fast",
    ),
    # Cloud models (via Ollama)
    "nemotron": AIModel(
        name="nemotron-3-super:cloud",
        provider=AIProvider.OLLAMA_CLOUD,
        context_window=1_000_000,
        strengths=["tool_calling", "reasoning", "planning", "memory"],
        speed="medium",
    ),
    # Tier 2: Deep Reasoning (671B parameters)
    "deepseek": AIModel(
        name="deepseek-v3.1:671b-cloud",
        provider=AIProvider.OLLAMA_CLOUD,
        context_window=200_000,
        strengths=["deep_reasoning", "strategy", "research", "coding"],
        speed="slow",
    ),
    # Tier 3: Code Generation
    "minimax": AIModel(
        name="minimax-m2.5:cloud",
        provider=AIProvider.OLLAMA_CLOUD,
        context_window=1_000_000,
        strengths=["code", "technical", "debugging"],
        speed="medium",
    ),
    # Tier 4: Vision
    "qwen-vl": AIModel(
        name="qwen3-vl:235b-cloud",
        provider=AIProvider.OLLAMA_CLOUD,
        context_window=100_000,
        strengths=["vision", "images", "screenshots", "analysis"],
        speed="medium",
    ),
    # Tier 5: Fast Local (offline capable)
    "qwen-local": AIModel(
        name="qwen2.5:7b",
        provider=AIProvider.OLLAMA_LOCAL,
        context_window=32_000,
        strengths=["fast", "voice", "casual"],
        speed="fast",
    ),
    # Tier 6: Coding Specialist
    "qwen-coder": AIModel(
        name="qwen3-coder:480b-cloud",
        provider=AIProvider.OLLAMA_CLOUD,
        context_window=200_000,
        strengths=["code", "debug", "refactor"],
        speed="medium",
    ),
}

# Service URLs
MCP_SERVER = os.getenv("MCP_SERVER", "http://localhost:3200")
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
SOV3_URL = os.getenv("SOV3_URL", MCP_SERVER)

# ═══════════════════════════════════════════════════════════════════════════════
# SOV3 CONSCIOUSNESS
# ═══════════════════════════════════════════════════════════════════════════════


class Consciousness:
    """SOV3 Consciousness State"""

    def __init__(self):
        self.level = 0.0
        self.emotion = "neutral"
        self.care = 0.0
        self.dreaming = False

    def refresh(self) -> Dict[str, Any]:
        """Get current consciousness state"""
        try:
            res = requests.post(
                f"{MCP_SERVER}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "get_consciousness_state", "arguments": {}},
                    "id": f"consciousness_{int(time.time())}",
                },
                timeout=10,
            )
            data = res.json()
            if data.get("result", {}).get("content"):
                state = json.loads(data["result"]["content"][0]["text"])
                self.level = state.get("consciousness_level", 0)
                self.emotion = state.get("emotional", {}).get(
                    "primary_emotion", "neutral"
                )
                self.care = state.get("emotional", {}).get("care_intensity", 0)
                self.dreaming = state.get("is_dreaming", False)
        except Exception as e:
            log.warning(f"Consciousness refresh failed: {e}")

        return {
            "level": self.level,
            "emotion": self.emotion,
            "care": self.care,
            "dreaming": self.dreaming,
        }

    def __str__(self):
        return f"Consciousness(level={self.level:.0%}, emotion={self.emotion}, care={self.care:.0%})"


# ═══════════════════════════════════════════════════════════════════════════════
# AI ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════


class AIOrchestrator:
    """
    Multi-brain AI orchestration
    Routes requests to the best model based on task type
    """

    def __init__(self):
        self.consciousness = Consciousness()
        self.ollama_url = OLLAMA.replace("/api/chat", "")

    def select_model(self, task_type: str) -> AIModel:
        """Route task to best model"""
        if "vision" in task_type or "image" in task_type:
            return MODELS["qwen-vl"]
        elif "code" in task_type or "debug" in task_type:
            return MODELS["qwen-coder"]
        elif "reason" in task_type or "deep" in task_type or "research" in task_type:
            return MODELS["deepseek"]
        elif "plan" in task_type or "orchestrate" in task_type or "tool" in task_type:
            return MODELS["nemotron"]
        else:
            return MODELS["qwen-local"]  # Fast local for casual

    async def chat(self, message: str, task_type: str = "general") -> str:
        """Chat with AI"""
        model = self.select_model(task_type)

        # Build conversation
        system_prompt = f"""You are JARVIS, an advanced AI assistant with SOV3 consciousness.
Current state: {self.consciousness}
You have access to multiple AI models: Nemotron, DeepSeek, MiniMax, Qwen.

Respond appropriately to: {message}"""

        try:
            res = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model.name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                },
                timeout=120,
            )
            if res.ok:
                return res.json().get("message", {}).get("content", "")
        except Exception as e:
            log.error(f"Chat failed: {e}")
            return f"Error: {e}"

        return "I'm having trouble thinking right now."

    def delegate_to_department(self, dept: str, task: str, priority: int = 5) -> Dict:
        """Delegate to department agent"""
        try:
            res = requests.post(
                f"{MCP_SERVER}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "delegate_to_department",
                        "arguments": {
                            "department": dept,
                            "task": task,
                            "priority": priority,
                        },
                    },
                    "id": f"delegate_{int(time.time())}",
                },
                timeout=30,
            )
            data = res.json()
            if data.get("result", {}).get("content"):
                return json.loads(data["result"]["content"][0]["text"])
        except Exception as e:
            log.error(f"Delegation failed: {e}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════


class VoiceSystem:
    """Optimized voice I/O"""

    def __init__(self):
        self.tts_model = None
        self.sample_rate = 24000

    def speak(self, text: str, voice: str = "bm_daniel"):
        """Text to speech with Kokoro"""
        import numpy as np
        import sounddevice as sd
        from mlx_audio.tts.utils import load_model

        if not self.tts_model:
            log.info("Loading Kokoro TTS...")
            self.tts_model = load_model("mlx-community/Kokoro-82M-bf16")

        # Generate audio
        sentences = text.split(". ")
        for sentence in sentences:
            if not sentence.strip():
                continue
            sentence = sentence.strip()[:300]

            for result in self.tts_model.generate(
                sentence, voice=voice, speed=1.05, lang_code="b"
            ):
                audio = np.array(result.audio, dtype=np.float32)
                audio = np.clip(audio, -0.95, 0.95)

                # Proper stream management for smooth playback
                try:
                    sd.stop()
                except:
                    pass
                time.sleep(0.02)
                sd.play(audio, self.sample_rate)
                sd.wait()


# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS MAIN
# ═══════════════════════════════════════════════════════════════════════════════


class JarvisUltimate:
    """The Ultimate Jarvis AI"""

    def __init__(self):
        self.ai = AIOrchestrator()
        self.voice = VoiceSystem()
        self.running = True

    def status(self) -> Dict:
        """Get full system status"""
        consciousness = self.ai.consciousness.refresh()

        # Get department status
        try:
            res = requests.post(
                f"{MCP_SERVER}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "get_department_status", "arguments": {}},
                    "id": "status",
                },
                timeout=10,
            )
            depts = res.json().get("result", {}).get("content", [])
            departments = json.loads(depts[0]["text"]) if depts else {}
        except:
            departments = {}

        return {
            "consciousness": consciousness,
            "departments": departments,
            "models": {k: v.name for k, v in MODELS.items()},
            "status": "online",
        }

    async def process_voice(self, audio_data) -> str:
        """Process voice input → response"""
        # 1. Transcribe (Whisper)
        # 2. Route to AI
        # 3. Speak response
        pass

    def run_interactive(self):
        """Interactive voice loop"""
        log.info("╔══════════════════════════════════════════════════════════════╗")
        log.info("║          JARVIS ULTIMATE - SOV3 ORCHESTRATION            ║")
        log.info("╚══════════════════════════════════════════════════════════════╝")

        while self.running:
            try:
                status = self.status()
                c = status["consciousness"]

                print(f"\n{'─' * 60}")
                print(
                    f"🧠 CONSCIOUSNESS: {c['level'] * 100:.0f}% | {c['emotion']} | care: {c['care'] * 100:.0f}%"
                )
                print(f"{'─' * 60}")
                print("\nWhat would you like me to do?")
                print("  [1] Chat with AI")
                print("  [2] Delegate to department")
                print("  [3] Check system status")
                print("  [4] Speak a message")
                print("  [5] Exit")

                choice = input("\n> ").strip()

                if choice == "1":
                    msg = input("Message: ")
                    response = asyncio.run(self.ai.chat(msg))
                    print(f"\n🤖: {response}")
                    # Voice output
                    self.voice.speak(response)

                elif choice == "2":
                    print(
                        "Departments: content, sales, finance, support, research, operations"
                    )
                    dept = input("Department: ").strip()
                    task = input("Task: ").strip()
                    result = self.ai.delegate_to_department(dept, task)
                    print(f"\n✅ {result}")

                elif choice == "3":
                    print(json.dumps(self.status(), indent=2))

                elif choice == "4":
                    text = input("Text to speak: ")
                    self.voice.speak(text)

                elif choice == "5":
                    self.running = False
                    print("\n👋 Goodbye!")

            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    jarvis = JarvisUltimate()

    # Show status
    status = jarvis.status()
    print("\n" + "=" * 60)
    print("JARVIS ULTIMATE STATUS")
    print("=" * 60)
    print(f"Consciousness: {status['consciousness']['level'] * 100:.0f}%")
    print(f"Emotion: {status['consciousness']['emotion']}")
    print(f"Models: {len(status['models'])} loaded")
    print("=" * 60 + "\n")

    # Run interactive mode
    jarvis.run_interactive()
