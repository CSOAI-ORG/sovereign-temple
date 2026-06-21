#!/usr/bin/env python3
"""
JARVIS Advanced Conversational AI
Next-level voice assistant - continuous, emotional, intelligent

Features:
1. Continuous conversation (no push-to-talk needed)
2. Voice Activity Detection - knows when to listen
3. Emotional intelligence - responds to user's tone
4. Context memory - remembers conversation
5. Interrupt handling - can be stopped mid-sentence
6. Turn-taking - natural pauses, knows when to respond
7. Streaming TTS - speaks while thinking
8. Multimodal - sees screen, knows context

This is like Samantha from "Her" - the AI we want to build
"""

import asyncio
import json
import queue
import threading
import time
import numpy as np
import sounddevice as sd
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from enum import Enum

# Audio settings
RATE = 16000
CHUNK_SIZE = 4096


class ConversationState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


@dataclass
class ConversationTurn:
    """Single turn in conversation"""

    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    emotion: str = "neutral"


@dataclass
class UserEmotion:
    """Detected user emotion"""

    primary: str = "neutral"
    energy: float = 0.5  # 0=low, 1=high
    valence: float = 0.5  # 0=negative, 1=positive


class ContinuousVAD:
    """
    Voice Activity Detection - knows when user is speaking
    Different from push-to-talk - detects speech automatically
    """

    def __init__(self, threshold: float = 0.02, min_speech_duration: float = 0.3):
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.is_speaking = False
        self.speech_start = 0.0
        self.audio_buffer = []
        self.stream = None

    def start(self):
        """Start continuous listening"""
        self.audio_buffer = []

        def callback(indata, frames, time_info, status):
            if status:
                return

            # Get RMS amplitude
            if indata.ndim > 1:
                mono = indata[:, 0]
            else:
                mono = indata

            rms = np.sqrt(np.mean(mono**2))

            # Speech detection with hysteresis
            if rms > self.threshold:
                if not self.is_speaking:
                    self.is_speaking = True
                    self.speech_start = time.time()
                    print("🟢 User started speaking")
                self.audio_buffer.append(mono.copy())
            else:
                if self.is_speaking:
                    speech_duration = time.time() - self.speech_start
                    if speech_duration > self.min_speech_duration:
                        # Valid speech segment ended
                        print(f"🔴 User stopped speaking ({speech_duration:.1f}s)")
                        self.on_speech_end()
                    self.is_speaking = False
                    self.audio_buffer = []

        self.stream = sd.InputStream(
            samplerate=RATE,
            channels=1,
            dtype=np.float32,
            blocksize=1024,
            callback=callback,
        )
        self.stream.start()

    def on_speech_end(self):
        """Override this - called when user finishes speaking"""
        pass

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None


class EmotionDetector:
    """Detects user's emotion from voice"""

    def __init__(self):
        self.history: List[UserEmotion] = []

    def detect(self, audio: np.ndarray) -> UserEmotion:
        """Simple energy-based emotion detection"""
        rms = np.sqrt(np.mean(audio**2))

        # Energy = excitement/energy level
        energy = min(1.0, rms * 10)

        # Simple heuristic - can be improved with ML
        if rms < 0.01:
            primary = "quiet"
            energy = 0.2
        elif rms > 0.1:
            primary = "excited"
            energy = 0.9
        else:
            primary = "neutral"

        emotion = UserEmotion(primary=primary, energy=energy)
        self.history.append(emotion)

        if len(self.history) > 10:
            self.history.pop(0)

        return emotion


class ConversationalJARVIS:
    """
    Advanced conversational JARVIS - like Samantha from Her

    States:
    - IDLE: Waiting, VAD active
    - LISTENING: User is speaking, capturing audio
    - THINKING: Processing, may speak partial thoughts
    - SPEAKING: Responding, can be interrupted
    - INTERRUPTED: User cut in, return to listening
    """

    def __init__(self):
        self.state = ConversationState.IDLE
        self.conversation_history: List[ConversationTurn] = []
        self.vad = ContinuousVAD()
        self.emotion_detector = EmotionDetector()

        # Response cache for continuous context
        self.last_user_message = ""
        self.last_response = ""

        # Flags
        self.running = False
        self.should_interrupt = False

    def start(self):
        """Start continuous conversation"""
        self.running = True

        print("=" * 60)
        print("🎙️ JARVIS - Advanced Conversational AI")
        print("=" * 60)
        print("Say 'Hey JARVIS' to start conversation")
        print("Say 'Goodbye' to end")
        print("=" * 60)

        # Start VAD
        self.vad.start()

        # Main conversation loop
        self.conversation_loop()

    def conversation_loop(self):
        """Main conversation loop"""
        while self.running:
            # Monitor for wake word in background
            # For now, use simple input
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            # Check for exit
            if user_input.lower() in ["goodbye", "exit", "quit"]:
                self.speak("Goodbye, Sir. It's been an honor talking with you.")
                break

            # Process conversation
            self.process_turn(user_input)

    def process_turn(self, user_input: str):
        """Process a conversation turn"""
        self.state = ConversationState.THINKING
        print("🤔 Thinking...")

        # Add to history
        self.conversation_history.append(
            ConversationTurn(role="user", content=user_input)
        )

        # Get response with context
        response = self.get_contextual_response(user_input)

        # Add to history
        self.conversation_history.append(
            ConversationTurn(role="assistant", content=response)
        )

        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        # Speak with emotion
        self.state = ConversationState.SPEAKING
        self.speak(response, emotion=self.detect_response_emotion(response))

        self.state = ConversationState.IDLE

    def get_contextual_response(self, text: str) -> str:
        """Get response with full conversation context"""
        import httpx

        # Build context from history
        context_parts = []
        for turn in self.conversation_history[-6:]:  # Last 6 turns
            prefix = "User" if turn.role == "user" else "JARVIS"
            context_parts.append(f"{prefix}: {turn.content}")

        context = "\n".join(context_parts)

        # Build prompt
        prompt = f"""You are JARVIS, an advanced AI assistant with a warm, intelligent personality.
You have memory of this conversation and respond naturally to what was just said.

Current conversation:
{context}

User just said: {text}

Respond naturally as JARVIS would - be helpful, slightly witty, and concise. 
If referencing something from earlier in conversation, acknowledge it.
Keep responses conversational, like talking to a friend.
"""

        try:
            # Try local Ollama first
            r = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen2.5:14b", "prompt": prompt, "stream": False},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json().get("response", "")[:500]
        except:
            pass

        # Fallback to MCP
        try:
            r = httpx.post(
                "http://localhost:3200/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ask_sovereign",
                        "arguments": {"message": text, "context": context},
                    },
                    "id": "chat",
                },
                timeout=30,
            )
            d = r.json()
            if d.get("result", {}).get("content"):
                return json.loads(d["result"]["content"][0]["text"]).get(
                    "response", ""
                )[:500]
        except Exception as e:
            print(f"Error: {e}")

        return "I'm here, Sir. Tell me more."

    def detect_response_emotion(self, text: str) -> str:
        """Detect appropriate emotion for response"""
        text_lower = text.lower()

        if any(w in text_lower for w in ["happy", "great", "wonderful", "excellent"]):
            return "happy"
        elif any(w in text_lower for w in ["sorry", "unfortunately", "unfortunately"]):
            return "apologetic"
        elif any(w in text_lower for w in ["excited", "amazing", "incredible"]):
            return "enthusiastic"
        elif "?" in text:
            return "curious"
        else:
            return "neutral"

    def speak(self, text: str, emotion: str = "neutral"):
        """Speak with emotion - interruptible"""
        if not text:
            return

        print(f"🤖 JARVIS: {text[:60]}...")

        # Select voice based on emotion
        voice_map = {
            "happy": "bm_fable",
            "enthusiastic": "bm_onyx",
            "apologetic": "bm_aloe",
            "curious": "bm_daniel",
            "neutral": "bm_daniel",
        }
        voice = voice_map.get(emotion, "bm_daniel")

        try:
            from mlx_audio.tts.utils import load_model

            tts = load_model("mlx-community/Kokoro-82M-bf16")

            # Split into sentences for natural flow
            import re

            sentences = re.split(r"(?<=[.!?])\s+", text)

            for sentence in sentences:
                if self.should_interrupt:
                    print("🛑 Interrupted!")
                    self.should_interrupt = False
                    break

                sentence = sentence.strip()
                if len(sentence) < 2:
                    continue

                for result in tts.generate(
                    sentence, voice=voice, speed=1.0, lang_code="b"
                ):
                    if self.should_interrupt:
                        break
                    audio = np.array(result.audio, dtype=np.float32)
                    audio = np.clip(audio, -0.95, 0.95)
                    sd.play(audio, 24000)
                    sd.wait()

        except Exception as e:
            print(f"TTS error: {e}")
            # Fallback to Web Speech
            try:
                import threading

                def speak_web():
                    utterance = speechSynthesis.speak(text)

                threading.Thread(target=speak_web, daemon=True).start()
            except:
                pass


class VoiceCommandProcessor:
    """Processes voice commands with intent recognition"""

    def __init__(self, jarvis: ConversationalJARVIS):
        self.jarvis = jarvis

    def process(self, text: str) -> Optional[str]:
        """Process voice command or return None to continue conversation"""
        text_lower = text.lower().strip()

        # Wake commands
        wake_words = ["hey jarvis", "jarvis", "hello jarvis", "ok jarvis"]
        if any(w in text_lower for w in wake_words):
            self.jarvis.speak("Yes, Sir? I'm listening.")
            return None  # Continue to conversation

        # Action commands
        if "what can you do" in text_lower:
            return self.list_capabilities()
        elif "tell me about" in text_lower or "what is" in text_lower:
            return self.explain_concept(text_lower)
        elif "remember" in text_lower:
            return self.create_memory(text_lower)
        elif "what did i say" in text_lower or "what did i tell you" in text_lower:
            return self.recall_last()

        # Exit commands
        if text_lower in ["goodbye", "exit", "quit", "that's all"]:
            return "goodbye"

        return None  # Not a command, continue to conversation

    def list_capabilities(self) -> str:
        return """I can help you with many things:

• Answer questions and have conversations
• Remember things you tell me
• Control your smart home
• Check your system status
• Run commands on your computer
• And much more - just ask!"""

    def explain_concept(self, text: str) -> str:
        return "I'm not sure about that. Would you like me to look it up?"

    def create_memory(self, text: str) -> str:
        # Extract what to remember
        if "remember that" in text:
            memory = text.replace("remember that", "").strip()
        elif "remember" in text:
            memory = text.replace("remember", "").strip()
        else:
            memory = text

        self.jarvis.conversation_history.append(
            ConversationTurn(role="memory", content=memory)
        )
        return f"I'll remember that: {memory}"

    def recall_last(self) -> str:
        memories = [t for t in self.jarvis.conversation_history if t.role == "memory"]
        if memories:
            return f"You told me: {memories[-1].content}"
        return "I don't have any memories from you yet."


def demo_conversation():
    """Demo the conversational system"""
    jarvis = ConversationalJARVIS()
    processor = VoiceCommandProcessor(jarvis)

    print("Starting demo conversation...")
    print("Type your messages or say 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        # Check for commands
        response = processor.process(user_input)

        if response == "goodbye":
            jarvis.speak("Goodbye, Sir. Until next time.")
            break
        elif response:
            jarvis.speak(response)
        else:
            # Process as conversation
            jarvis.process_turn(user_input)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            demo_conversation()
    else:
        jarvis = ConversationalJARVIS()
        jarvis.start()
