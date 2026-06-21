#!/usr/bin/env python3
"""
JARVIS Emotional Intelligence Upgrade
Real-time voice emotion → adaptive responses, emotional memory, empathy engine.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

EMOTION_LOG = Path("/Users/nicholas/clawd/jarvis-memory/emotion_log.json")
EMOTION_LOG.parent.mkdir(exist_ok=True)


class EmotionalIntelligence:
    """
    Tracks Nick's emotional patterns over time and adapts JARVIS behavior:
    - Voice tone analysis → emotion detection
    - Emotional memory → patterns over days/weeks
    - Adaptive responses → JARVIS adjusts tone, pace, content
    - Empathy engine → recognizes distress, offers support
    """

    def __init__(self):
        self.emotion_history = self._load_history()
        self.current_emotion = "neutral"
        self.emotion_streaks = {}  # emotion -> count of consecutive occurrences

    def _load_history(self) -> List[Dict]:
        if EMOTION_LOG.exists():
            try:
                return json.loads(EMOTION_LOG.read_text())
            except:
                return []
        return []

    def _save_history(self):
        # Keep last 1000 entries
        if len(self.emotion_history) > 1000:
            self.emotion_history = self.emotion_history[-1000:]
        EMOTION_LOG.write_text(json.dumps(self.emotion_history, indent=2, default=str))

    def record_emotion(self, emotion: str, intensity: float = 0.5, context: str = ""):
        """Record an emotional detection."""
        entry = {
            "emotion": emotion,
            "intensity": intensity,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.emotion_history.append(entry)
        self.current_emotion = emotion
        self._save_history()

    def get_emotional_pattern(self, hours: int = 24) -> Dict[str, Any]:
        """Get emotional patterns over the last N hours."""
        cutoff = time.time() - (hours * 3600)
        recent = [
            e
            for e in self.emotion_history
            if datetime.fromisoformat(e["timestamp"]).timestamp() > cutoff
        ]

        if not recent:
            return {"pattern": "no_data", "dominant_emotion": "unknown"}

        # Count emotions
        emotion_counts = {}
        for e in recent:
            emotion_counts[e["emotion"]] = emotion_counts.get(e["emotion"], 0) + 1

        dominant = max(emotion_counts, key=emotion_counts.get)
        avg_intensity = sum(e["intensity"] for e in recent) / len(recent)

        return {
            "pattern": "stable" if len(emotion_counts) <= 2 else "variable",
            "dominant_emotion": dominant,
            "emotion_distribution": emotion_counts,
            "average_intensity": round(avg_intensity, 2),
            "sample_size": len(recent),
        }

    def get_adaptive_response(self, user_emotion: str) -> Dict[str, Any]:
        """Get adaptive response parameters based on user emotion."""
        adaptations = {
            "excited": {
                "voice": "default",
                "pace": "fast",
                "tone": "enthusiastic",
                "content": "match_energy",
                "prompt_modifier": "User is excited. Match their energy, be enthusiastic and supportive.",
            },
            "stressed": {
                "voice": "calm",
                "pace": "slow",
                "tone": "soothing",
                "content": "simplify",
                "prompt_modifier": "User is stressed. Be calm, gentle, and supportive. Simplify responses. Offer help.",
            },
            "tired": {
                "voice": "calm",
                "pace": "slow",
                "tone": "gentle",
                "content": "brief",
                "prompt_modifier": "User is tired. Keep responses brief and gentle. Offer to handle things for them.",
            },
            "sad": {
                "voice": "warm",
                "pace": "slow",
                "tone": "empathetic",
                "content": "supportive",
                "prompt_modifier": "User seems sad. Be warm, empathetic, and supportive. Listen more than speak.",
            },
            "neutral": {
                "voice": "default",
                "pace": "normal",
                "tone": "professional",
                "content": "normal",
                "prompt_modifier": "",
            },
        }

        return adaptations.get(user_emotion, adaptations["neutral"])

    def get_empathy_prompt(self, user_emotion: str, context: str = "") -> str:
        """Generate an empathy-aware system prompt modifier."""
        adaptation = self.get_adaptive_response(user_emotion)
        prompt = adaptation["prompt_modifier"]

        # Check for emotional patterns
        pattern = self.get_emotional_pattern(24)
        if pattern.get("dominant_emotion") in ("stressed", "sad", "tired"):
            prompt += f" Note: User has been {pattern['dominant_emotion']} for the last 24 hours. Be extra supportive."

        # Check for emotional streaks
        recent = self.emotion_history[-5:]
        if recent and all(e["emotion"] == user_emotion for e in recent):
            prompt += f" This is the {len(recent)}th time in a row they've been {user_emotion}."

        return prompt

    def get_daily_emotional_report(self) -> Dict[str, Any]:
        """Generate a daily emotional summary."""
        today = datetime.now(timezone.utc).date().isoformat()
        today_entries = [
            e for e in self.emotion_history if e["timestamp"].startswith(today)
        ]

        if not today_entries:
            return {"date": today, "status": "no_data"}

        emotion_counts = {}
        for e in today_entries:
            emotion_counts[e["emotion"]] = emotion_counts.get(e["emotion"], 0) + 1

        return {
            "date": today,
            "total_interactions": len(today_entries),
            "emotion_distribution": emotion_counts,
            "dominant_emotion": max(emotion_counts, key=emotion_counts.get),
            "average_intensity": round(
                sum(e["intensity"] for e in today_entries) / len(today_entries), 2
            ),
        }
