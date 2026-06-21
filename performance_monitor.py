#!/usr/bin/env python3
"""
Performance Monitor - Track Jarvis performance metrics
"""

import time
import json
import threading
from typing import Dict, List
from collections import deque


class PerformanceMonitor:
    """Track and report performance metrics"""

    def __init__(self):
        self.metrics = {
            "response_times": deque(maxlen=50),
            "transcription_times": deque(maxlen=50),
            "tts_times": deque(maxlen=50),
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": [],
            "conversations": 0,
            "total_words_processed": 0,
        }
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record_response_time(self, duration: float):
        with self._lock:
            self.metrics["response_times"].append(duration)

    def record_transcription_time(self, duration: float):
        with self._lock:
            self.metrics["transcription_times"].append(duration)

    def record_tts_time(self, duration: float):
        with self._lock:
            self.metrics["tts_times"].append(duration)

    def record_cache_hit(self):
        with self._lock:
            self.metrics["cache_hits"] += 1

    def record_cache_miss(self):
        with self._lock:
            self.metrics["cache_misses"] += 1

    def record_error(self, error: str):
        with self._lock:
            self.metrics["errors"].append(
                {
                    "error": error,
                    "timestamp": time.time(),
                }
            )
            # Keep only last 10 errors
            if len(self.metrics["errors"]) > 10:
                self.metrics["errors"] = self.metrics["errors"][-10:]

    def increment_conversations(self):
        with self._lock:
            self.metrics["conversations"] += 1

    def add_words(self, count: int):
        with self._lock:
            self.metrics["total_words_processed"] += count

    def get_stats(self) -> Dict:
        with self._lock:
            uptime = time.time() - self._start_time

            # Calculate averages
            avg_response = 0
            if self.metrics["response_times"]:
                avg_response = sum(self.metrics["response_times"]) / len(
                    self.metrics["response_times"]
                )

            avg_transcription = 0
            if self.metrics["transcription_times"]:
                avg_transcription = sum(self.metrics["transcription_times"]) / len(
                    self.metrics["transcription_times"]
                )

            avg_tts = 0
            if self.metrics["tts_times"]:
                avg_tts = sum(self.metrics["tts_times"]) / len(
                    self.metrics["tts_times"]
                )

            # Cache hit rate
            total_cache = self.metrics["cache_hits"] + self.metrics["cache_misses"]
            cache_hit_rate = (
                (self.metrics["cache_hits"] / total_cache * 100)
                if total_cache > 0
                else 0
            )

            return {
                "uptime_seconds": int(uptime),
                "conversations": self.metrics["conversations"],
                "words_processed": self.metrics["total_words_processed"],
                "avg_response_time_ms": int(avg_response * 1000),
                "avg_transcription_time_ms": int(avg_transcription * 1000),
                "avg_tts_time_ms": int(avg_tts * 1000),
                "cache_hit_rate_percent": round(cache_hit_rate, 1),
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"],
                "recent_errors": len(self.metrics["errors"]),
            }

    def get_report(self) -> str:
        """Get human-readable performance report"""
        stats = self.get_stats()

        lines = [
            "📊 Performance Report:",
            f"  Uptime: {stats['uptime_seconds']}s",
            f"  Conversations: {stats['conversations']}",
            f"  Words processed: {stats['words_processed']}",
            "",
            "⏱️ Average Times:",
            f"  Response: {stats['avg_response_time_ms']}ms",
            f"  Transcription: {stats['avg_transcription_time_ms']}ms",
            f"  TTS: {stats['avg_tts_time_ms']}ms",
            "",
            "💾 Cache:",
            f"  Hit rate: {stats['cache_hit_rate_percent']}%",
            f"  Hits: {stats['cache_hits']} | Misses: {stats['cache_misses']}",
            "",
            f"  Errors: {stats['recent_errors']}",
        ]

        return "\n".join(lines)

    def save_stats(self, filepath: str = "/tmp/jarvis_performance.json"):
        """Save stats to file"""
        stats = self.get_stats()
        stats["timestamp"] = time.time()

        try:
            with open(filepath, "w") as f:
                json.dump(stats, f, indent=2)
        except:
            pass


# Global instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    return _performance_monitor


if __name__ == "__main__":
    # Test
    monitor = PerformanceMonitor()

    # Simulate some metrics
    for i in range(10):
        monitor.record_response_time(1.2 + i * 0.1)

    monitor.increment_conversations()
    monitor.add_words(500)
    monitor.record_cache_hit()
    monitor.record_cache_hit()
    monitor.record_cache_miss()

    print(monitor.get_report())
