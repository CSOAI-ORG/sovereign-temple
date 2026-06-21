#!/usr/bin/env python3
"""
Advanced Conversation Features
- Interrupt handling
- Backchanneling
- Mid-utterance processing
- Emotion-aware timing
"""

import time
import threading
import numpy as np
from typing import Optional, Callable
import queue


# ═══ INTERRUPT HANDLING ═══
class InterruptHandler:
    """Handle user interruptions during AI speech"""

    def __init__(self):
        self.interrupted = False
        self.interrupt_thread = None
        self._lock = threading.Lock()

    def start_listening_for_interrupt(
        self, audio_callback: Callable, vad_threshold: float = 0.02
    ):
        """Start background thread listening for user speech (interrupt)"""
        self.interrupted = False

        def listen():
            import pyaudio

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=512,
            )
            try:
                while not self.interrupted:
                    try:
                        audio = (
                            np.frombuffer(
                                stream.read(512, exception_on_overflow=False),
                                dtype=np.int16,
                            ).astype(np.float32)
                            / 32768.0
                        )

                        energy = np.sqrt(np.mean(audio**2))

                        # If significant audio detected while AI is speaking = interrupt
                        if energy > vad_threshold:
                            with self._lock:
                                self.interrupted = True
                            audio_callback()
                            break
                    except:
                        continue
            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()

        self.interrupt_thread = threading.Thread(target=listen, daemon=True)
        self.interrupt_thread.start()

    def check_and_clear(self) -> bool:
        """Check if interrupted, then reset"""
        with self._lock:
            if self.interrupted:
                self.interrupted = False
                return True
            return False

    def force_interrupt(self):
        """Manually trigger interrupt"""
        with self._lock:
            self.interrupted = True


# ═══ BACKCHANNELING ═══
class BackchannelEngine:
    """Play acknowledgment sounds while user is speaking"""

    def __init__(self):
        self.enabled = True
        self.last_backchannel = 0
        self.backchannel_interval = 2.0  # seconds between backchannels
        self._playing = False

    def should_backchannel(self, audio_energy: float, speech_detected: bool) -> bool:
        """Decide if we should play backchannel"""
        if not self.enabled or self._playing:
            return False

        now = time.time()
        if speech_detected and audio_energy > 0.01:
            if now - self.last_backchannel > self.backchannel_interval:
                self.last_backchannel = now
                return True
        return False

    async def play_backchannel(self):
        """Play acknowledgment sound (mm-hmm, uh-huh)"""
        self._playing = True
        try:
            # Could use Kokoro to generate quick acknowledgment
            # For now, just a placeholder
            pass
        finally:
            self._playing = False


# ═══ MID-UTTERANCE PROCESSING ═══
class MidUtteranceProcessor:
    """Start processing before user finishes speaking"""

    def __init__(self):
        self.min_confidence = 0.7
        self.min_words = 3

    def should_start_processing(
        self, partial_text: str, confidence: float = 1.0
    ) -> bool:
        """Decide if we should start LLM processing before user finishes"""
        word_count = len(partial_text.split())

        # High confidence patterns can trigger early
        early_patterns = [
            "what's the time",
            "what time is",
            "how are you",
            "can you",
            "tell me",
            "search for",
            "look up",
        ]

        lower = partial_text.lower()

        # Always process if we have enough words
        if word_count >= self.min_words:
            return True

        # Or if it's a high-confidence pattern
        if any(p in lower for p in early_patterns):
            return True

        return False

    def get_processing_prompt(self, partial_text: str) -> str:
        """Get prompt for partial processing"""
        return f"User said (may be incomplete): {partial_text}. Provide a response if confident, otherwise ask for clarification."


# ═══ EMOTION-AWARE TIMING ═══
class EmotionAwareTiming:
    """Adjust response timing based on detected emotion"""

    def __init__(self):
        self.default_delay = 0.3  # base delay before responding
        self.emotion_delays = {
            "excited": 0.1,  # Respond quickly to match energy
            "happy": 0.2,
            "neutral": 0.3,
            "stressed": 0.5,  # Give more time
            "sad": 0.4,
            "tired": 0.4,
            "angry": 0.2,  # Be immediate, show attention
        }

    def get_response_delay(self, user_emotion: str) -> float:
        """Get appropriate delay before responding"""
        return self.emotion_delays.get(user_emotion, self.default_delay)

    def should_use_faster_tts(self, user_emotion: str) -> bool:
        """Use faster TTS for certain emotions"""
        fast_emotions = ["excited", "angry", "stressed"]
        return user_emotion in fast_emotions


# ═══ ADAPTIVE SILENCE DETECTION ═══
class AdaptiveSilenceDetector:
    """Dynamically adjust silence threshold based on context"""

    def __init__(self):
        self.base_threshold = 2.5  # seconds
        self.context_multipliers = {
            "question": 0.7,  # Shorter wait for questions
            "statement": 1.0,  # Normal wait
            "command": 0.8,  # Slightly shorter
        }
        self.current_context = "statement"

    def get_silence_threshold(self) -> float:
        """Get silence threshold based on context"""
        return self.base_threshold * self.context_multipliers.get(
            self.current_context, 1.0
        )

    def update_context(self, text: str):
        """Update context based on text"""
        if "?" in text:
            self.current_context = "question"
        elif any(
            w in text.lower().split()[:2]
            for w in ["can", "could", "would", "will", "do"]
        ):
            self.current_context = "question"
        elif any(
            text.lower().startswith(p)
            for p in ["search", "find", "look", "get", "show"]
        ):
            self.current_context = "command"
        else:
            self.current_context = "statement"


# ═══ PROACTIVE SUGGESTIONS ═══
class ProactiveSuggestions:
    """Offer helpful suggestions based on context"""

    def __init__(self):
        self.suggestion_triggers = {
            "weather": ["forecast", "temperature", "climate"],
            "time": ["date", "schedule", "calendar"],
            "search": ["more details", "related", "alternatives"],
            "code": ["test", "debug", "explain"],
            "consciousness": ["feel", "think", "aware"],
        }

    def get_suggestion(self, topic: str) -> Optional[str]:
        """Get proactive suggestion for topic"""
        topic_lower = topic.lower()

        for key, suggestions in self.suggestion_triggers.items():
            if key in topic_lower:
                import random

                return random.choice(suggestions)

        return None


# ═══ INITIALIZE ALL ═══
print("🎯 Loading advanced conversation features...")

interrupt_handler = InterruptHandler()
backchannel_engine = BackchannelEngine()
mid_utterance_processor = MidUtteranceProcessor()
emotion_aware_timing = EmotionAwareTiming()
adaptive_silence = AdaptiveSilenceDetector()
proactive_suggestions = ProactiveSuggestions()

print("✓ Advanced conversation features loaded:")
print("  - Interrupt handling")
print("  - Backchanneling")
print("  - Mid-utterance processing")
print("  - Emotion-aware timing")
print("  - Adaptive silence detection")
print("  - Proactive suggestions")
