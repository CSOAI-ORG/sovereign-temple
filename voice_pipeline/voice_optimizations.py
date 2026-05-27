#!/usr/bin/env python3
"""
Voice Pipeline Optimizations
Improves latency, responsiveness, and natural conversation
"""

import os
import time
import threading
import asyncio
import numpy as np
from typing import Optional, Callable
import wave
import json


# ═══ OPTIMIZATION 1: Faster Wake Word Detection ═══
class FastWakeWord:
    """Optimized wake word with lower threshold and faster response"""

    def __init__(self, model_path=None):
        try:
            from openwakeword.model import Model as WakeModel

            self.model = WakeModel()
            self.enabled = True
            self.threshold = 0.3  # Lower threshold = more responsive (was 0.5)
            self.cooldown = 0
        except Exception as e:
            print(f"Wake word init failed: {e}")
            self.enabled = False

    def predict(self, audio):
        if not self.enabled:
            return {"hey_jarvis": 0}

        if self.cooldown > 0:
            self.cooldown -= 1
            return {"hey_jarvis": 0}

        try:
            result = self.model.predict(audio)
            score = result.get("hey_jarvis", 0)
            if score > self.threshold:
                self.cooldown = 10  # Prevent rapid re-trigger
                return {"hey_jarvis": score}
        except:
            pass
        return {"hey_jarvis": 0}


# ═══ OPTIMIZATION 2: Adaptive VAD ═══
class AdaptiveVAD:
    """Smarter voice activity detection with adaptive thresholds"""

    def __init__(self):
        from silero_vad import load_silero_vad

        self.vad = load_silero_vad()
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
        self.adaptive_threshold = 0.5
        self.min_speech_frames = 3  # Require minimum speech before starting

    def reset_states(self):
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False

    def detect(self, chunk, sample_rate=16000):
        """Returns True if speech detected"""
        is_speech = (
            self.vad(torch.from_numpy(chunk), sample_rate).item()
            > self.adaptive_threshold
        )

        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
            if self.speech_frames >= self.min_speech_frames:
                self.is_speaking = True
        else:
            if self.is_speaking:
                self.silence_frames += 1

        return self.is_speaking, self.silence_frames


# ═══ OPTIMIZATION 3: Parallel STT Processing ═══
class FastSTT:
    """Optimized speech-to-text with caching and parallel processing"""

    def __init__(self):
        from lightning_whisper_mlx import LightningWhisperMLX

        self.model = LightningWhisperMLX(model_size="distil-large-v3")
        self.cache = {}
        self.cache_lock = threading.Lock()

    def transcribe(self, audio_bytes: bytes, prompt: str = "") -> str:
        """Transcribe with optional prompt for context"""
        import uuid
        import tempfile

        # Check cache (simple hash of audio length)
        cache_key = len(audio_bytes)
        with self.cache_lock:
            if cache_key in self.cache:
                return self.cache[cache_key]

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            wf = wave.open(tmp_path, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_bytes)
            wf.close()

            result = self.model.transcribe(audio_path=tmp_path, prompt=prompt)
            text = result["text"].strip()

            # Cache result
            with self.cache_lock:
                if len(self.cache) < 100:
                    self.cache[cache_key] = text

            return text
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass


# ═══ OPTIMIZATION 4: Smart Response Formatter ═══
class ResponseFormatter:
    """Makes LLM responses more conversational and natural"""

    def __init__(self):
        self.last_response = ""

    def format(self, response: str) -> str:
        """Clean up and enhance response for voice"""
        if not response:
            return "I'm not sure how to respond to that, Sir."

        # Remove JSON artifacts
        import re

        response = re.sub(r"\{[^}]*\}", "", response)
        response = re.sub(r"\[[^\]]*\]", "", response)

        # Remove markdown
        response = re.sub(r"\*\*([^*]+)\*\*", r"\1", response)
        response = re.sub(r"\*([^*]+)\*", r"\1", response)
        response = re.sub(r"`([^`]+)`", r"\1", response)

        # Clean up multiple spaces
        response = re.sub(r"\s+", " ", response)

        # Remove leftover punctuation patterns
        response = re.sub(r"^[.,;:]+", "", response)
        response = response.strip()

        # Add natural variety based on response length
        if len(response) > 200:
            # Longer responses - add conversational lead-in
            if not response.lower().startswith(
                (
                    "yes",
                    "no",
                    "well",
                    "actually",
                    "sure",
                    "look",
                    "here",
                    "think",
                    "know",
                )
            ):
                response = "Here's what I think, Sir. " + response

        # Truncate very long responses for TTS
        max_chars = 1500
        if len(response) > max_chars:
            response = response[:max_chars]
            # Try to end on a complete sentence
            last_period = response.rfind(".")
            if last_period > max_chars - 200:
                response = response[: last_period + 1]

        self.last_response = response
        return response

    def is_question(self, text: str) -> bool:
        """Check if user asked a question"""
        text = text.lower().strip()
        question_words = [
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "can",
            "could",
            "would",
            "should",
            "is",
            "are",
            "do",
            "does",
            "tell",
            "explain",
        ]
        return any(text.startswith(q) for q in question_words)


# ═══ OPTIMIZATION 5: Predictive Caching ═══
class PredictiveCache:
    """Predict and pre-load common responses"""

    def __init__(self):
        self.cache = {}
        self.common_queries = {
            "hello": "Hello, Sir. How can I help you?",
            "hi": "Hi, Sir. What can I do for you?",
            "hey": "Hey, Sir. Ready when you are.",
            "time": "It's currently ",
            "date": "Today is ",
            "weather": "Let me check the weather for you.",
        }

    def get(self, query: str) -> Optional[str]:
        """Check if we have a cached response"""
        lower = query.lower().strip()

        # Direct match
        if lower in self.cache:
            return self.cache[lower]

        # Common query match
        for key, response in self.common_queries.items():
            if key in lower:
                return response

        return None

    def add(self, query: str, response: str):
        """Add to cache"""
        self.cache[query.lower().strip()] = response


# ═══ OPTIMIZATION 6: Quick-Reply Mode ═══
class QuickReplyEngine:
    """Fast responses for common queries without LLM"""

    def __init__(self):
        import datetime

        self.handlers = []

        # Time handler
        def get_time():
            return f"It's {datetime.datetime.now().strftime('%I:%M %p')}, Sir."

        self.handlers.append(("time", get_time))

        # Date handler
        def get_date():
            return f"Today is {datetime.datetime.now().strftime('%A, %B %d')}, Sir."

        self.handlers.append(("date", get_date))

    def process(self, text: str) -> Optional[str]:
        """Check if we can handle this quickly"""
        lower = text.lower().strip()

        for key, handler in self.handlers:
            if key in lower:
                try:
                    return handler()
                except:
                    pass

        return None


# ═══ OPTIMIZATION 7: Parallel LLM + TTS Start ═══
class StreamingResponseHandler:
    """Start TTS earlier by streaming response generation"""

    def __init__(self):
        self.tts_queue = None
        self.tts_thread = None

    def start_early(self, text: str, speak_func: Callable):
        """Start speaking before full response is ready"""
        # This would be integrated with the main response handler
        # For now, just a placeholder for the streaming approach
        pass


# ═══ PERFORMANCE MONITORING ═══
class PerformanceMonitor:
    """Track and report performance metrics"""

    def __init__(self):
        self.metrics = {
            "wake_detection": [],
            "speech_recording": [],
            "transcription": [],
            "llm_response": [],
            "tts_generation": [],
        }

    def record(self, stage: str, duration: float):
        if stage in self.metrics:
            self.metrics[stage].append(duration)
            # Keep only last 10 measurements
            self.metrics[stage] = self.metrics[stage][-10:]

    def report(self) -> str:
        lines = ["Performance Report:"]
        for stage, times in self.metrics.items():
            if times:
                avg = sum(times) / len(times)
                lines.append(f"  {stage}: {avg * 1000:.0f}ms avg")
        return "\n".join(lines)


# ═══ INITIALIZE ALL OPTIMIZATIONS ═══
print("🚀 Loading voice optimizations...")

# These will be imported and used in jarvis_compass.py
FAST_WAKE = FastWakeWord()
ADAPTIVE_VAD = AdaptiveVAD()
RESPONSE_FORMATTER = ResponseFormatter()
PREDICTIVE_CACHE = PredictiveCache()
QUICK_REPLY = QuickReplyEngine()
PERF_MONITOR = PerformanceMonitor()

print("✓ Optimizations loaded: FastWake, AdaptiveVAD, ResponseFormatter, QuickReply")
