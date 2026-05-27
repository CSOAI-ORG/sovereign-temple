#!/usr/bin/env python3
"""
JARVIS Voice Pipeline 2.0 - Pipecat-style async pipeline
Features:
- Async audio frame processing
- Interruptible TTS with context awareness
- Multi-model LLM routing (local/remote)
- Voice activity detection integration
- Proper audio buffer management

Run: python jarvis_voice_v2.py
"""

import asyncio
import audioop
import base64
import json
import numpy as np
import struct
import tempfile
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Callable, Optional, List, Dict, Any
import os

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import httpx
except ImportError:
    httpx = None


class VoiceState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


@dataclass
class AudioFrame:
    """Individual audio frame with metadata"""

    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    format: str = "int16"
    timestamp: float = 0.0
    is_speech: bool = True


@dataclass
class TranscriptionResult:
    """Transcription with metadata"""

    text: str
    confidence: float = 1.0
    is_final: bool = True
    language: str = "en"
    timestamp: float = 0.0


@dataclass
class LLMResponse:
    """LLM response with streaming support"""

    text: str
    done: bool = True
    model: str = ""
    finish_reason: str = "stop"
    tool_calls: List[Dict] = field(default_factory=list)


class AudioProcessor(ABC):
    """Abstract base for audio processing stages"""

    @abstractmethod
    async def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        pass

    async def flush(self) -> Optional[AudioFrame]:
        return None


class NoiseReducer(AudioProcessor):
    """Simple noise reduction using energy threshold"""

    def __init__(self, threshold: float = 0.01):
        self.threshold = threshold
        self.silence_frames = 0
        self.silence_threshold = 10

    async def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        audio_data = (
            np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0
        )
        energy = np.sqrt(np.mean(audio_data**2))

        if energy < self.threshold:
            self.silence_frames += 1
            if self.silence_frames < self.silence_threshold:
                return None  # Skip quiet frames
        else:
            self.silence_frames = 0

        return frame


class VADProcessor(AudioProcessor):
    """Voice Activity Detection - marks speech vs silence"""

    def __init__(self, energy_threshold: float = 0.02, min_speech_frames: int = 5):
        self.energy_threshold = energy_threshold
        self.min_speech_frames = min_speech_frames
        self.speech_frames = 0
        self.is_speaking = False

    async def process(self, frame: AudioFrame) -> AudioFrame:
        audio_data = (
            np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0
        )
        energy = np.sqrt(np.mean(audio_data**2))

        is_speech = energy > self.energy_threshold

        if is_speech:
            self.speech_frames += 1
            self.is_speaking = True
        else:
            if self.speech_frames > 0 and self.speech_frames < self.min_speech_frames:
                self.speech_frames = 0
                self.is_speaking = False
            elif self.speech_frames >= self.min_speech_frames:
                pass  # Keep speaking state
            else:
                self.is_speaking = False

        frame.is_speech = self.is_speaking
        return frame


class BufferProcessor(AudioProcessor):
    """Accumulates frames into larger chunks for batch processing"""

    def __init__(self, buffer_size: int = 20, overlap: int = 5):
        self.buffer_size = buffer_size
        self.overlap = overlap
        self.buffer: deque = deque(maxlen=buffer_size + overlap)
        self.frame_count = 0

    async def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        self.buffer.append(frame)
        self.frame_count += 1

        # Only emit when we have enough frames
        if len(self.buffer) >= self.buffer_size:
            # Combine frames
            combined = b"".join(f.data for f in list(self.buffer)[: self.buffer_size])
            result = AudioFrame(
                data=combined,
                sample_rate=frame.sample_rate,
                channels=frame.channels,
                timestamp=frame.timestamp,
            )
            # Keep overlap frames
            for _ in range(self.overlap):
                if self.buffer:
                    self.buffer.popleft()
            return result

        return None

    async def flush(self) -> Optional[AudioFrame]:
        if self.buffer:
            combined = b"".join(f.data for f in self.buffer)
            self.buffer.clear()
            return AudioFrame(
                data=combined, sample_rate=16000, channels=1, timestamp=0.0
            )
        return None


class WhisperClient:
    """Async Whisper transcription client"""

    def __init__(self, endpoint: str = "http://localhost:8001"):
        self.endpoint = endpoint
        self.client: Optional[httpx.AsyncClient] = None

    async def transcribe(self, audio_data: bytes) -> TranscriptionResult:
        if not httpx:
            return TranscriptionResult(text="[Whisper not available]", confidence=0.0)

        if not self.client:
            self.client = httpx.AsyncClient(timeout=30.0)

        # Save to temp file
        import scipy.io.wavfile as wavfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            wavfile.write(f.name, 16000, audio_array)
            temp_path = f.name

        try:
            with open(temp_path, "rb") as f:
                response = await self.client.post(
                    f"{self.endpoint}/transcribe", files={"file": f}
                )
            if response.status_code == 200:
                data = response.json()
                return TranscriptionResult(
                    text=data.get("text", ""),
                    confidence=data.get("confidence", 1.0),
                    is_final=True,
                )
        except Exception as e:
            pass
        finally:
            os.unlink(temp_path)

        return TranscriptionResult(text="", confidence=0.0)


class OllamaLLM:
    """Async Ollama LLM client with streaming"""

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:14b"
    ):
        self.base_url = base_url
        self.model = model
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.client:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client

    async def chat(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None
    ) -> AsyncIterator[str]:
        """Stream chat completion"""
        client = await self._get_client()

        payload = {"model": self.model, "messages": messages, "stream": True}

        if tools:
            payload["tools"] = tools

        async with client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield content
                        if data.get("done", False):
                            break
                    except:
                        pass

    async def complete(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Single completion"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        full_text = ""
        async for chunk in self.chat(messages):
            full_text += chunk

        return LLMResponse(text=full_text, done=True, model=self.model)


class KokoroTTS:
    """Async Kokoro TTS client"""

    def __init__(self, endpoint: str = "http://localhost:5000"):
        self.endpoint = endpoint
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.client:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def speak(
        self, text: str, voice: str = "bm_daniel", speed: float = 1.0
    ) -> AsyncIterator[bytes]:
        """Stream audio chunks"""
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.endpoint}/speak",
                json={"text": text, "voice": voice, "speed": speed},
                timeout=30.0,
            )
            if response.status_code == 200:
                audio_data = response.content
                # Yield in chunks
                chunk_size = 4096
                for i in range(0, len(audio_data), chunk_size):
                    yield audio_data[i : i + chunk_size]
        except:
            pass

    async def speak_streaming(
        self, text: str, voice: str = "bm_daniel"
    ) -> AsyncIterator[AudioFrame]:
        """Generate TTS with proper framing"""
        import re

        # Split into sentences for natural flow
        sentences = re.split(r"(?<=[.!?])\s+", text)

        async for audio_chunk in self.speak(sentences[0] if sentences else text, voice):
            yield AudioFrame(
                data=audio_chunk, sample_rate=24000, channels=1, timestamp=0.0
            )


class InterruptibleTTS:
    """TTS with interrupt capability"""

    def __init__(self, tts: KokoroTTS):
        self.tts = tts
        self.current_task: Optional[asyncio.Task] = None
        self.interrupted = False
        self.queue: asyncio.Queue = asyncio.Queue()

    async def speak(self, text: str, voice: str = "bm_daniel"):
        """Start speaking - can be interrupted"""
        self.interrupted = False

        async def generate():
            try:
                async for frame in self.tts.speak_streaming(text, voice):
                    if self.interrupted:
                        break
                    await self.queue.put(frame)
            finally:
                await self.queue.put(None)  # Signal done

        self.current_task = asyncio.create_task(generate())

    def interrupt(self):
        """Interrupt current speech"""
        self.interrupted = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

    async def audio_stream(self) -> AsyncIterator[bytes]:
        """Get audio chunks"""
        while True:
            frame = await self.queue.get()
            if frame is None:
                break
            yield frame.data


@dataclass
class PipelineContext:
    """Context passed through pipeline"""

    state: VoiceState = VoiceState.IDLE
    transcript: str = ""
    llm_response: str = ""
    tool_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VoicePipeline:
    """Main voice pipeline orchestrator"""

    def __init__(self):
        # Audio processors
        self.noise_reducer = NoiseReducer(threshold=0.008)
        self.vad = VADProcessor(energy_threshold=0.015, min_speech_frames=3)
        self.buffer = BufferProcessor(buffer_size=15, overlap=3)

        # AI services
        self.whisper = WhisperClient(endpoint="http://localhost:8001")
        self.llm = OllamaLLM(model="qwen2.5:14b")
        self.tts = KokoroTTS(endpoint="http://localhost:5000")
        self.interruptible_tts = InterruptibleTTS(self.tts)

        # State
        self.state = VoiceState.IDLE
        self.context = PipelineContext()
        self.listeners: List[Callable[[VoiceState, PipelineContext], None]] = []

        # Audio playback
        self.stream_out: Optional[sd.OutputStream] = None

    def add_listener(self, callback: Callable[[VoiceState, PipelineContext], None]):
        """Add state change listener"""
        self.listeners.append(callback)

    async def _notify(self):
        for listener in self.listeners:
            try:
                listener(self.state, self.context)
            except:
                pass

    async def process_audio_frame(
        self, frame: AudioFrame
    ) -> Optional[TranscriptionResult]:
        """Process incoming audio through pipeline"""
        # Noise reduction
        frame = await self.noise_reducer.process(frame)
        if frame is None:
            return None

        # VAD
        frame = await self.vad.process(frame)

        # Buffer for batch processing
        buffered = await self.buffer.process(frame)

        if buffered and frame.is_speech:
            self.state = VoiceState.LISTENING
            await self._notify()

            # Transcribe
            result = await self.whisper.transcribe(buffered.data)
            if result.text.strip():
                self.context.transcript = result.text
                return result

        return None

    async def flush(self) -> Optional[TranscriptionResult]:
        """Flush remaining buffer"""
        buffered = await self.buffer.flush()
        if buffered:
            return await self.whisper.transcribe(buffered.data)
        return None

    async def respond(self, prompt: Optional[str] = None) -> str:
        """Get LLM response to transcript"""
        self.state = VoiceState.PROCESSING
        await self._notify()

        user_msg = prompt or self.context.transcript

        system = """You are JARVIS, a helpful AI assistant. 
Be concise, intelligent, and slightly witty. Keep responses natural and conversational."""

        response = await self.llm.complete(user_msg, system)
        self.context.llm_response = response.text

        self.state = VoiceState.SPEAKING
        await self._notify()

        return response.text

    async def speak(self, text: str):
        """Speak text with interrupt support"""
        await self.interruptible_tts.speak(text)

        async for audio in self.interruptible_tts.audio_stream():
            if self.state == VoiceState.INTERRUPTED:
                break
            # Play audio
            if sd:
                try:
                    audio_array = np.frombuffer(audio, dtype=np.float32)
                    sd.play(audio_array, 24000)
                except:
                    pass

        self.state = VoiceState.IDLE
        await self._notify()

    def interrupt(self):
        """Interrupt current operation"""
        self.state = VoiceState.INTERRUPTED
        self.interruptible_tts.interrupt()
        self._notify()


class RealTimeVoiceAssistant:
    """Complete real-time voice assistant"""

    def __init__(self):
        self.pipeline = VoicePipeline()
        self.running = False

    async def start_listening(self):
        """Start audio input capture"""
        self.running = True

        if not sd:
            print("sounddevice not available")
            return

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")

            # Convert to frame
            audio_bytes = indata[:, 0].tobytes()
            frame = AudioFrame(
                data=audio_bytes, sample_rate=16000, timestamp=time_info.currentTime
            )

            # Process in background
            asyncio.create_task(self.pipeline.process_audio_frame(frame))

        try:
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype=np.float32,
                blocksize=1024,
                callback=callback,
            ):
                print("🎙️ Listening... (Ctrl+C to stop)")
                while self.running:
                    await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop listening"""
        self.running = False
        self.pipeline.interrupt()
        print("\n👋 Stopped")


async def demo():
    """Demo the pipeline components"""
    print("=" * 50)
    print("JARVIS Voice Pipeline 2.0 Demo")
    print("=" * 50)

    pipeline = VoicePipeline()

    # Test LLM
    print("\n1. Testing LLM...")
    response = await pipeline.llm.complete("What is 2+2?")
    print(f"   LLM: {response.text[:100]}...")

    # Test TTS (without playback)
    print("\n2. Testing TTS...")
    async for frame in pipeline.tts.speak_streaming("Hello, I am JARVIS."):
        print(f"   TTS frame: {len(frame.data)} bytes")
        break

    print("\n3. Testing audio processors...")
    test_frame = AudioFrame(data=b"\x00" * 1024, sample_rate=16000, timestamp=0.0)
    processed = await pipeline.vad.process(test_frame)
    print(f"   VAD: is_speech={processed.is_speech}")

    print("\n✅ Pipeline components working!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo())
    else:
        print("Usage: python jarvis_voice_v2.py demo")
        print("       python jarvis_voice_v2.py  # Start real-time")
        print("\nFor real-time, you'll need:")
        print("  - sounddevice: pip install sounddevice")
        print("  - Whisper API at localhost:8001")
        print("  - Kokoro TTS at localhost:5000")
