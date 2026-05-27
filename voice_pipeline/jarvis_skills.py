#!/usr/bin/env python3
"""
JARVIS Skill Execution Framework
Web search, calendar, file ops, system commands, and more.
"""

import json
import os
import subprocess
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


class SkillExecutor:
    """Execute skills based on intent detection from user input."""

    def __init__(self):
        self.skills = {
            "web_search": self._web_search,
            "calendar": self._calendar,
            "file_search": self._file_search,
            "system_status": self._system_status,
            "memory_query": self._memory_query,
            "code_execution": self._code_execution,
            "email_check": self._email_check,
            "weather": self._weather,
            "open_terminal": self._open_terminal,
            "run_command": self._run_command,
            "system_execute": self._system_execute,
            "browse_web": self._browse_web,
            "edit_file": self._edit_file,
            "git_ops": self._git_ops,
        }

    def detect_intent(self, text: str) -> List[str]:
        """Detect which skills to execute based on user input."""
        lower = text.lower()
        intents = []

        # Web search
        if any(
            w in lower
            for w in [
                "search",
                "look up",
                "find",
                "what is",
                "who is",
                "latest",
                "news",
                "check online",
            ]
        ):
            intents.append("web_search")

        # Calendar
        if any(
            w in lower
            for w in [
                "calendar",
                "schedule",
                "appointment",
                "meeting",
                "what's today",
                "what do i have",
                "events",
            ]
        ):
            intents.append("calendar")

        # File search
        if any(
            w in lower
            for w in [
                "find file",
                "search files",
                "where is",
                "open file",
                "show me the file",
            ]
        ):
            intents.append("file_search")

        # System status
        if any(
            w in lower
            for w in [
                "system status",
                "health check",
                "how are systems",
                "is everything running",
                "status check",
            ]
        ):
            intents.append("system_status")

        # Memory query
        if any(
            w in lower
            for w in [
                "remember",
                "what did we",
                "earlier you said",
                "last time",
                "previous conversation",
            ]
        ):
            intents.append("memory_query")

        # Code execution
        if any(
            w in lower
            for w in [
                "run this",
                "execute",
                "test this",
                "run the code",
                "check if it works",
            ]
        ):
            intents.append("code_execution")

        # Email
        if any(
            w in lower
            for w in ["email", "mail", "inbox", "new messages", "check email"]
        ):
            intents.append("email_check")

        # Weather
        if any(
            w in lower
            for w in ["weather", "temperature", "rain", "forecast", "going to rain"]
        ):
            intents.append("weather")

        # Terminal/Command execution
        if any(
            w in lower
            for w in [
                "open terminal",
                "open a terminal",
                "run terminal",
                "open command",
                "open cmd",
                "execute command",
                "run command",
                "run script",
                "execute script",
                "run in terminal",
                "run this command",
                "open terminal and",
                "launch terminal",
            ]
        ):
            intents.append("open_terminal")

        # System execute (hidden execution)
        if any(
            w in lower
            for w in [
                "check processes",
                "show cpu",
                "show memory",
                "system info",
                "get system",
                "list processes",
                "what's running",
                "ps aux",
            ]
        ):
            intents.append("system_execute")

        # Browse web
        if any(
            w in lower
            for w in [
                "browse",
                "go to website",
                "open page",
                "visit site",
                "check website",
                "open url",
            ]
        ):
            intents.append("browse_web")

        # File editing
        if any(
            w in lower
            for w in [
                "edit file",
                "read file",
                "show file",
                "modify file",
                "open file",
                "search code",
                "find in code",
                "grep",
            ]
        ):
            intents.append("edit_file")

        # Git operations
        if any(
            w in lower
            for w in [
                "git diff",
                "git log",
                "git commit",
                "show changes",
                "show commits",
                "recent commits",
                "commit this",
            ]
        ):
            intents.append("git_ops")

        return intents

    def execute(self, intent: str, **kwargs) -> Dict[str, Any]:
        """Execute a skill by intent name."""
        skill_fn = self.skills.get(intent)
        if skill_fn:
            try:
                return skill_fn(**kwargs)
            except Exception as e:
                return {"error": f"Skill {intent} failed: {str(e)}"}
        return {"error": f"Unknown skill: {intent}"}

    def execute_all(self, intents: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Execute multiple skills and return results."""
        results = []
        for intent in intents:
            result = self.execute(intent, **kwargs)
            results.append({"intent": intent, "result": result})
        return results

    # ─── Skill Implementations ───

    def _web_search(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Web search via a search API."""
        if not query:
            return {"error": "No search query provided"}
        try:
            # Use DuckDuckGo HTML search (no API key needed)
            from urllib.parse import quote

            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            # Simple extraction
            results = []
            for line in resp.text.split("\n"):
                if 'class="result__snippet"' in line:
                    import re

                    text = re.sub(r"<[^>]+>", "", line).strip()
                    if text and len(text) > 20:
                        results.append(text[:200])
                        if len(results) >= 3:
                            break
            return {"query": query, "results": results, "count": len(results)}
        except Exception as e:
            return {"error": f"Web search failed: {str(e)}"}

    def _calendar(self, **kwargs) -> Dict[str, Any]:
        """Check calendar via Apple Calendar."""
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    """
                    tell application "Calendar"
                        set today to current date
                        set today's date to date (short date string of today)
                        set tomorrow to today + 1 * days
                        set output to ""
                        repeat with c in calendars
                            repeat with e in (every event of c whose start date ≥ today and start date < tomorrow)
                                set output to output & (summary of e) & " at " & (time string of start date of e) & "\\n"
                            end repeat
                        end repeat
                        return output
                    end tell
                """,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            events = result.stdout.strip()
            if events:
                return {"events": events, "status": "success"}
            return {"events": "No events today", "status": "success"}
        except Exception as e:
            return {"error": f"Calendar check failed: {str(e)}"}

    def _file_search(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Search for files in workspace."""
        if not query:
            return {"error": "No search query provided"}
        try:
            result = subprocess.run(
                ["mdfind", "-name", query, "-limit", "10"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            files = result.stdout.strip().split("\n")
            files = [f for f in files if f][:10]
            return {"query": query, "files": files, "count": len(files)}
        except Exception as e:
            return {"error": f"File search failed: {str(e)}"}

    def _system_status(self, **kwargs) -> Dict[str, Any]:
        """Check system status of all services."""
        services = {
            "SOV3": "http://localhost:3101/health",
            "MEOK OS": "http://localhost:3000",
            "OpenClaw": "http://localhost:18789",
            "Ollama": "http://localhost:11434",
        }
        status = {}
        for name, url in services.items():
            try:
                resp = requests.get(url, timeout=3)
                status[name] = (
                    "online"
                    if resp.status_code == 200
                    else f"error ({resp.status_code})"
                )
            except:
                status[name] = "offline"
        return {"services": status}

    def _memory_query(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Query SOV3 memory for past conversations."""
        if not query:
            return {"error": "No query provided"}
        try:
            resp = requests.post(
                "http://localhost:3101/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "query_memories",
                        "arguments": {"query": query, "limit": 3},
                    },
                },
                timeout=10,
            )
            data = resp.json()
            text = data.get("result", {}).get("content", [{}])[0].get("text", "")
            memories = json.loads(text) if text else {}
            episodes = memories.get("memories", [])
            if episodes:
                return {"memories": [ep.get("content", "")[:200] for ep in episodes]}
            return {"memories": [], "message": "No relevant memories found"}
        except Exception as e:
            return {"error": f"Memory query failed: {str(e)}"}

    def _code_execution(self, code: str = None, **kwargs) -> Dict[str, Any]:
        """Execute code safely."""
        if not code:
            return {"error": "No code provided"}
        try:
            result = subprocess.run(
                ["python3", "-c", code], capture_output=True, text=True, timeout=30
            )
            return {
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"error": f"Code execution failed: {str(e)}"}

    def _email_check(self, **kwargs) -> Dict[str, Any]:
        """Check email via Apple Mail."""
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    """
                    tell application "Mail"
                        set unreadCount to count of (messages of inbox whose read status is false)
                        if unreadCount > 0 then
                            set output to "You have " & unreadCount & " unread emails."
                            set recentMessages to ""
                            set msgList to messages of inbox whose read status is false
                            repeat with i from 1 to (minimum of {5, count of msgList})
                                set m to item i of msgList
                                set recentMessages to recentMessages & (sender of m) & ": " & (subject of m) & "\\n"
                            end repeat
                            return output & "\\n" & recentMessages
                        else
                            return "No unread emails."
                        end if
                    end tell
                """,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {"result": result.stdout.strip()}
        except Exception as e:
            return {"error": f"Email check failed: {str(e)}"}

    def _weather(self, **kwargs) -> Dict[str, Any]:
        """Get weather via wttr.in (no API key needed)."""
        try:
            resp = requests.get("https://wttr.in/?format=j1", timeout=10)
            data = resp.json()
            current = data.get("current_condition", [{}])[0]
            return {
                "temp_c": current.get("temp_C", "?"),
                "temp_f": current.get("temp_F", "?"),
                "condition": current.get("weatherDesc", [{}])[0].get("value", "?"),
                "humidity": current.get("humidity", "?"),
                "wind_kph": current.get("windspeedKmph", "?"),
            }
        except Exception as e:
            return {"error": f"Weather check failed: {str(e)}"}

    def _open_terminal(self, command: str = None, **kwargs) -> Dict[str, Any]:
        """Open Terminal app and optionally run a command."""
        try:
            # Open Terminal
            subprocess.run(["open", "-a", "Terminal"], capture_output=True, timeout=5)

            if command:
                # Run command in new tab
                script = f'tell application "Terminal" to do script "{command}"'
                subprocess.run(
                    ["osascript", "-e", script], capture_output=True, timeout=5
                )
                return {
                    "success": True,
                    "action": "opened_terminal",
                    "command": command,
                }

            return {
                "success": True,
                "action": "opened_terminal",
                "message": "Terminal is now open on your screen",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_command(self, command: str = None, **kwargs) -> Dict[str, Any]:
        """Run a shell command with safety blocklist."""
        if not command:
            return {"error": "No command provided"}

        # Safety blocklist
        import re
        _blocked = ["rm -rf /", "mkfs", "dd if=", ":(){ :|:", "chmod -R 777 /"]
        for pat in _blocked:
            if pat in command.lower():
                return {"error": f"Command blocked by safety filter"}

        try:
            command = command.replace("~", os.environ.get("HOME", "/Users/nicholas"))
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

    def _system_execute(self, **kwargs) -> Dict[str, Any]:
        """Get real system information and run commands."""
        try:
            results = {}

            # CPU info
            cpu = subprocess.run(
                ["sh", "-c", "top -l 1 -n 0 | grep 'CPU usage'"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            results["cpu"] = cpu.stdout.strip() or "CPU info unavailable"

            # Memory
            mem = subprocess.run(
                ["sysctl", "hw.memsize"], capture_output=True, text=True, timeout=5
            )
            results["memory_total"] = mem.stdout.strip()

            # Disk
            disk = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True, timeout=5
            )
            results["disk"] = disk.stdout

            # Process count
            procs = subprocess.run(
                ["ps", "-e", "-c"], capture_output=True, text=True, timeout=5
            )
            results["process_count"] = len(procs.stdout.split("\n"))

            # Top processes
            top = subprocess.run(
                ["sh", "-c", "ps aux --sort=-%cpu | head -6"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            results["top_processes"] = top.stdout

            return results
        except Exception as e:
            return {"error": str(e)}

    def _browse_web(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Browse a web page via SOV3 MCP browse_page tool."""
        url = query or kwargs.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            import requests
            resp = requests.post(
                "http://localhost:3101/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "jarvis-browse",
                    "method": "tools/call",
                    "params": {"name": "browse_page", "arguments": {"url": url, "action": "extract"}},
                },
                timeout=20,
            )
            data = resp.json()
            text = data.get("result", {}).get("content", [{}])[0].get("text", "")
            try:
                parsed = json.loads(text)
                return {"url": url, "title": parsed.get("title", ""), "text": parsed.get("text", "")[:1000]}
            except Exception:
                return {"url": url, "text": text[:1000]}
        except Exception as e:
            return {"error": f"Browse failed: {str(e)}"}

    def _edit_file(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Read or search files via SOV3 MCP claw_code tool."""
        filepath = query or kwargs.get("path", "")
        if not filepath:
            return {"error": "No file path provided"}
        try:
            import requests
            resp = requests.post(
                "http://localhost:3101/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "jarvis-file",
                    "method": "tools/call",
                    "params": {"name": "execute_with_claw_code", "arguments": {"action": "read_file", "file_path": filepath}},
                },
                timeout=15,
            )
            data = resp.json()
            text = data.get("result", {}).get("content", [{}])[0].get("text", "")
            return {"path": filepath, "content": text[:2000]}
        except Exception as e:
            return {"error": f"File read failed: {str(e)}"}

    def _git_ops(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Run git operations (safe: only allows git subcommands)."""
        import shlex
        cmd = query or "git status -s"
        if not cmd.startswith("git"):
            cmd = f"git {cmd}"
        # Safety: block shell metacharacters
        if any(c in cmd for c in [";", "|", "&", "`", "$", "(", ")", ">", "<"]):
            return {"error": "Shell metacharacters not allowed in git commands"}
        try:
            result = subprocess.run(
                shlex.split(cmd),
                shell=False,
                capture_output=True,
                text=True,
                timeout=15,
                cwd="/Users/nicholas/clawd/meok",
            )
            return {
                "command": cmd,
                "success": result.returncode == 0,
                "output": result.stdout[:2000],
                "error": result.stderr[:500] if result.stderr else None,
            }
        except Exception as e:
            return {"error": f"Git failed: {str(e)}"}
