#!/usr/bin/env python3
"""
Computer Use Bridge - Desktop Automation for SOV3
Enables AI to: capture screen, click, type, hotkey, and automate desktop
macOS focused with fallback for other platforms
"""

import os
import time
import subprocess
import base64
from typing import Dict, List, Optional, Any, Tuple
import logging

log = logging.getLogger("computer-use")


class ComputerUseBridge:
    """
    Desktop automation bridge
    Capabilities: Screenshot, click, type, hotkey, window management
    """

    def __init__(self):
        self.platform = "macos"
        self._setup()

    def _setup(self):
        """Check availability and permissions"""
        # Check for screenshot capability
        try:
            subprocess.run(
                ["screencapture", "--version"], capture_output=True, check=True
            )
            self.screenshot_available = True
        except:
            log.warning("screencapture not available")
            self.screenshot_available = False

        # Check for automation permissions
        try:
            import pyautogui

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            self.pyautogui_available = True
            log.info("✅ pyautogui available")
        except ImportError:
            log.warning("pyautogui not installed: pip install pyautogui")
            self.pyautogui_available = False

    def screenshot(self, path: str = None) -> Dict:
        """Capture screen and return base64 or save to file"""
        if not self.screenshot_available:
            return {"error": "Screenshot not available on this system"}

        if path is None:
            path = f"/tmp/screenshot_{int(time.time())}.png"

        try:
            # macOS screenshot
            result = subprocess.run(
                ["screencapture", "-x", path],  # -x for no sound
                capture_output=True,
                check=True,
            )

            # Read and encode
            with open(path, "rb") as f:
                img_data = f.read()
                img_b64 = base64.b64encode(img_data).decode("utf-8")

            return {
                "success": True,
                "path": path,
                "size_bytes": len(img_data),
                "base64": img_b64[:100] + "...",  # Truncated for display
                "full_base64": img_b64,  # Full data
            }
        except Exception as e:
            return {"error": str(e)}

    def click(self, x: int = None, y: int = None, button: str = "left") -> Dict:
        """Click at coordinates (or current position if None)"""
        if not self.pyautogui_available:
            return {"error": "pyautogui not available"}

        try:
            import pyautogui

            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)

            return {
                "success": True,
                "action": f"click at ({x}, {y}) with {button} button",
            }
        except Exception as e:
            return {"error": str(e)}

    def double_click(self, x: int = None, y: int = None) -> Dict:
        """Double click at coordinates"""
        if not self.pyautogui_available:
            return {"error": "pyautogui not available"}

        try:
            import pyautogui

            if x is not None and y is not None:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.doubleClick()
            return {"success": True, "action": "double click"}
        except Exception as e:
            return {"error": str(e)}

    def right_click(self, x: int = None, y: int = None) -> Dict:
        """Right click at coordinates"""
        return self.click(x, y, button="right")

    def move_to(self, x: int, y: int, duration: float = 0.5) -> Dict:
        """Move mouse to coordinates with optional duration"""
        if not self.pyautogui_available:
            return {"error": "pyautogui not available"}

        try:
            import pyautogui

            pyautogui.moveTo(x, y, duration=duration)
            return {"success": True, "action": f"moved to ({x}, {y})"}
        except Exception as e:
            return {"error": str(e)}

    def type(self, text: str, interval: float = 0.05) -> Dict:
        """Type text with optional interval between keys"""
        if not self.pyautogui_available:
            return {"error": "pyautogui not available"}

        try:
            import pyautogui

            pyautogui.write(text, interval=interval)
            return {"success": True, "action": f"typed '{text[:50]}...'"}
        except Exception as e:
            return {"error": str(e)}

    def hotkey(self, *keys) -> Dict:
        """Press hotkey combination (e.g., 'command', 'c')"""
        if not self.pyautogui_available:
            return {"error": "pyautogui not available"}

        try:
            import pyautogui

            pyautogui.hotkey(*keys)
            return {"success": True, "action": f"pressed {'+'.join(keys)}"}
        except Exception as e:
            return {"error": str(e)}

    def scroll(self, clicks: int) -> Dict:
        """Scroll up or down by number of clicks"""
        if not self.pyautogui_available:
            return {"error": "pyautogui not available"}

        try:
            import pyautogui

            pyautogui.scroll(clicks)
            return {"success": True, "action": f"scrolled {clicks} clicks"}
        except Exception as e:
            return {"error": str(e)}

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions"""
        if not self.pyautogui_available:
            return (1920, 1080)  # Default
        import pyautogui

        return pyautogui.size()

    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position"""
        if not self.pyautogui_available:
            return (0, 0)
        import pyautogui

        return pyautogui.position()

    def get_window_list(self) -> List[Dict]:
        """Get list of open windows (macOS)"""
        try:
            # Use AppleScript to get window list
            script = """
            tell application "System Events"
                set windowList to {}
                repeat with proc in (every process whose background only is false)
                    try
                        set procName to name of proc
                        set winList to windows of proc
                        repeat with w in winList
                            set winName to name of w
                            set end of windowList to {procName, winName}
                        end repeat
                    end try
                end repeat
                return windowList
            end tell
            """
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )

            windows = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split(", ")
                if len(parts) >= 2:
                    windows.append({"app": parts[0], "window": parts[1]})

            return windows
        except Exception as e:
            return [{"error": str(e)}]

    def activate_app(self, app_name: str) -> Dict:
        """Bring app to foreground"""
        try:
            subprocess.run(
                ["osascript", "-e", f'activate app "{app_name}"'], check=True
            )
            return {"success": True, "action": f"activated {app_name}"}
        except Exception as e:
            return {"error": str(e)}

    def execute_automation(self, actions: List[Dict]) -> Dict:
        """Execute a sequence of automation actions"""
        results = []

        for action in actions:
            action_type = action.get("action", "")

            if action_type == "screenshot":
                results.append(self.screenshot())

            elif action_type == "click":
                results.append(self.click(action.get("x"), action.get("y")))

            elif action_type == "type":
                results.append(self.type(action.get("text", "")))

            elif action_type == "hotkey":
                keys = action.get("keys", [])
                results.append(self.hotkey(*keys))

            elif action_type == "scroll":
                results.append(self.scroll(action.get("clicks", 0)))

            elif action_type == "wait":
                time.sleep(action.get("seconds", 1))
                results.append({"success": True, "action": "waited"})

            else:
                results.append({"error": f"Unknown action: {action_type}"})

        return {"results": results, "total": len(results)}


# Global instance
_computer_use: Optional[ComputerUseBridge] = None


def get_computer_use() -> ComputerUseBridge:
    global _computer_use
    if _computer_use is None:
        _computer_use = ComputerUseBridge()
    return _computer_use


if __name__ == "__main__":
    comp = get_computer_use()
    print(f"Screen size: {comp.get_screen_size()}")
    print(f"Cursor: {comp.get_cursor_position()}")
    print(f"Windows: {comp.get_window_list()[:5]}")

    # Test screenshot
    print("\n=== Screenshot Test ===")
    result = comp.screenshot()
    print(f"Screenshot: {result.get('size_bytes', 'error')} bytes")
