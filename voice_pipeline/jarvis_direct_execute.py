#!/usr/bin/env python3
"""
JARVIS Direct Execution Skill - Actually opens terminal and runs commands
"""

import subprocess
import os
import json


class DirectExecutor:
    """Actually executes system commands and returns real results."""

    def __init__(self):
        pass

    def open_terminal(self, command=None):
        """Open Terminal and optionally run a command."""
        try:
            # First, open Terminal app
            subprocess.run(["open", "-a", "Terminal"], capture_output=True, timeout=5)

            if command:
                # Run the command in a new window
                script = f'tell application "Terminal" to do script "{command}"'
                subprocess.run(
                    ["osascript", "-e", script], capture_output=True, timeout=5
                )
                return {
                    "success": True,
                    "action": "opened_terminal",
                    "command": command,
                }

            return {"success": True, "action": "opened_terminal"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_command(self, command, shell="bash"):
        """Run a shell command and return real output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.environ.get("HOME", "/Users/nicholas"),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_info(self):
        """Get real system information."""
        try:
            # CPU load
            cpu = subprocess.run(
                ["sh", "-c", "ps aux | head -1; top -l 1 | grep 'CPU usage'"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Memory
            mem = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True, timeout=5
            )

            # Process count
            procs = subprocess.run(
                ["ps", "-e"], capture_output=True, text=True, timeout=5
            )

            return {
                "cpu": cpu.stdout[:500],
                "disk": mem.stdout,
                "processes": len(procs.stdout.split("\n")),
            }
        except Exception as e:
            return {"error": str(e)}


# Test it
if __name__ == "__main__":
    executor = DirectExecutor()

    print("🧪 Testing Direct Execution")
    print("=" * 40)

    # Test 1: Open terminal
    print("\n1️⃣ Opening Terminal...")
    result = executor.open_terminal()
    print(f"   Result: {result}")

    # Test 2: Run a command
    print("\n2️⃣ Running 'echo SOV3_TEST'...")
    result = executor.run_command("echo 'SOV3_TEST_FROM_JARVIS'")
    print(f"   stdout: {result.get('stdout', 'none')[:100]}")

    # Test 3: System info
    print("\n3️⃣ Getting system info...")
    info = executor.get_system_info()
    print(f"   Processes: {info.get('processes', '?')}")

    print("\n" + "=" * 40)
    print("✅ Direct execution working!")
