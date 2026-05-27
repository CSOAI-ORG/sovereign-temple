#!/usr/bin/env python3
"""
JARVIS-MEOK Bridge - Real-time communication between JARVIS and MEOK
Writes execution logs that MEOK UI can read and display
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

BRIDGE_DIR = Path("/Users/nicholas/clawd/jarvis-memory")
BRIDGE_DIR.mkdir(exist_ok=True)


class JarvisMEOKBridge:
    """Bridge to sync JARVIS state with MEOK UI"""

    def __init__(self):
        self.status_file = BRIDGE_DIR / "jarvis-status.json"
        self.log_file = BRIDGE_DIR / "execution-log.json"
        self.state_file = BRIDGE_DIR / "jarvis-state.json"

    def update_status(self, status, progress=0, current_action="", details=None):
        """Update JARVIS status for MEOK to read"""
        data = {
            "status": status,  # idle, thinking, speaking, executing, error
            "progress": progress,  # 0-100
            "current_action": current_action,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.status_file.write_text(json.dumps(data, indent=2))
        return data

    def log_execution(self, action, command, output=None, error=None):
        """Log an execution for MEOK dashboard"""
        log_entry = {
            "id": int(time.time() * 1000),
            "action": action,
            "command": command,
            "output": output[:500] if output else None,
            "error": error[:200] if error else None,
            "timestamp": datetime.now().isoformat(),
        }

        # Read existing logs
        logs = []
        if self.log_file.exists():
            try:
                logs = json.loads(self.log_file.read_text())
            except:
                logs = []

        # Add new entry (keep last 50)
        logs.append(log_entry)
        logs = logs[-50:]

        self.log_file.write_text(json.dumps(logs, indent=2))
        return log_entry

    def set_state(self, state_name, **kwargs):
        """Set JARVIS state (thinking, speaking, idle, etc)"""
        data = {
            "state": state_name,
            "brain_active": kwargs.get("brain_active", ""),
            "model": kwargs.get("model", ""),
            "emotion": kwargs.get("emotion", "neutral"),
            "consciousness_level": kwargs.get("consciousness_level", 0.5),
            "last_update": datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(data, indent=2))
        return data

    def get_status(self):
        """Get current status for MEOK to read"""
        if self.status_file.exists():
            try:
                return json.loads(self.status_file.read_text())
            except:
                pass
        return {"status": "idle", "progress": 0, "current_action": ""}

    def get_logs(self, limit=10):
        """Get recent execution logs"""
        if self.log_file.exists():
            try:
                logs = json.loads(self.log_file.read_text())
                return logs[-limit:]
            except:
                pass
        return []


# Global bridge instance
bridge = JarvisMEOKBridge()

# Test it
if __name__ == "__main__":
    print("🧪 Testing JARVIS-MEOK Bridge")
    print("=" * 40)

    # Update status
    bridge.update_status("executing", 75, "Running command", {"command": "ls -la"})
    print(f"Status: {bridge.get_status()}")

    # Log execution
    bridge.log_execution("open_terminal", "echo test", "test output")
    print(f"Logs: {bridge.get_logs()}")

    # Set state
    bridge.set_state(
        "thinking", brain_active="qwen3.5:35b", model="qwen3.5:35b", emotion="focused"
    )
    print(f"State set")

    print("\n✅ Bridge ready!")
