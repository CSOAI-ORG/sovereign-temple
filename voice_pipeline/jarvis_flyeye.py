#!/usr/bin/env python3
"""
MEOK Fly Eye — Camera + Screen Awareness System
Captures screen, webcam, and provides visual context to JARVIS/SOV3.

Modes:
1. Screen capture — sees what you see
2. Webcam — sees you
3. Combined — sees both
4. Continuous monitoring — watches for changes
"""

import os
import sys
import time
import json
import base64
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

SOV3_URL = "http://localhost:3101"
OLLAMA_URL = "http://localhost:11434"
CAPTURE_DIR = Path("/Users/nicholas/clawd/jarvis-memory/flyeye")
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)


class FlyEye:
    """Visual awareness system for JARVIS."""

    def __init__(self):
        self.active = False
        self.last_capture = None
        self.capture_count = 0
        self.monitoring = False

    def capture_screen(self, region: str = None) -> Optional[str]:
        """
        Capture the current screen as base64 image.
        region: None = full screen, or "x,y,w,h"
        Returns base64-encoded JPEG string.
        """
        try:
            tmp_path = str(CAPTURE_DIR / f"screen_{int(time.time())}.jpg")

            if region:
                x, y, w, h = region.split(",")
                cmd = ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", tmp_path]
            else:
                cmd = ["screencapture", "-x", tmp_path]

            subprocess.run(cmd, capture_output=True, timeout=10)

            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")

                self.last_capture = {
                    "type": "screen",
                    "timestamp": datetime.now().isoformat(),
                    "path": tmp_path,
                    "size": os.path.getsize(tmp_path),
                }
                self.capture_count += 1

                # Clean up old captures (keep last 10)
                self._cleanup_captures()

                return img_data

        except Exception as e:
            print(f"[FlyEye] Screen capture failed: {e}")

        return None

    def capture_webcam(self, duration: int = 1) -> Optional[str]:
        """
        Capture from webcam using imagesnap.
        Returns base64-encoded JPEG string.
        """
        try:
            tmp_path = str(CAPTURE_DIR / f"webcam_{int(time.time())}.jpg")

            # Check if imagesnap is installed
            if not self._has_imagesnap():
                print("[FlyEye] imagesnap not found. Install: brew install imagesnap")
                return None

            cmd = ["imagesnap", "-w", str(duration), tmp_path]
            subprocess.run(cmd, capture_output=True, timeout=15)

            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")

                self.last_capture = {
                    "type": "webcam",
                    "timestamp": datetime.now().isoformat(),
                    "path": tmp_path,
                    "size": os.path.getsize(tmp_path),
                }
                self.capture_count += 1
                self._cleanup_captures()

                return img_data

        except Exception as e:
            print(f"[FlyEye] Webcam capture failed: {e}")

        return None

    def analyze_image(self, image_b64: str, query: str = None) -> str:
        """
        Send image to vision model for analysis.
        Uses Qwen3-VL via Ollama.
        """
        if not query:
            query = "Describe what you see in detail. What application is open? What is the user working on? Note any important text, UI elements, or context."

        try:
            # Save image temporarily for Ollama
            tmp_path = str(CAPTURE_DIR / f"analyze_{int(time.time())}.jpg")
            with open(tmp_path, "wb") as f:
                f.write(base64.b64decode(image_b64))

            # Use Ollama vision model
            import requests

            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": "qwen3-vl:235b-cloud",
                    "messages": [
                        {
                            "role": "user",
                            "content": query,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 512},
                },
                timeout=60,
            )

            if resp.status_code == 200:
                result = resp.json()
                analysis = result.get("message", {}).get("content", "")

                # Record to SOV3 memory
                self._record_visual_memory(query, analysis)

                # Clean up
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

                return analysis

        except Exception as e:
            print(f"[FlyEye] Image analysis failed: {e}")

        return "I couldn't analyze the image, Sir."

    def continuous_monitor(self, interval: int = 5, callback=None):
        """
        Continuously monitor screen for changes.
        Calls callback(screen_description) when significant change detected.
        """
        self.monitoring = True
        last_hash = None

        while self.monitoring:
            try:
                img_b64 = self.capture_screen()
                if img_b64:
                    # Simple change detection via hash
                    import hashlib

                    current_hash = hashlib.md5(img_b64.encode()).hexdigest()

                    if current_hash != last_hash:
                        last_hash = current_hash
                        if callback:
                            # Analyze what changed
                            analysis = self.analyze_image(
                                img_b64,
                                "What application is now active? What changed on screen?",
                            )
                            callback(analysis)

                    time.sleep(interval)

            except Exception as e:
                print(f"[FlyEye] Monitor error: {e}")
                time.sleep(interval)

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.monitoring = False

    def get_context(self) -> Dict:
        """Get current visual context."""
        # Get active app
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    """
                    tell application "System Events"
                        set frontApp to name of first application process whose frontmost is true
                        return frontApp
                    end tell
                """,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            active_app = result.stdout.strip()
        except:
            active_app = "Unknown"

        # Get window title
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    """
                    tell application "System Events"
                        set frontApp to first application process whose frontmost is true
                        set winName to name of front window of frontApp
                        return winName
                    end tell
                """,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            window_title = result.stdout.strip()
        except:
            window_title = ""

        return {
            "active_app": active_app,
            "window_title": window_title,
            "last_capture": self.last_capture,
            "total_captures": self.capture_count,
            "monitoring": self.monitoring,
        }

    def _has_imagesnap(self) -> bool:
        """Check if imagesnap is installed."""
        try:
            subprocess.run(["which", "imagesnap"], capture_output=True, timeout=3)
            return True
        except:
            return False

    def _cleanup_captures(self, keep: int = 10):
        """Remove old captures, keep only recent ones."""
        files = sorted(CAPTURE_DIR.glob("*.jpg"), key=lambda f: f.stat().st_mtime)
        for f in files[:-keep]:
            try:
                f.unlink()
            except:
                pass

    def _record_visual_memory(self, query: str, analysis: str):
        """Record visual analysis to SOV3 memory."""
        try:
            import requests

            requests.post(
                f"{SOV3_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "record_memory",
                        "arguments": {
                            "content": f"FlyEye saw: {analysis[:500]}",
                            "source_agent": "jarvis_flyeye",
                            "memory_type": "observation",
                            "tags": ["flyeye", "visual", "screen"],
                            "care_weight": 0.5,
                        },
                    },
                },
                timeout=5,
            )
        except:
            pass


# Global instance
flyeye = FlyEye()


if __name__ == "__main__":
    import sys

    fe = FlyEye()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "screen":
            print("📸 Capturing screen...")
            img = fe.capture_screen()
            if img:
                print(f"✅ Screen captured ({len(img)} bytes)")
                # Analyze
                print("🔍 Analyzing...")
                analysis = fe.analyze_image(img)
                print(f"\n{analysis}")
            else:
                print("❌ Capture failed")

        elif cmd == "webcam":
            print("📷 Capturing webcam...")
            img = fe.capture_webcam()
            if img:
                print(f"✅ Webcam captured ({len(img)} bytes)")
            else:
                print("❌ Capture failed")

        elif cmd == "context":
            ctx = fe.get_context()
            print(json.dumps(ctx, indent=2))

        elif cmd == "monitor":
            print("👁️  Fly Eye monitoring started (Ctrl+C to stop)")

            def on_change(desc):
                print(f"\n📺 Screen changed: {desc[:200]}")

            fe.continuous_monitor(interval=10, callback=on_change)

        else:
            print(f"Unknown command: {cmd}")
            print("Usage: flyeye.py [screen|webcam|context|monitor]")
    else:
        print("👁️  MEOK Fly Eye — Visual Awareness System")
        print("Usage: flyeye.py [screen|webcam|context|monitor]")
        print()
        ctx = fe.get_context()
        print(f"Active app: {ctx['active_app']}")
        print(f"Window: {ctx['window_title']}")
        print(f"Total captures: {ctx['total_captures']}")
