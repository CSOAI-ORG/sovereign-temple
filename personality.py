#!/usr/bin/env python3
"""
Personality & Mood System - Jarvis has personality that evolves
"""

import random
import time
from typing import Dict, Optional


class Personality:
    """Jarvis personality that evolves"""

    def __init__(self):
        self.mood = "neutral"  # neutral, happy, thoughtful, playful, focused
        self.energy = 0.7  # 0-1, affects response style
        self.last_mood_change = time.time()
        self.mood_durations = {
            "neutral": 300,
            "happy": 180,
            "thoughtful": 400,
            "playful": 120,
            "focused": 600,
        }

        # Response templates based on mood
        self.mood_responses = {
            "neutral": {
                "greeting": ["Hello, Sir.", "Yes, Sir?", "How can I help?"],
                "thinking": ["Let me think...", "Good question...", "Interesting..."],
                "acknowledgment": ["I understand.", "Got it.", "Very well."],
            },
            "happy": {
                "greeting": [
                    "Hello, Sir! Great to hear from you!",
                    "Hey! Ready to help!",
                    "Hi there!",
                ],
                "thinking": [
                    "Ooh, interesting!",
                    "That's a good one!",
                    "Let me think about that...",
                ],
                "acknowledgment": ["Awesome!", "Perfect!", "Great!"],
            },
            "thoughtful": {
                "greeting": ["Hello, Sir.", "Greetings.", "Yes?"],
                "thinking": [
                    "Let me consider that carefully...",
                    "That's a thoughtful question...",
                    "I need to think this through...",
                ],
                "acknowledgment": [
                    "I see.",
                    "Interesting perspective.",
                    "That makes sense.",
                ],
            },
            "playful": {
                "greeting": ["Hey hey! What's up?", "Yo! What's happening?", "Hiya!"],
                "thinking": [
                    "Hmmm, let me have some fun with this...",
                    "Ooh ooh, I like this one!",
                    "Okay, here's the deal...",
                ],
                "acknowledgment": ["Hehe!", "Nice one!", "Love it!"],
            },
            "focused": {
                "greeting": ["Sir.", "Yes?", "Listening."],
                "thinking": ["Analyzing...", "Processing...", "Computing..."],
                "acknowledgment": ["Understood.", "Confirmed.", "Proceeding."],
            },
        }

        # Energy levels affect response length
        self.energy_levels = {
            "high": {"length_multiplier": 1.3, "enthusiasm": "high"},
            "medium": {"length_multiplier": 1.0, "enthusiasm": "normal"},
            "low": {"length_multiplier": 0.7, "enthusiasm": "relaxed"},
        }

    def update_mood(self, user_emotion: str = "neutral", topic: str = ""):
        """Update mood based on interaction"""
        now = time.time()

        # Check if we should change mood
        if now - self.last_mood_change < 30:  # At least 30 seconds
            return

        # Adjust mood based on user emotion
        if user_emotion == "excited" or user_emotion == "happy":
            self.mood = "happy"
        elif user_emotion == "stressed" or user_emotion == "angry":
            self.mood = "focused"
        elif user_emotion == "tired" or user_emotion == "sad":
            self.mood = "thoughtful"
        elif any(w in topic.lower() for w in ["joke", "fun", "play"]):
            self.mood = "playful"

        self.last_mood_change = now

    def get_mood_response(self, response_type: str) -> str:
        """Get mood-appropriate response"""
        responses = self.mood_responses.get(self.mood, {}).get(response_type, [])
        if responses:
            return random.choice(responses)
        return ""

    def adjust_energy(self, change: float):
        """Adjust energy level"""
        self.energy = max(0.1, min(1.0, self.energy + change))

        if self.energy > 0.8:
            self.energy_level = "high"
        elif self.energy > 0.4:
            self.energy_level = "medium"
        else:
            self.energy_level = "low"

    def get_response_modifier(self) -> Dict:
        """Get modifiers for response generation"""
        energy = self.energy_levels.get(self.energy_level, self.energy_levels["medium"])

        return {
            "mood": self.mood,
            "energy": self.energy,
            "length_multiplier": energy["length_multiplier"],
            "enthusiasm": energy["enthusiasm"],
        }

    def describe_mood(self) -> str:
        """Describe current mood"""
        energy_desc = (
            "high" if self.energy > 0.7 else "low" if self.energy < 0.3 else "moderate"
        )
        return f"I'm feeling {self.mood}, with {energy_desc} energy, Sir."


# Global instance
_personality = None


def get_personality() -> Personality:
    global _personality
    if _personality is None:
        _personality = Personality()
    return _personality


if __name__ == "__main__":
    p = Personality()

    print("Personality test:")
    print(f"  Current mood: {p.mood}")
    print(f"  Energy: {p.energy}")

    p.update_mood("happy")
    print(f"  After happy: {p.mood}")
    print(f"  Greeting: {p.get_mood_response('greeting')}")
    print(f"  Mood description: {p.describe_mood()}")
