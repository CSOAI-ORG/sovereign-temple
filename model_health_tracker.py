#!/usr/bin/env python3
"""
Model Health Tracker — Load balancer tuning for MEOKCLAW inference mesh.

Tracks per-model latency, error rates, and success rates to enable
adaptive routing decisions.
"""

import time
from collections import deque, defaultdict
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ModelHealth:
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latency_ms_history: deque = field(default_factory=lambda: deque(maxlen=100))
    last_failure_at: Optional[float] = None
    last_success_at: Optional[float] = None
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def p50_latency_ms(self) -> float:
        if not self.latency_ms_history:
            return 0.0
        sorted_latencies = sorted(self.latency_ms_history)
        n = len(sorted_latencies)
        if n % 2 == 1:
            return sorted_latencies[n // 2]
        return (sorted_latencies[n // 2 - 1] + sorted_latencies[n // 2]) / 2

    @property
    def p95_latency_ms(self) -> float:
        if not self.latency_ms_history:
            return 0.0
        sorted_latencies = sorted(self.latency_ms_history)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def health_score(self) -> float:
        """Composite health score (0.0 = unhealthy, 1.0 = perfect)."""
        if self.consecutive_failures >= 3:
            return 0.0
        score = self.success_rate
        # Deprioritize slow models
        if self.p95_latency_ms > 20000:  # > 20s
            score *= 0.7
        elif self.p95_latency_ms > 10000:  # > 10s
            score *= 0.85
        # Deprioritize models with recent failures
        if self.last_failure_at and self.last_success_at:
            if self.last_failure_at > self.last_success_at:
                score *= 0.8
        return max(0.0, min(1.0, score))

    def record_success(self, latency_ms: float):
        self.total_requests += 1
        self.successful_requests += 1
        self.latency_ms_history.append(latency_ms)
        self.last_success_at = time.time()
        self.consecutive_failures = 0

    def record_failure(self):
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure_at = time.time()
        self.consecutive_failures += 1


class ModelHealthTracker:
    """Tracks health for all models in the inference mesh."""

    def __init__(self):
        self._health: Dict[str, ModelHealth] = defaultdict(
            lambda: ModelHealth(model_id="unknown")
        )

    def get(self, model_id: str) -> ModelHealth:
        if model_id not in self._health:
            self._health[model_id] = ModelHealth(model_id=model_id)
        return self._health[model_id]

    def record_success(self, model_id: str, latency_ms: float):
        self.get(model_id).record_success(latency_ms)

    def record_failure(self, model_id: str):
        self.get(model_id).record_failure()

    def get_healthiest(self, model_ids: list) -> Optional[str]:
        """Return the healthiest model from a list of candidates."""
        if not model_ids:
            return None
        scored = [(mid, self.get(mid).health_score) for mid in model_ids]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def should_avoid(self, model_id: str) -> bool:
        """Check if a model should be avoided due to poor health."""
        return self.get(model_id).health_score < 0.3

    def summary(self) -> Dict[str, Any]:
        return {
            mid: {
                "success_rate": round(h.success_rate, 3),
                "p50_latency_ms": round(h.p50_latency_ms, 1),
                "p95_latency_ms": round(h.p95_latency_ms, 1),
                "health_score": round(h.health_score, 3),
                "total_requests": h.total_requests,
                "consecutive_failures": h.consecutive_failures,
            }
            for mid, h in self._health.items()
        }


# Singleton instance
_global_tracker: Optional[ModelHealthTracker] = None


def get_tracker() -> ModelHealthTracker:
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ModelHealthTracker()
    return _global_tracker
