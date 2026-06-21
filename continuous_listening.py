#!/usr/bin/env python3
"""
Continuous Listening Mode - Jarvis stays awake between responses
"""

import time
import threading
import queue
from typing import Callable, Optional


class ContinuousListener:
    """Keep Jarvis listening between responses"""

    def __init__(self):
        self.listening = False
        self.command_queue = queue.Queue()
        self.background_thread = None
        self.vad_threshold = 0.02
        self.silence_threshold = 3.0  # seconds of silence before command

    def start(self):
        """Start continuous listening"""
        if self.listening:
            return

        self.listening = True
        self.command_queue = queue.Queue()

        def listen_loop():
            import pyaudio
            import numpy as np

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=512,
            )

            try:
                while self.listening:
                    try:
                        audio = (
                            np.frombuffer(
                                stream.read(512, exception_on_overflow=False),
                                dtype=np.int16,
                            ).astype(np.float32)
                            / 32768.0
                        )

                        energy = np.sqrt(np.mean(audio**2))

                        # If significant audio, queue for processing
                        if energy > self.vad_threshold:
                            self.command_queue.put(("audio_detected", energy))
                            time.sleep(0.5)  # Debounce
                        else:
                            self.command_queue.put(("silence", energy))

                    except:
                        continue

            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()

        self.background_thread = threading.Thread(target=listen_loop, daemon=True)
        self.background_thread.start()

    def stop(self):
        """Stop continuous listening"""
        self.listening = False
        if self.background_thread:
            self.background_thread.join(timeout=2)

    def get_command(self, timeout: float = 0.1) -> Optional[tuple]:
        """Get next command from queue"""
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_speaking(self) -> bool:
        """Check if user is speaking (for pausing TTS)"""
        # Would check recent queue entries
        return False


# Global instance
_continuous_listener = None


def get_continuous_listener() -> ContinuousListener:
    global _continuous_listener
    if _continuous_listener is None:
        _continuous_listener = ContinuousListener()
    return _continuous_listener


# Context-aware suggestions
class ContextSuggestions:
    """Suggest actions based on context"""

    def __init__(self):
        self.context_history = []
        self.suggestion_patterns = {
            "time": ["check calendar", "set reminder"],
            "weather": ["forecast", "clothes recommendation"],
            "search": ["more details", "narrow search"],
            "code": ["test", "explain", "optimize"],
            "memory": ["what else remember", "list important"],
            "system": ["check status", "performance"],
        }

    def add_context(self, query: str):
        """Add to context history"""
        self.context_history.append(
            {
                "query": query.lower(),
                "timestamp": time.time(),
            }
        )

        # Keep last 10
        if len(self.context_history) > 10:
            self.context_history = self.context_history[-10:]

    def get_suggestions(self) -> list:
        """Get contextual suggestions"""
        if not self.context_history:
            return []

        last = self.context_history[-1]["query"]
        suggestions = []

        for key, values in self.suggestion_patterns.items():
            if key in last:
                suggestions.extend(values)

        return suggestions[:3]

    def clear(self):
        """Clear context"""
        self.context_history = []


# Global instance
_context_suggestions = None


def get_context_suggestions() -> ContextSuggestions:
    global _context_suggestions
    if _context_suggestions is None:
        _context_suggestions = ContextSuggestions()
    return _context_suggestions


if __name__ == "__main__":
    # Test
    suggestions = ContextSuggestions()

    suggestions.add_context("what time is it")
    print(f"After time query: {suggestions.get_suggestions()}")

    suggestions.add_context("weather today")
    print(f"After weather: {suggestions.get_suggestions()}")

    suggestions.add_context("write python code")
    print(f"After code: {suggestions.get_suggestions()}")
