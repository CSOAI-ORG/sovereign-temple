#!/usr/bin/env python3
"""
JARVIS Voice Mode - Claude Code Style
Push-to-talk, continuous conversation, natural flow

Key features:
1. Hold spacebar (or button) to talk, release to send
2. Continuous listening - can add multiple sentences
3. Fast response - streams as AI generates
4. Natural TTS - interruptible, human-like
5. Seamless switching - type or speak anytime

Based on Claude Code voice mode design
"""

import asyncio
import threading
import time
import queue
import numpy as np
import sounddevice as sd
from typing import Optional, Callable
import re

# Audio settings
RATE = 16000
CHUNK_SIZE = 4096


class PushToTalk:
    """Push-to-talk voice input - hold to talk, release to send"""

    def __init__(self, on_transcript: Callable[[str], None]):
        self.on_transcript = on_transcript
        self.is_recording = False
        self.audio_buffer = []
        self.stream = None

    def start(self):
        """Start recording - called when button pressed/space held"""
        if self.is_recording:
            return
        self.is_recording = True
        self.audio_buffer = []

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio callback: {status}")
            if self.is_recording:
                # Convert to mono and float32
                mono = indata[:, 0] if indata.ndim > 1 else indata
                self.audio_buffer.append(mono.copy())

        self.stream = sd.InputStream(
            samplerate=RATE,
            channels=1,
            dtype=np.float32,
            blocksize=CHUNK_SIZE,
            callback=callback,
        )
        self.stream.start()
        print("🎙️ Listening... (release to send)")

    def stop(self):
        """Stop recording - called when button released/space released"""
        if not self.is_recording:
            return
        self.is_recording = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.audio_buffer:
            audio = np.concatenate(self.audio_buffer)
            # Save to temp file for Whisper
            import tempfile
            import scipy.io.wavfile as wavfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wavfile.write(f.name, RATE, (audio * 32767).astype(np.int16))
                temp_path = f.name

            # Transcribe
            text = self.transcribe(temp_path)
            if text and text.strip():
                print(f"📝 Got: {text}")
                self.on_transcript(text)

            # Cleanup
            import os

            os.unlink(temp_path)
        else:
            print("No audio recorded")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio using local Whisper"""
        try:
            from lightning_whisper_mlx import LightningWhisperMLX

            model = LightningWhisperMLX(model="distil-large-v3", batch_size=12)
            result = model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception as e:
            print(f"Transcribe error: {e}")
            return ""


class NaturalTTS:
    """Natural TTS - interruptible, human-like, streams while generating"""

    def __init__(self):
        self.current_audio = None
        self.is_speaking = False
        self.interrupt_flag = False
        self.tts_model = None

    def load_model(self):
        """Lazy load TTS model"""
        if self.tts_model is None:
            from mlx_audio.tts.utils import load_model

            print("Loading Kokoro TTS...")
            self.tts_model = load_model("mlx-community/Kokoro-82M-bf16")
        return self.tts_model

    def speak(self, text: str, interrupt: bool = True):
        """Speak text - interruptible"""
        if interrupt:
            self.interrupt()

        if not text:
            return

        self.is_speaking = True

        # Split into sentences for more natural flow
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for i, sentence in enumerate(sentences):
            if self.interrupt_flag:
                break
            sentence = sentence.strip()
            if len(sentence) < 2:
                continue

            try:
                tts = self.load_model()

                for result in tts.generate(
                    sentence, voice="bm_daniel", speed=1.05, lang_code="b"
                ):
                    if self.interrupt_flag:
                        break
                    audio = np.array(result.audio, dtype=np.float32)
                    audio = np.clip(audio, -0.95, 0.95)

                    # Play while generating (streaming)
                    sd.play(audio, 24000)
                    sd.wait()

            except Exception as e:
                print(f"TTS error: {e}")

        self.is_speaking = False
        self.interrupt_flag = False

    def interrupt(self):
        """Interrupt current speech"""
        self.interrupt_flag = True
        try:
            sd.stop()
        except:
            pass
        self.is_speaking = False


class ClaudeStyleVoice:
    """
    Claude Code style voice for JARVIS
    - Push to talk (hold space/button)
    - Continuous conversation
    - Natural flow
    """

    def __init__(self):
        self.ptt = PushToTalk(self.on_user_speech)
        self.tts = NaturalTTS()
        self.conversation_active = False
        self.last_response = ""

    def on_user_speech(self, text: str):
        """Handle transcribed speech - send to JARVIS"""
        print(f"👤 You: {text}")

        # Get response from JARVIS/Sovereign
        response = self.ask_jarvis(text)

        # Speak naturally
        print(f"🤖 JARVIS: {response[:100]}...")
        self.tts.speak(response)

    def ask_jarvis(self, text: str) -> str:
        """Get response from JARVIS"""
        # Use MCP /mcp endpoint
        import httpx
        import json

        try:
            r = httpx.post(
                "http://localhost:3200/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "ask_sovereign", "arguments": {"message": text}},
                    "id": "voice",
                },
                timeout=30,
            )
            d = r.json()
            if d.get("result", {}).get("content"):
                return json.loads(d["result"]["content"][0]["text"]).get(
                    "response", ""
                )[:500]
        except Exception as e:
            print(f"JARVIS error: {e}")

        return "I'm here, Sir. How may I assist you?"

    def run_interactive(self):
        """Run interactive voice mode"""
        print("=" * 50)
        print("🎙️ JARVIS Voice Mode - Claude Code Style")
        print("=" * 50)
        print("Press ENTER to start recording")
        print("Press ENTER again to stop and send")
        print("Type 'quit' to exit")
        print("=" * 50)

        while True:
            try:
                user_input = input(
                    "\n🎤 Press ENTER to talk (or type message): "
                ).strip()

                if user_input.lower() in ("quit", "exit", "goodbye"):
                    self.tts.speak("Goodbye, Sir. Sovereign stands down.")
                    break

                if user_input:
                    # Text input - process directly
                    print(f"👤 You: {user_input}")
                    response = self.ask_jarvis(user_input)
                    print(f"🤖 JARVIS: {response[:80]}...")
                    self.tts.speak(response)
                else:
                    # Voice input
                    print("🎙️ HOLD to talk, RELEASE to send...")
                    input("Press ENTER to start, ENTER again to stop...")
                    self.ptt.start()
                    input("Press ENTER to stop...")
                    self.ptt.stop()

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


def test_push_to_talk():
    """Test push-to-talk mode"""
    print("Testing push-to-talk voice...")

    def on_speech(text):
        print(f"📝 Transcribed: {text}")

    ptt = PushToTalk(on_speech)

    print("Press ENTER to start recording, ENTER to stop")
    input()
    ptt.start()
    input()
    ptt.stop()


def test_tts():
    """Test natural TTS"""
    print("Testing natural TTS...")
    tts = NaturalTTS()
    tts.speak("Hello Sir. I am JARVIS. All systems are operational.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test-ptt":
            test_push_to_talk()
        elif sys.argv[1] == "test-tts":
            test_tts()
    else:
        voice = ClaudeStyleVoice()
        voice.run_interactive()
