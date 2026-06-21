#!/usr/bin/env python3
"""
Voice Bridge - Unified Voice Pipeline
Integrates: STT (Whisper/Soniox), TTS (Kokoro/Edge-TTS), VAD, Wake Word
"""

import os
import json
import asyncio
import base64
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass


@dataclass
class VoiceConfig:
    """Voice pipeline configuration"""

    # STT
    stt_model: str = "distil-large-v3"  # lightning-whisper-mlx
    stt_url: str = "http://localhost:11434"  # Local Ollama for vision models

    # TTS
    tts_voice: str = "bm_daniel"
    tts_speed: float = 1.05
    tts_engine: str = "kokoro"  # kokoro, edge-tts

    # Wake word
    wake_word: str = "hey_jarvis"
    wake_threshold: float = 0.5

    # VAD
    vad_threshold: float = 0.5
    silence_threshold: float = 1.5  # seconds of silence to end


class VoiceBridge:
    """
    Unified voice pipeline - STT -> LLM -> TTS
    Supports multiple STT/TTS backends
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.is_listening = False
        self.is_speaking = False
        self.audio_callback: Optional[Callable] = None

    async def initialize(self) -> bool:
        """Initialize voice components"""
        print("🎤 Initializing Voice Bridge...")

        # Initialize STT
        try:
            from lightning_whisper_mlx import LightningWhisperMLX

            self.stt = LightningWhisperMLX(model=self.config.stt_model, batch_size=8)
            print(f"✅ STT: {self.config.stt_model}")
        except Exception as e:
            print(f"⚠️ STT init failed: {e}")
            self.stt = None

        # Initialize TTS
        try:
            from mlx_audio.tts.utils import load_model as load_tts
            from kokoro_mlx import generate as kokoro_generate

            self.tts_model = load_tts("mlx-community/Kokoro-82M-bf16")
            self.tts_engine = "kokoro"
            print(f"✅ TTS: Kokoro-82M")
        except Exception as e:
            print(f"⚠️ Kokoro failed: {e}, falling back to edge-tts")
            self.tts_engine = "edge-tts"
            self.tts_model = None

        return True

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text"""
        if not self.stt:
            return "STT not initialized"

        try:
            result = self.stt.transcribe(audio_path=audio_path)
            return result.get("text", "").strip()
        except Exception as e:
            return f"Transcription error: {e}"

    async def speak(
        self, text: str, interrupt_callback: Optional[Callable] = None
    ) -> str:
        """Convert text to speech and play"""
        self.is_speaking = True

        try:
            if self.tts_engine == "kokoro" and self.tts_model:
                audio = await self._speak_kokoro(text, interrupt_callback)
            else:
                audio = await self._speak_edge(text, interrupt_callback)

            return audio or "Audio generated"
        finally:
            self.is_speaking = False

    async def _speak_kokoro(
        self, text: str, interrupt_callback: Optional[Callable]
    ) -> str:
        """Generate speech using Kokoro"""
        try:
            from kokoro_mlx import generate as kokoro_generate

            # Split into sentences for chunked generation
            import re

            sentences = re.split(r"(?<=[.!?])\s+", text)

            for sentence in sentences:
                if interrupt_callback and interrupt_callback():
                    break

                sentence = sentence.strip()
                if not sentence:
                    continue

                # Generate audio
                for result in self.tts_model.generate(
                    sentence[:300],  # Chunk size
                    voice=self.config.tts_voice,
                    speed=self.config.tts_speed,
                    lang_code="b",
                ):
                    if interrupt_callback and interrupt_callback():
                        break
                    yield_audio(result.audio)

            return "Speech complete"
        except Exception as e:
            return f"Kokoro error: {e}"

    async def _speak_edge(
        self, text: str, interrupt_callback: Optional[Callable]
    ) -> str:
        """Generate speech using Edge-TTS"""
        try:
            import edge_tts
            import numpy as np
            import sounddevice as sd

            communicate = edge_tts.Communicate(text, "en-US-Neural2-F")

            # Save to temp file
            tmp_path = f"/tmp/voice_bridge_{time.time()}.mp3"
            await communicate.save(tmp_path)

            # Convert MP3 to WAV and play (simplified)
            # In production, use proper audio pipeline
            return tmp_path
        except Exception as e:
            return f"Edge-TTS error: {e}"

    def set_voice(self, voice: str) -> None:
        """Set TTS voice"""
        self.config.tts_voice = voice

    def get_voices(self) -> Dict[str, str]:
        """Get available voices"""
        return {
            "kokoro": {
                "bm_daniel": "British male - clear",
                "bf_emma": "British female - warm",
                "am_adam": "American male - crisp",
                "bf_isabella": "British female - soft/calm",
            },
            "edge": {
                "en-US-Neural2-F": "American female - neural",
                "en-US-Neural2-J": "American male - neural",
            },
        }

    def get_status(self) -> Dict:
        """Get voice pipeline status"""
        return {
            "stt_ready": self.stt is not None,
            "tts_ready": self.tts_model is not None or self.tts_engine == "edge-tts",
            "stt_model": self.config.stt_model,
            "tts_engine": self.tts_engine,
            "current_voice": self.config.tts_voice,
            "listening": self.is_listening,
            "speaking": self.is_speaking,
        }


def yield_audio(audio_data):
    """Play audio (placeholder - integrate with sounddevice)"""
    import numpy as np
    import sounddevice as sd

    try:
        audio = np.array(audio_data, dtype=np.float32)
        audio = np.clip(audio, -0.95, 0.95)
        sd.play(audio, 24000)
        sd.wait()
    except Exception:
        pass


# Global instance
_voice_bridge: Optional[VoiceBridge] = None


def get_voice_bridge() -> VoiceBridge:
    global _voice_bridge
    if _voice_bridge is None:
        _voice_bridge = VoiceBridge()
    return _voice_bridge


if __name__ == "__main__":

    async def test():
        vb = await VoiceBridge().initialize()
        print(json.dumps(vb.get_status(), indent=2))

        # Test voices
        print("\n=== Available Voices ===")
        print(json.dumps(vb.get_voices(), indent=2))

    asyncio.run(test())
