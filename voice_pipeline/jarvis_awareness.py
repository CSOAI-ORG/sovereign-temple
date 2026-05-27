#!/usr/bin/env python3
"""
JARVIS Background Awareness Engine
Monitors environment, keywords, system events while listening for wake word.
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

AWARNESS_FILE = Path("/Users/nicholas/clawd/jarvis-memory/awareness.json")
AWARNESS_FILE.parent.mkdir(exist_ok=True)


class BackgroundAwareness:
    """
    Background awareness while JARVIS is in wake-word mode:
    1. System monitoring — CPU, memory, disk, network
    2. Keyword monitoring — listen for important words in transcripts
    3. Environmental sensing — time, weather, calendar changes
    4. Alert detection — critical system events
    """

    def __init__(self, alert_fn: Callable = None):
        self.alert_fn = alert_fn
        self.monitoring = False
        self.watch_keywords = []
        self.last_system_check = 0
        self.system_check_interval = 300  # 5 minutes
        self.last_alerts = {}
        self.alert_cooldown = 3600  # 1 hour between same alerts

    def set_keywords(self, keywords: List[str]):
        """Set keywords to watch for in conversation transcripts."""
        self.watch_keywords = keywords

    def check_keywords(self, text: str) -> List[str]:
        """Check if any watched keywords appear in text."""
        lower = text.lower()
        matches = [kw for kw in self.watch_keywords if kw.lower() in lower]
        return matches

    def get_system_health(self) -> Dict:
        """Get system health metrics."""
        try:
            # CPU load
            load = os.getloadavg()
            cpu_pct = round((load[0] / os.cpu_count()) * 100, 1)

            # Memory
            mem_cmd = "vm_stat | perl -ne '/page size of (\\d+)/ and $ps=$1; /Pages\\s+([^:]+)[^\\d]+(\\d+)/ and printf(\"%s %.1f MB\\n\", \\$1, \\$2 * $ps / 1048576);'"
            mem_result = subprocess.run(
                mem_cmd, shell=True, capture_output=True, text=True, timeout=5
            )

            # Disk
            disk = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True, timeout=5
            )
            disk_lines = disk.stdout.strip().split("\n")
            disk_pct = disk_lines[1].split()[4] if len(disk_lines) > 1 else "?"

            return {
                "cpu_load": f"{cpu_pct}%",
                "load_avg": load,
                "disk_usage": disk_pct,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}

    def check_services(self) -> Dict[str, str]:
        """Check if critical services are running."""
        import requests

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
                status[name] = "online" if resp.status_code == 200 else "degraded"
            except:
                status[name] = "offline"
        return status

    def check_critical_alerts(self) -> List[str]:
        """Check for critical system alerts."""
        alerts = []
        now = time.time()

        # Check services
        service_status = self.check_services()
        for name, status in service_status.items():
            if status == "offline":
                alert_key = f"service_{name}"
                if now - self.last_alerts.get(alert_key, 0) > self.alert_cooldown:
                    alerts.append(f"⚠️ {name} is offline")
                    self.last_alerts[alert_key] = now

        # Check system resources
        health = self.get_system_health()
        if "cpu_load" in health:
            cpu = float(health["cpu_load"].replace("%", ""))
            if cpu > 90:
                alert_key = "high_cpu"
                if now - self.last_alerts.get(alert_key, 0) > self.alert_cooldown:
                    alerts.append(f"🔥 CPU at {health['cpu_load']}")
                    self.last_alerts[alert_key] = now

        return alerts

    def start_monitoring(self):
        """Start background monitoring loop."""
        self.monitoring = True

        def monitor_loop():
            while self.monitoring:
                time.sleep(60)  # Check every minute
                try:
                    alerts = self.check_critical_alerts()
                    if alerts and self.alert_fn:
                        for alert in alerts:
                            self.alert_fn(alert)

                    # Save awareness state
                    state = {
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "alerts_triggered": len(self.last_alerts),
                        "keywords_watched": len(self.watch_keywords),
                    }
                    AWARNESS_FILE.write_text(json.dumps(state, indent=2))
                except Exception as e:
                    pass  # Don't crash background monitoring

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring = False
