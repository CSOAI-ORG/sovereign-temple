"""
Family OS Module for MEOK OS
Family dashboard, member management, schedules, and AI insights
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict


class MemberRole(Enum):
    """Family member roles"""

    PARENT = "parent"
    CHILD = "child"
    GUARDIAN = "guardian"
    GUEST = "guest"


class ChoreStatus(Enum):
    """Chore completion status"""

    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"


def _serialize_datetime(dt):
    """Helper to serialize datetime"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


@dataclass
class FamilyMember:
    """Family member profile"""

    member_id: str
    name: str
    role: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    birth_date: Optional[str] = None
    age: Optional[int] = None
    timezone: str = "America/New_York"
    interests: List[str] = field(default_factory=list)
    notifications_enabled: bool = True
    joined_at: Optional[datetime] = None

    def __post_init__(self):
        if self.joined_at is None:
            self.joined_at = datetime.utcnow()

    @property
    def age_group(self) -> str:
        """Get age group category"""
        if self.age is None:
            return "unknown"
        if self.age < 6:
            return "young_child"
        elif self.age < 13:
            return "child"
        elif self.age < 18:
            return "teen"
        else:
            return "adult"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "member_id": self.member_id,
            "name": self.name,
            "role": self.role,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "birth_date": self.birth_date,
            "age": self.age,
            "timezone": self.timezone,
            "interests": self.interests,
            "notifications_enabled": self.notifications_enabled,
            "joined_at": _serialize_datetime(self.joined_at),
            "age_group": self.age_group,
        }


@dataclass
class Chore:
    """Household chore/task"""

    chore_id: str
    title: str
    description: Optional[str] = None
    assigned_to: List[str] = field(default_factory=list)
    due_date: Optional[date] = None
    due_time: Optional[str] = None
    recurring: Dict[str, Any] = field(default_factory=dict)
    points: int = 0
    status: str = "pending"
    created_by: Optional[str] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chore_id": self.chore_id,
            "title": self.title,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_time": self.due_time,
            "recurring": self.recurring,
            "points": self.points,
            "status": self.status,
            "created_by": self.created_by,
            "completed_at": _serialize_datetime(self.completed_at),
        }


@dataclass
class Event:
    """Calendar event"""

    event_id: str
    title: str
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    description: Optional[str] = None
    all_day: bool = False
    attendees: List[str] = field(default_factory=list)
    location: Optional[str] = None
    reminder: Optional[int] = None
    color: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "start_datetime": _serialize_datetime(self.start_datetime),
            "end_datetime": _serialize_datetime(self.end_datetime),
            "all_day": self.all_day,
            "attendees": self.attendees,
            "location": self.location,
            "reminder": self.reminder,
            "color": self.color,
        }


class FamilyDashboard:
    """Family OS - Main dashboard and management"""

    def __init__(self):
        self.members: Dict[str, FamilyMember] = {}
        self.chores: Dict[str, Chore] = {}
        self.events: Dict[str, Event] = {}
        self._load_data()

    def _load_data(self):
        """Load saved family data"""
        pass

    def add_member(
        self,
        member_id: str,
        name: str,
        role: str,
        age: Optional[int] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a family member"""
        if member_id in self.members:
            return {"success": False, "error": "Member already exists"}

        member = FamilyMember(
            member_id=member_id, name=name, role=role, age=age, email=email
        )
        self.members[member_id] = member

        return {"success": True, "member": member.to_dict()}

    def remove_member(self, member_id: str) -> Dict[str, Any]:
        """Remove a family member"""
        if member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        member = self.members.pop(member_id)

        for chore in self.chores.values():
            if member_id in chore.assigned_to:
                chore.assigned_to.remove(member_id)

        return {"success": True, "removed": member.name}

    def get_members(self) -> List[Dict[str, Any]]:
        """Get all family members"""
        return [m.to_dict() for m in self.members.values()]

    def get_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific member"""
        member = self.members.get(member_id)
        return member.to_dict() if member else None

    def add_chore(
        self,
        chore_id: str,
        title: str,
        assigned_to: List[str],
        due_date: Optional[date] = None,
        points: int = 0,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a chore"""
        chore = Chore(
            chore_id=chore_id,
            title=title,
            description=description,
            assigned_to=assigned_to,
            due_date=due_date,
            points=points,
            created_by=assigned_to[0] if assigned_to else None,
        )
        self.chores[chore_id] = chore

        return {"success": True, "chore": chore.to_dict()}

    def complete_chore(self, chore_id: str, member_id: str) -> Dict[str, Any]:
        """Mark a chore as completed"""
        chore = self.chores.get(chore_id)
        if not chore:
            return {"success": False, "error": "Chore not found"}

        if member_id not in chore.assigned_to:
            return {"success": False, "error": "Not assigned to this member"}

        chore.status = "completed"
        chore.completed_at = datetime.utcnow()

        return {
            "success": True,
            "chore_id": chore_id,
            "completed_by": member_id,
            "points_earned": chore.points,
        }

    def get_chores(
        self, member_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get chores, optionally filtered"""
        chores = list(self.chores.values())

        if member_id:
            chores = [c for c in chores if member_id in c.assigned_to]

        if status:
            chores = [c for c in chores if c.status == status]

        return [c.to_dict() for c in chores]

    def get_chore_stats(self) -> Dict[str, Any]:
        """Get chore completion statistics"""
        total = len(self.chores)
        completed = sum(1 for c in self.chores.values() if c.status == "completed")
        pending = sum(1 for c in self.chores.values() if c.status == "pending")
        overdue = sum(
            1
            for c in self.chores.values()
            if c.status == "pending" and c.due_date and c.due_date < date.today()
        )

        member_points = defaultdict(int)
        for chore in self.chores.values():
            if chore.status == "completed" and chore.completed_at:
                for member_id in chore.assigned_to:
                    member_points[member_id] += chore.points

        return {
            "total_chores": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
            "leaderboard": dict(member_points),
        }

    def add_event(
        self,
        event_id: str,
        title: str,
        start_datetime: datetime,
        end_datetime: Optional[datetime] = None,
        attendees: Optional[List[str]] = None,
        description: Optional[str] = None,
        all_day: bool = False,
    ) -> Dict[str, Any]:
        """Add a calendar event"""
        event = Event(
            event_id=event_id,
            title=title,
            description=description,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            attendees=attendees or [],
            all_day=all_day,
        )
        self.events[event_id] = event

        return {"success": True, "event": event.to_dict()}

    def get_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        member_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get events, optionally filtered"""
        events = list(self.events.values())

        if member_id:
            events = [e for e in events if member_id in e.attendees]

        if start_date:
            events = [e for e in events if e.start_datetime.date() >= start_date]

        if end_date:
            events = [e for e in events if e.start_datetime.date() <= end_date]

        return [e.to_dict() for e in sorted(events, key=lambda e: e.start_datetime)]

    def get_today_events(self) -> List[Dict[str, Any]]:
        """Get today's events"""
        today = date.today()
        return self.get_events(start_date=today, end_date=today)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        today = date.today()

        today_events = self.get_today_events()
        pending_chores = self.get_chores(status="pending")
        chore_stats = self.get_chore_stats()
        members = self.get_members()

        upcoming_events = self.get_events(
            start_date=today, end_date=today + timedelta(days=7)
        )

        return {
            "date": today.isoformat(),
            "members": {
                "count": len(members),
                "parents": len([m for m in members if m["role"] == "parent"]),
                "children": len([m for m in members if m["role"] == "child"]),
            },
            "chores": {
                "pending": chore_stats["pending"],
                "overdue": chore_stats["overdue"],
                "preview": pending_chores[:5],
            },
            "events": {
                "today": len(today_events),
                "upcoming": len(upcoming_events),
                "today_list": today_events[:5],
            },
            "leaderboard": chore_stats.get("leaderboard", {}),
        }

    def get_upcoming_week(self) -> Dict[str, Any]:
        """Get upcoming week's schedule"""
        today = date.today()
        week_events = []

        for i in range(7):
            day = today + timedelta(days=i)
            day_events = self.get_events(start_date=day, end_date=day)
            day_chores = [
                c
                for c in self.get_chores(status="pending")
                if c.get("due_date") == day.isoformat()
            ]

            week_events.append(
                {
                    "date": day.isoformat(),
                    "day_name": day.strftime("%A"),
                    "events": day_events,
                    "chores": day_chores,
                }
            )

        return {"week_start": today.isoformat(), "days": week_events}


_dashboard = None


def get_dashboard() -> FamilyDashboard:
    """Get or create dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = FamilyDashboard()
    return _dashboard


# MCP Tool functions
def add_family_member(
    member_id: str,
    name: str,
    role: str,
    age: Optional[int] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a family member"""
    dashboard = get_dashboard()
    return dashboard.add_member(member_id, name, role, age, email)


def get_family_members() -> List[Dict[str, Any]]:
    """Get all family members"""
    dashboard = get_dashboard()
    return dashboard.get_members()


def add_chore(
    chore_id: str,
    title: str,
    assigned_to: List[str],
    due_date: Optional[str] = None,
    points: int = 0,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a chore"""
    due = None
    if due_date:
        due = date.fromisoformat(due_date)

    dashboard = get_dashboard()
    return dashboard.add_chore(chore_id, title, assigned_to, due, points, description)


def complete_chore(chore_id: str, member_id: str) -> Dict[str, Any]:
    """Complete a chore"""
    dashboard = get_dashboard()
    return dashboard.complete_chore(chore_id, member_id)


def get_chores(
    member_id: Optional[str] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get chores"""
    dashboard = get_dashboard()
    return dashboard.get_chores(member_id, status)


def add_event(
    event_id: str,
    title: str,
    start_datetime: str,
    end_datetime: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    all_day: bool = False,
) -> Dict[str, Any]:
    """Add an event"""
    start = datetime.fromisoformat(start_datetime)
    end = datetime.fromisoformat(end_datetime) if end_datetime else None

    dashboard = get_dashboard()
    return dashboard.add_event(
        event_id, title, start, end, attendees, description, all_day
    )


def get_events(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get events"""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    dashboard = get_dashboard()
    return dashboard.get_events(start, end)


def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data"""
    dashboard = get_dashboard()
    return dashboard.get_dashboard_data()


def get_upcoming_week() -> Dict[str, Any]:
    """Get upcoming week schedule"""
    dashboard = get_dashboard()
    return dashboard.get_upcoming_week()


def get_chore_stats() -> Dict[str, Any]:
    """Get chore statistics"""
    dashboard = get_dashboard()
    return dashboard.get_chore_stats()
