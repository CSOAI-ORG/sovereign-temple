"""
Screen Awareness Engine — Continuous screenshot + OCR for SOV3
================================================================
Takes screenshots every N seconds, runs OCR, and feeds context
to the character so it can see what you're doing.

This is how the AI becomes aware of your screen — not just text chat.

Uses SOV3's existing capture_screenshot + analyze_screenshot tools.
"""

import asyncio
import json
import logging
import time
import subprocess
import tempfile
import base64
import os
import requests

log = logging.getLogger("screen_awareness")

SOV3_URL = "http://localhost:3101"
OLLAMA_URL = "http://localhost:11434"
CAPTURE_INTERVAL = 30  # seconds between captures
HISTORY_SIZE = 5       # keep last N screen descriptions


class ScreenAwareness:
    """Continuous screen monitoring for AI context awareness."""

    def __init__(self):
        self.history: list = []
        self.running = False
        self.current_context = ""

    def capture_screenshot(self) -> str:
        """Capture screen and return base64 PNG."""
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            subprocess.run(
                ["screencapture", "-x", "-C", tmp.name],
                check=True, timeout=5,
            )
            with open(tmp.name, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            os.unlink(tmp.name)
            return b64
        except Exception as e:
            log.error(f"Screenshot failed: {e}")
            return ""

    def analyze_with_gemma4(self, screenshot_b64: str) -> str:
        """Send screenshot to Gemma 4 E4B for visual understanding."""
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json={
                "model": "gemma4:e4b",
                "messages": [{
                    "role": "user",
                    "content": "Describe what you see on this screen in 2-3 sentences. Focus on: what app is open, what the user is doing, any important text or UI elements.",
                    "images": [screenshot_b64],
                }],
                "stream": False,
                "think": False,
                "options": {"num_predict": 150, "temperature": 0.3},
            }, timeout=60)
            return r.json().get("message", {}).get("content", "")
        except Exception as e:
            return f"Vision error: {e}"

    def get_context(self) -> str:
        """Get current screen context for the character."""
        if not self.history:
            return "No screen context available yet."
        return f"Recent screen activity: {self.history[-1]}"

    async def run_continuous(self, interval: int = None):
        """Run continuous screen capture loop."""
        interval = interval or CAPTURE_INTERVAL
        self.running = True
        log.info(f"Screen awareness started (every {interval}s)")

        while self.running:
            try:
                b64 = self.capture_screenshot()
                if b64:
                    description = self.analyze_with_gemma4(b64)
                    if description and "error" not in description.lower()[:10]:
                        self.history.append({
                            "time": time.strftime("%H:%M:%S"),
                            "description": description,
                        })
                        self.current_context = description
                        # Keep history bounded
                        if len(self.history) > HISTORY_SIZE:
                            self.history = self.history[-HISTORY_SIZE:]

                        log.info(f"Screen: {description[:80]}...")

                        # Store as memory in SOV3
                        try:
                            requests.post(f"{SOV3_URL}/mcp", json={
                                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {
                                    "name": "record_memory",
                                    "arguments": {
                                        "content": f"Screen context at {time.strftime('%H:%M')}: {description}",
                                        "tags": ["screen", "visual_context", time.strftime("%Y-%m-%d")],
                                        "importance": 0.3,
                                    },
                                },
                            }, timeout=10)
                        except Exception:
                            pass

            except Exception as e:
                log.error(f"Screen capture error: {e}")

            await asyncio.sleep(interval)

    def stop(self):
        self.running = False


# Global instance
_screen = None

def get_screen_awareness() -> ScreenAwareness:
    global _screen
    if _screen is None:
        _screen = ScreenAwareness()
    return _screen


def register_screen_routes(app):
    """Register screen awareness API endpoints."""
    screen = get_screen_awareness()

    @app.get("/screen/context")
    async def screen_context():
        return {
            "current": screen.current_context,
            "history": screen.history[-3:],
            "running": screen.running,
        }

    @app.post("/screen/start")
    async def screen_start():
        if not screen.running:
            asyncio.create_task(screen.run_continuous())
        return {"status": "started"}

    @app.post("/screen/stop")
    async def screen_stop():
        screen.stop()
        return {"status": "stopped"}

    @app.post("/screen/capture")
    async def screen_capture_now():
        """Single capture + analyze."""
        b64 = screen.capture_screenshot()
        if not b64:
            return {"error": "Screenshot failed"}
        desc = screen.analyze_with_gemma4(b64)
        return {"description": desc, "timestamp": time.strftime("%H:%M:%S")}
