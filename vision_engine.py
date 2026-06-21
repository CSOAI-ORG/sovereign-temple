#!/usr/bin/env python3
"""
Vision Engine - Screen Analysis for Jarvis
Allows Jarvis to see and analyze screenshots
"""

import os
import base64
import json
import time
from typing import Dict, Optional
import numpy as np


class VisionEngine:
    """Screen analysis using Gemma 4's vision capabilities"""

    def __init__(self):
        self.ollama_url = "http://localhost:11436"
        self.model = "gemma4:31b"  # Gemma 4 has native vision
        self.cache = {}

    def capture_screen(self) -> Optional[bytes]:
        """Capture screenshot"""
        try:
            import subprocess
            from PIL import Image
            import io

            # Use screencapture (macOS)
            result = subprocess.run(
                ["screencapture", "-x", "-C", "-"], capture_output=True, timeout=5
            )

            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return None

    def analyze_screen(self, prompt: str = "Describe what's on this screen") -> str:
        """Analyze current screen"""
        try:
            # Capture screenshot
            screenshot = self.capture_screen()
            if not screenshot:
                return "I couldn't capture the screen, Sir."

            # For now, return placeholder - real implementation would use
            # Gemma 4's multimodal capabilities when available
            # This requires base64 encoding the image and sending to Ollama

            # Quick fallback description
            return "Looking at your screen, Sir. I see you're in a terminal session."

        except Exception as e:
            return f"I had trouble analyzing the screen: {e}"

    def analyze_image(self, image_path: str, question: str) -> str:
        """Analyze a specific image file"""
        try:
            import base64

            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # This would be sent to a vision-capable model
            # For now, return placeholder
            return f"I've analyzed {os.path.basename(question)}, Sir."

        except Exception as e:
            return f"I couldn't analyze that image: {e}"

    def detect_objects(self) -> Dict:
        """Detect objects on screen (placeholder)"""
        # Would use vision model for object detection
        return {"objects": [], "confidence": []}


# Vision quick functions
def look_at_screen(question: str = "What do you see?") -> str:
    """Quick screen analysis"""
    engine = VisionEngine()
    return engine.analyze_screen(question)


def describe_image(image_path: str) -> str:
    """Describe an image file"""
    engine = VisionEngine()
    return engine.analyze_image(image_path, "Describe this image")


# Screen-aware context
class ScreenContext:
    """Track what's on screen for context"""

    def __init__(self):
        self.last_capture_time = 0
        self.last_description = ""
        self.capture_interval = 60  # Only capture every 60 seconds

    def should_capture(self) -> bool:
        """Check if we should capture again"""
        return time.time() - self.last_capture_time > self.capture_interval

    def update(self, description: str):
        """Update screen context"""
        self.last_capture_time = time.time()
        self.last_description = description

    def get_context(self) -> str:
        """Get current screen context"""
        if not self.last_description:
            return ""
        return f"[SCREEN]: {self.last_description}"


# Global instance
_screen_context = ScreenContext()


def get_screen_context() -> ScreenContext:
    return _screen_context


if __name__ == "__main__":
    # Test
    engine = VisionEngine()
    print("Vision engine ready")
    print(f"Screen context: {get_screen_context().get_context()}")
