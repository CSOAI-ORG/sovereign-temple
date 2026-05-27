#!/usr/bin/env python3
"""
Comprehensive Error Handling & Recovery System
"""

import traceback
import time
import logging
from typing import Dict, Optional, Callable, Any
from functools import wraps
import queue
import threading


class ErrorRecovery:
    """Comprehensive error handling with automatic recovery"""

    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.max_history = 50
        self.retry_strategies = {}

        # Define retry strategies for different error types
        self.default_strategies = {
            "connection": {"retries": 3, "delay": 1.0, "backoff": 2.0},
            "timeout": {"retries": 2, "delay": 0.5, "backoff": 1.5},
            "memory": {"retries": 1, "delay": 0.1, "backoff": 1.0},
            "audio": {"retries": 3, "delay": 0.2, "backoff": 1.0},
            "model": {"retries": 2, "delay": 1.0, "backoff": 2.0},
            "unknown": {"retries": 1, "delay": 0.5, "backoff": 1.0},
        }

    def classify_error(self, error: Exception) -> str:
        """Classify error type"""
        error_str = str(error).lower()

        if any(w in error_str for w in ["connection", "network", "refused", "timeout"]):
            return "connection"
        if any(w in error_str for w in ["timeout", "timed out"]):
            return "timeout"
        if any(w in error_str for w in ["memory", "allocation", "oom"]):
            return "memory"
        if any(w in error_str for w in ["audio", "microphone", "speak", "sound"]):
            return "audio"
        if any(w in error_str for w in ["model", "ollama", "gemma", "inference"]):
            return "model"

        return "unknown"

    def record_error(self, error: Exception, context: str = ""):
        """Record error for analysis"""
        error_type = self.classify_error(error)

        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1

        self.error_history.append(
            {
                "error": str(error)[:200],
                "type": error_type,
                "context": context,
                "timestamp": time.time(),
            }
        )

        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

    def get_recovery_strategy(self, error_type: str) -> Dict:
        """Get recovery strategy for error type"""
        return self.default_strategies.get(
            error_type, self.default_strategies["unknown"]
        )

    def get_error_summary(self) -> str:
        """Get error summary"""
        if not self.error_counts:
            return "No errors recorded, Sir."

        lines = ["Error summary:"]
        for error_type, count in sorted(self.error_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {error_type}: {count} occurrences")

        return "\n".join(lines)

    def should_retry(self, error_type: str) -> bool:
        """Check if we should retry based on error frequency"""
        count = self.error_counts.get(error_type, 0)

        # Don't retry too many times
        if error_type == "connection" and count > 10:
            return False
        if error_type == "model" and count > 5:
            return False

        return True


class RobustFallbackChain:
    """Multiple fallback levels for reliability"""

    def __init__(self):
        self.fallbacks = []
        self.current_level = 0

    def add_fallback(self, name: str, func: Callable, *args, **kwargs):
        """Add a fallback function"""
        self.fallbacks.append(
            {
                "name": name,
                "func": func,
                "args": args,
                "kwargs": kwargs,
            }
        )

    def execute(self) -> Any:
        """Execute with fallback chain"""
        last_error = None

        for i, fallback in enumerate(self.fallbacks):
            try:
                result = fallback["func"](*fallback["args"], **fallback["kwargs"])
                if result:
                    return result
            except Exception as e:
                last_error = e
                continue

        return None


# Global error recovery
_error_recovery = ErrorRecovery()


def get_error_recovery() -> ErrorRecovery:
    return _error_recovery


def with_error_handling(error_type: str = "unknown", context: str = ""):
    """Decorator for error handling"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _error_recovery.record_error(e, f"{context}:{func.__name__}")
                raise

        return wrapper

    return decorator


# Audio error handling
class AudioErrorHandler:
    """Handle audio-related errors gracefully"""

    def __init__(self):
        self.mic_available = True
        self.speaker_available = True
        self.last_mic_error = None
        self.last_speaker_error = None

    def handle_mic_error(self, error: Exception) -> str:
        """Handle microphone errors"""
        self.mic_available = False
        self.last_mic_error = str(error)[:100]

        return "I'm having trouble with the microphone, Sir. Please check it and try again."

    def handle_speaker_error(self, error: Exception) -> str:
        """Handle speaker errors"""
        self.speaker_available = False
        self.last_speaker_error = str(error)[:100]

        return "I can't output audio right now, Sir. Check your speakers."

    def check_availability(self) -> Dict:
        """Check audio availability"""
        return {
            "microphone": self.mic_available,
            "speaker": self.speaker_available,
        }


# Global audio handler
_audio_handler = AudioErrorHandler()


def get_audio_handler() -> AudioErrorHandler:
    return _audio_handler


if __name__ == "__main__":
    # Test error recovery
    recovery = ErrorRecovery()

    class TestError(Exception):
        pass

    recovery.record_error(TestError("Test error"), "test_context")
    print(recovery.get_error_summary())

    # Test fallback chain
    chain = RobustFallbackChain()
    chain.add_fallback("first", lambda: None)
    chain.add_fallback("second", lambda: "success")
    result = chain.execute()
    print(f"Fallback result: {result}")
