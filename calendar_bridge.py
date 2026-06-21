#!/usr/bin/env python3
"""
Calendar Integration Bridge - Calendar Access for SOV3
Enables AI to: read events, create events, check schedules
Supports: Google Calendar, Apple Calendar (local), generic iCal
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

log = logging.getLogger("calendar-bridge")


@dataclass
class CalendarEvent:
    title: str
    start: datetime.datetime
    end: datetime.datetime
    description: str = ""
    location: str = ""
    attendees: List[str] = None

    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "description": self.description,
            "location": self.location,
            "attendees": self.attendees,
        }


class GoogleCalendarBridge:
    """Google Calendar API integration"""

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or os.path.expanduser(
            "~/.config/google-calendar-credentials.json"
        )
        self.service = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Google Calendar API"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            if not os.path.exists(self.credentials_path):
                log.warning(f"Google credentials not found at {self.credentials_path}")
                return False

            creds = Credentials.from_creds_file(self.credentials_path)
            self.service = build("calendar", "v3", credentials=creds)
            self._initialized = True
            log.info("✅ Google Calendar initialized")
            return True

        except ImportError:
            log.warning(
                "Google API not installed: pip install google-api-python-client"
            )
            return False
        except Exception as e:
            log.error(f"Google Calendar init failed: {e}")
            return False

    async def get_events(self, days_ahead: int = 7, max_events: int = 20) -> List[Dict]:
        """Get upcoming events"""
        if not self._initialized:
            return [{"error": "Not initialized"}]

        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            end = (
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days_ahead)
            ).isoformat() + "Z"

            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=end,
                    maxResults=max_events,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            return [
                {
                    "title": e.get("summary", "No title"),
                    "start": e.get("start", {}).get(
                        "dateTime", e.get("start", {}).get("date", "")
                    ),
                    "end": e.get("end", {}).get(
                        "dateTime", e.get("end", {}).get("date", "")
                    ),
                    "location": e.get("location", ""),
                    "description": e.get("description", "")[:200],
                }
                for e in events
            ]

        except Exception as e:
            return [{"error": str(e)}]

    async def create_event(
        self,
        title: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        description: str = "",
        location: str = "",
    ) -> Dict:
        """Create a new event"""
        if not self._initialized:
            return {"error": "Not initialized"}

        try:
            event = {
                "summary": title,
                "start": {"dateTime": start_time.isoformat()},
                "end": {"dateTime": end_time.isoformat()},
                "description": description,
                "location": location,
            }

            created = (
                self.service.events().insert(calendarId="primary", body=event).execute()
            )

            return {
                "success": True,
                "event_id": created.get("id"),
                "link": created.get("htmlLink"),
            }

        except Exception as e:
            return {"error": str(e)}


class AppleCalendarBridge:
    """macOS Calendar (local) integration via AppleScript"""

    def __init__(self):
        self.calendars = []

    async def get_calendars(self) -> List[str]:
        """Get list of available calendars"""
        try:
            script = """
            tell application "Calendar"
                set calList to {}
                repeat with c in calendars
                    set end of calList to name of c
                end repeat
                return calList
            end tell
            """
            result = self._run_script(script)
            return [c.strip() for c in result.split("\n") if c.strip()]
        except Exception as e:
            log.error(f"Failed to get calendars: {e}")
            return []

    async def get_events(self, days_ahead: int = 7) -> List[Dict]:
        """Get upcoming events from all calendars"""
        try:
            script = f"""
            tell application "Calendar"
                set todayDate to current date
                set endDate to todayDate + ({days_ahead} * days)
                
                set eventList to {{}}
                repeat with c in calendars
                    set calEvents to events of c whose start time > todayDate and start time < endDate
                    repeat with e in calEvents
                        set eventStart to start date of e
                        set eventEnd to end date of e
                        set eventTitle to summary of e
                        set eventLoc to location of e
                        set eventDesc to description of e
                        set end of eventList to {{eventTitle, eventStart, eventEnd, eventLoc, eventDesc}}
                    end repeat
                end repeat
                return eventList
            end tell
            """

            result = self._run_script(script)
            events = []

            # Parse AppleScript output
            for line in result.split("\n"):
                if line.strip() and "," in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        events.append(
                            {
                                "title": parts[0].strip(),
                                "start": parts[1].strip() if len(parts) > 1 else "",
                                "end": parts[2].strip() if len(parts) > 2 else "",
                                "location": parts[3].strip() if len(parts) > 3 else "",
                                "description": ",".join(parts[4:]).strip()
                                if len(parts) > 4
                                else "",
                            }
                        )

            return events

        except Exception as e:
            log.error(f"Failed to get events: {e}")
            return [{"error": str(e)}]

    async def create_event(
        self,
        title: str,
        start_time: datetime.datetime,
        duration_minutes: int = 60,
        description: str = "",
        calendar: str = "Home",
    ) -> Dict:
        """Create a new event"""
        try:
            # Format for AppleScript
            start_str = start_time.strftime("%B %d, %Y %I:%M %p")

            script = f'''
            tell application "Calendar"
                tell calendar "{calendar}"
                    make new event with properties {{
                        summary:"{title}",
                        start date:date "{start_str}",
                        description:"{description}"
                    }}
                end tell
            end tell
            '''

            self._run_script(script)
            return {"success": True, "message": f"Event '{title}' created"}

        except Exception as e:
            return {"error": str(e)}

    def _run_script(self, script: str) -> str:
        """Run AppleScript and return output"""
        import subprocess

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        return result.stdout


class ICSCalendarBridge:
    """Generic ICS/iCalendar file support"""

    def __init__(self, ics_path: str = None):
        self.ics_path = ics_path

    async def parse_ics(self, ics_path: str = None) -> List[Dict]:
        """Parse an ICS file"""
        path = ics_path or self.ics_path

        if not path or not os.path.exists(path):
            return [{"error": "ICS file not found"}]

        try:
            with open(path, "r") as f:
                ics_content = f.read()

            events = []
            current_event = {}

            for line in ics_content.split("\n"):
                if line.startswith("BEGIN:VEVENT"):
                    current_event = {}
                elif line.startswith("END:VEVENT"):
                    if current_event:
                        events.append(current_event)
                elif line.startswith("SUMMARY:"):
                    current_event["title"] = line[8:]
                elif line.startswith("DTSTART"):
                    current_event["start"] = line.split(":")[1] if ":" in line else ""
                elif line.startswith("DTEND"):
                    current_event["end"] = line.split(":")[1] if ":" in line else ""
                elif line.startswith("DESCRIPTION:"):
                    current_event["description"] = line[12:]
                elif line.startswith("LOCATION:"):
                    current_event["location"] = line[9:]

            return events

        except Exception as e:
            return [{"error": str(e)}]


class CalendarBridge:
    """
    Unified calendar bridge
    Tries: Google Calendar -> Apple Calendar -> ICS files
    """

    def __init__(self):
        self.google = GoogleCalendarBridge()
        self.apple = AppleCalendarBridge()
        self.ics = ICSCalendarBridge()
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize available calendar backends"""
        # Try Google first
        google_ok = await self.google.initialize()

        if google_ok:
            self._initialized = True
            log.info("✅ Calendar Bridge: Google Calendar")
            return True

        # Fall back to Apple Calendar
        calendars = await self.apple.get_calendars()
        if calendars:
            self._initialized = True
            log.info(f"✅ Calendar Bridge: Apple Calendar ({len(calendars)} calendars)")
            return True

        log.warning("⚠️ No calendar backend available")
        return False

    async def get_events(self, days_ahead: int = 7) -> Dict:
        """Get upcoming events from all available sources"""
        if self.google._initialized:
            events = await self.google.get_events(days_ahead)
            return {"source": "google", "events": events}

        if self.apple:
            events = await self.apple.get_events(days_ahead)
            return {"source": "apple", "events": events}

        return {"source": "none", "events": [], "error": "No calendar available"}

    async def create_event(
        self,
        title: str,
        start_time: datetime.datetime,
        duration_minutes: int = 60,
        description: str = "",
        calendar: str = "Home",
    ) -> Dict:
        """Create a new event"""
        if self.google._initialized:
            end_time = start_time + datetime.timedelta(minutes=duration_minutes)
            return await self.google.create_event(
                title, start_time, end_time, description
            )

        return await self.apple.create_event(
            title, start_time, duration_minutes, description
        )


# Global instance
_calendar_bridge: Optional[CalendarBridge] = None


def get_calendar_bridge() -> CalendarBridge:
    global _calendar_bridge
    if _calendar_bridge is None:
        _calendar_bridge = CalendarBridge()
    return _calendar_bridge


async def get_upcoming_events(days: int = 7) -> Dict:
    """Quick function to get upcoming events"""
    bridge = get_calendar_bridge()
    if not bridge._initialized:
        await bridge.initialize()
    return await bridge.get_events(days)


async def create_calendar_event(
    title: str, start: datetime.datetime, duration: int = 60, description: str = ""
) -> Dict:
    """Quick function to create an event"""
    bridge = get_calendar_bridge()
    if not bridge._initialized:
        await bridge.initialize()
    return await bridge.create_event(title, start, duration, description)


if __name__ == "__main__":
    import asyncio

    async def test():
        bridge = CalendarBridge()
        await bridge.initialize()

        print("=== Upcoming Events ===")
        result = await bridge.get_events(days_ahead=3)
        print(json.dumps(result, indent=2))

    asyncio.run(test())
