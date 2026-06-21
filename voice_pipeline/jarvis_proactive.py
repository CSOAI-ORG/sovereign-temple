#!/usr/bin/env python3
"""
JARVIS Proactive Engagement Engine
JARVIS initiates conversations based on patterns, time, and awareness.
"""

import json
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Callable

ENGAGEMENT_FILE = Path("/Users/nicholas/clawd/jarvis-memory/engagement.json")
ENGAGEMENT_FILE.parent.mkdir(exist_ok=True)


class ProactiveEngine:
    """
    JARVIS proactively engages when:
    1. Nick hasn't spoken in >2 hours during work hours
    2. Something interesting happens (system events, alerts)
    3. Time-based prompts (morning brief, afternoon check-in)
    4. Keyword monitoring in background
    """

    def __init__(self, speak_fn: Callable = None):
        self.speak_fn = speak_fn
        self.last_interaction = time.time()
        self.last_proactive = time.time()
        self.proactive_interval = 7200  # 2 hours
        self.monitoring = False
        self.keywords = []
        self.engagement_log = self._load_log()

    def _load_log(self) -> Dict:
        if ENGAGEMENT_FILE.exists():
            try:
                return json.loads(ENGAGEMENT_FILE.read_text())
            except:
                return {}
        return {"proactive_count": 0, "last_proactive": None, "topics": []}

    def _save_log(self):
        ENGAGEMENT_FILE.write_text(json.dumps(self.engagement_log, indent=2))

    def record_interaction(self):
        """Called when Nick speaks to JARVIS."""
        self.last_interaction = time.time()

    def set_keywords(self, keywords: List[str]):
        """Set keywords to monitor for in background."""
        self.keywords = keywords

    def get_time_prompt(self) -> Optional[str]:
        """Get a time-appropriate proactive prompt."""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()

        if 8 <= hour < 10:
            return "Good morning, Sir. Shall I give you a brief of today's priorities?"
        elif 12 <= hour < 13:
            return "It's lunchtime, Sir. How's the morning going? Anything you'd like to discuss?"
        elif 15 <= hour < 16:
            return "Afternoon check-in, Sir. How's the work progressing? Need any assistance?"
        elif 18 <= hour < 19:
            return (
                "Evening approaching, Sir. Shall we review what we accomplished today?"
            )
        elif hour >= 22:
            return "Getting late, Sir. Anything you'd like to wrap up before resting?"

        return None

    def should_engage(self) -> bool:
        """Check if it's time for proactive engagement."""
        now = time.time()
        hours_since_interaction = (now - self.last_interaction) / 3600
        hours_since_proactive = (now - self.last_proactive) / 3600

        # Don't engage if Nick just spoke
        if hours_since_interaction < 0.5:
            return False

        # Don't engage too frequently
        if hours_since_proactive < self.proactive_interval / 3600:
            return False

        # Don't engage during sleep hours (23:00 - 07:00)
        hour = datetime.now().hour
        if hour >= 23 or hour < 7:
            return False

        return True

    def engage(self):
        """Proactively engage with Nick."""
        if not self.should_engage() or not self.speak_fn:
            return

        prompt = self.get_time_prompt()
        if prompt:
            self.last_proactive = time.time()
            self.engagement_log["proactive_count"] = (
                self.engagement_log.get("proactive_count", 0) + 1
            )
            self.engagement_log["last_proactive"] = datetime.now(
                timezone.utc
            ).isoformat()
            self._save_log()

            # Speak the prompt
            threading.Thread(target=self.speak_fn, args=(prompt,), daemon=True).start()

    def start_monitoring(self):
        """Start background monitoring loop."""
        self.monitoring = True

        def monitor_loop():
            while self.monitoring:
                time.sleep(300)  # Check every 5 minutes
                try:
                    self.engage()
                except Exception as e:
                    print(f"[ProactiveEngine] Error: {e}")

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring = False
