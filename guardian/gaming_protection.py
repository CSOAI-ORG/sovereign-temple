"""
Guardian Gaming Protection Module for MEOK OS
Child safety for gaming, content filtering, and screen time
"""

import asyncio
import json
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class GameRating(Enum):
    """Game content ratings"""

    EARLY_CHILDHOOD = "ec"
    EVERYONE = "e"
    EVERYONE_10 = "e10+"
    TEEN = "t"
    MATURE = "m"
    ADULTS_ONLY = "ao"


class Platform(Enum):
    """Gaming platforms"""

    PLAYSTATION = "playstation"
    XBOX = "xbox"
    NINTENDO = "nintendo"
    STEAM = "steam"
    MOBILE = "mobile"
    PC = "pc"


@dataclass
class GameProfile:
    """Game profile with content info"""

    game_id: str
    title: str
    platform: str
    rating: Optional[str] = None
    content_tags: List[str] = None
    is_installed: bool = False
    play_time_today: int = 0  # minutes
    last_played: Optional[datetime] = None

    def __post_init__(self):
        if self.content_tags is None:
            self.content_tags = []


@dataclass
class ChildProfile:
    """Child profile for gaming protection"""

    child_id: str
    name: str
    age: int
    allowed_ratings: List[str] = None
    blocked_games: List[str] = None
    allowed_games: List[str] = None
    daily_limit_minutes: int = 60
    schedule: Dict[str, Any] = None  # day -> {"start": "08:00", "end": "20:00"}
    is_active: bool = True

    def __post_init__(self):
        if self.allowed_ratings is None:
            self.allowed_ratings = ["ec", "e", "e10+"]
        if self.blocked_games is None:
            self.blocked_games = []
        if self.allowed_games is None:
            self.allowed_games = []
        if self.schedule is None:
            self.schedule = {
                "weekday": {"start": "08:00", "end": "20:00"},
                "weekend": {"start": "08:00", "end": "21:00"},
            }


@dataclass
class GamingSession:
    """Active gaming session"""

    child_id: str
    game_id: str
    start_time: datetime
    duration_minutes: int = 0
    is_blocked: bool = False


@dataclass
class ContentCheckResult:
    """Content filtering result"""

    is_allowed: bool
    reason: str
    rating: Optional[str] = None
    matched_tags: List[str] = None
    confidence: float = 1.0

    def __post_init__(self):
        if self.matched_tags is None:
            self.matched_tags = []


# Common game content tags
GAME_CONTENT_TAGS = {
    "violence": ["violence", "combat", "shooting", "fighting", "blood", "gore"],
    "language": ["profanity", "crude_humor", "sexual_content"],
    "gambling": ["gambling", "casino", "betting"],
    "drugs": ["drug_use", "alcohol", "tobacco"],
    "social": ["online_play", "in_game_purchases", "chat"],
    "educational": ["educational", "learning", "puzzle", "creative"],
    "age_appropriate": ["kids", "family", "all_ages"],
}


# Game database (simplified - in production would use RAWG API or similar)
GAME_DATABASE = {
    "minecraft": {"rating": "e10+", "tags": ["creative", "building", "online_play"]},
    "fortnite": {
        "rating": "t",
        "tags": ["shooting", "online_play", "in_game_purchases"],
    },
    "roblox": {"rating": "e10+", "tags": ["online_play", "user_generated"]},
    "fifa": {"rating": "e", "tags": ["sports", "online_play"]},
    "call_of_duty": {"rating": "m", "tags": ["violence", "shooting", "online_play"]},
    "gta": {"rating": "m", "tags": ["violence", "drugs", "language", "gambling"]},
    "mario": {"rating": "e", "tags": ["family", "platformer"]},
    "pokemon": {"rating": "e", "tags": ["family", "rpg"]},
    "Among Us": {"rating": "e10+", "tags": ["online_play"]},
    "Brawl Stars": {"rating": "e10+", "tags": ["fighting", "online_play"]},
    "Clash of Clans": {"rating": "e10+", "tags": ["strategy", "in_game_purchases"]},
    "Candy Crush": {"rating": "e", "tags": ["puzzle"]},
}


class GamingProtectionModule:
    """
    Guardian Gaming Protection Module
    Provides child safety features for gaming
    """

    def __init__(self):
        self.children: Dict[str, ChildProfile] = {}
        self.sessions: Dict[str, GamingSession] = {}
        self.blocked_keywords: List[str] = []
        self._load_profiles()

    def _load_profiles(self):
        """Load saved profiles"""
        # In production, load from database
        pass

    def add_child(
        self,
        child_id: str,
        name: str,
        age: int,
        allowed_ratings: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a child profile"""
        profile = ChildProfile(
            child_id=child_id,
            name=name,
            age=age,
            allowed_ratings=allowed_ratings or self._get_ratings_for_age(age),
        )
        self.children[child_id] = profile

        return {
            "success": True,
            "child_id": child_id,
            "name": name,
            "age": age,
            "allowed_ratings": profile.allowed_ratings,
        }

    def _get_ratings_for_age(self, age: int) -> List[str]:
        """Get appropriate game ratings for age"""
        if age < 6:
            return ["ec", "e"]
        elif age < 10:
            return ["ec", "e", "e10+"]
        elif age < 13:
            return ["ec", "e", "e10+", "t"]
        elif age < 17:
            return ["ec", "e", "e10+", "t", "m"]
        else:
            return ["ec", "e", "e10+", "t", "m", "ao"]

    def check_game_content(self, game_title: str, child_id: str) -> ContentCheckResult:
        """Check if a game is appropriate for a child"""
        child = self.children.get(child_id)
        if not child:
            return ContentCheckResult(
                is_allowed=True,  # Unknown child, allow
                reason="No profile found",
            )

        # Get game info
        game_info = GAME_DATABASE.get(game_title.lower())

        if not game_info:
            # Unknown game - allow with warning
            return ContentCheckResult(
                is_allowed=True, reason=f"Unknown game: {game_title}", confidence=0.5
            )

        game_rating = game_info.get("rating", "e")
        game_tags = game_info.get("tags", [])

        # Check rating
        rating_order = ["ec", "e", "e10+", "t", "m", "ao"]

        child_max_idx = 0
        for r in child.allowed_ratings:
            if r in rating_order:
                child_max_idx = max(child_max_idx, rating_order.index(r))

        game_idx = rating_order.index(game_rating) if game_rating in rating_order else 0

        if game_idx > child_max_idx:
            return ContentCheckResult(
                is_allowed=False,
                reason=f"Rating {game_rating} not allowed for this child",
                rating=game_rating,
                matched_tags=game_tags,
            )

        # Check blocked games
        if game_title.lower() in [g.lower() for g in child.blocked_games]:
            return ContentCheckResult(
                is_allowed=False,
                reason="Game is explicitly blocked",
                rating=game_rating,
                matched_tags=game_tags,
            )

        # Check allowed games list
        if child.allowed_games:
            allowed_lower = [g.lower() for g in child.allowed_games]
            if game_title.lower() not in allowed_lower:
                return ContentCheckResult(
                    is_allowed=False,
                    reason="Game not in allowed list",
                    rating=game_rating,
                    matched_tags=game_tags,
                )

        # Check for blocked content tags
        blocked_tags = self._get_blocked_tags_for_age(child.age)
        matched_tags = [tag for tag in game_tags if tag in blocked_tags]

        if matched_tags:
            return ContentCheckResult(
                is_allowed=False,
                reason=f"Contains blocked content: {', '.join(matched_tags)}",
                rating=game_rating,
                matched_tags=matched_tags,
            )

        return ContentCheckResult(
            is_allowed=True,
            reason="Game is appropriate",
            rating=game_rating,
            matched_tags=game_tags,
        )

    def _get_blocked_tags_for_age(self, age: int) -> List[str]:
        """Get content tags to block based on age"""
        if age < 10:
            return ["violence", "gambling", "drugs", "language", "sexual_content"]
        elif age < 13:
            return ["gambling", "drugs", "sexual_content"]
        elif age < 16:
            return ["gambling", "sexual_content"]
        return []

    def check_play_time(self, child_id: str) -> Dict[str, Any]:
        """Check if child can play now (schedule + daily limit)"""
        child = self.children.get(child_id)
        if not child:
            return {"can_play": True, "reason": "No profile"}

        now = datetime.now()
        day_type = "weekend" if now.weekday() >= 5 else "weekday"
        schedule = child.schedule.get(day_type, {"start": "08:00", "end": "20:00"})

        # Check time window
        current_time = now.strftime("%H:%M")
        if current_time < schedule["start"] or current_time > schedule["end"]:
            return {
                "can_play": False,
                "reason": f"Outside allowed hours ({schedule['start']}-{schedule['end']})",
                "next_available": schedule["start"],
            }

        # Check daily limit
        if child.daily_limit_minutes <= 0:
            return {"can_play": False, "reason": "Daily time limit reached"}

        return {
            "can_play": True,
            "remaining_minutes": child.daily_limit_minutes,
            "allowed_until": schedule["end"],
        }

    def set_game_limit(self, child_id: str, minutes: int) -> Dict[str, Any]:
        """Set daily game time limit"""
        child = self.children.get(child_id)
        if not child:
            return {"success": False, "error": "Child not found"}

        child.daily_limit_minutes = minutes
        return {"success": True, "child_id": child_id, "daily_limit": minutes}

    def block_game(self, child_id: str, game_title: str) -> Dict[str, Any]:
        """Block a specific game"""
        child = self.children.get(child_id)
        if not child:
            return {"success": False, "error": "Child not found"}

        if game_title not in child.blocked_games:
            child.blocked_games.append(game_title)

        return {"success": True, "child_id": child_id, "blocked": game_title}

    def allow_game(self, child_id: str, game_title: str) -> Dict[str, Any]:
        """Explicitly allow a game"""
        child = self.children.get(child_id)
        if not child:
            return {"success": False, "error": "Child not found"}

        if game_title not in child.allowed_games:
            child.allowed_games.append(game_title)

        # Remove from blocked if present
        if game_title in child.blocked_games:
            child.blocked_games.remove(game_title)

        return {"success": True, "child_id": child_id, "allowed": game_title}

    def get_gaming_time(self, child_id: str) -> Dict[str, Any]:
        """Get gaming time statistics"""
        child = self.children.get(child_id)
        if not child:
            return {"error": "Child not found"}

        return {
            "child_id": child_id,
            "daily_limit": child.daily_limit_minutes,
            "remaining": child.daily_limit_minutes,  # Would track actual usage
            "today_usage": 0,
            "schedule": child.schedule,
        }

    def get_child_profiles(self) -> List[Dict[str, Any]]:
        """Get all child profiles"""
        return [asdict(p) for p in self.children.values()]

    def moderate_chat(self, message: str) -> Dict[str, Any]:
        """
        Moderate gaming chat messages
        Uses pattern matching and keyword detection
        """
        message_lower = message.lower()

        # Check for blocked keywords
        if self.blocked_keywords:
            for keyword in self.blocked_keywords:
                if keyword.lower() in message_lower:
                    return {
                        "is_safe": False,
                        "reason": f"Blocked keyword: {keyword}",
                        "action": "block",
                    }

        # Check for common safety issues
        dangerous_patterns = [
            (r"meet\s+me", "Request to meet in person"),
            (r"your\s+real\s+name", "Requesting real name"),
            (r"home\s+address", "Requesting address"),
            (r"phone\s+number", "Requesting phone number"),
            (r"parent", "Mention of parents"),  # Could be fine, flag for review
        ]

        for pattern, issue in dangerous_patterns:
            if re.search(pattern, message_lower):
                return {"is_safe": False, "reason": issue, "action": "review"}

        return {"is_safe": True, "reason": "Message appears safe", "action": "allow"}

    async def get_installed_games(self) -> List[GameProfile]:
        """
        Get list of installed games
        In production, would scan installed applications
        """
        # Simplified - would check actual installed games
        games = []

        # Common game locations to check
        potential_games = [
            ("minecraft", "PC", Platform.PC),
            ("steam", "Steam", Platform.STEAM),
            ("epic games", "Epic", Platform.PC),
        ]

        return games

    def get_activity_report(self, child_id: str, days: int = 7) -> Dict[str, Any]:
        """Get gaming activity report"""
        child = self.children.get(child_id)
        if not child:
            return {"error": "Child not found"}

        return {
            "child_id": child_id,
            "child_name": child.name,
            "period_days": days,
            "total_playtime_minutes": 0,  # Would track from sessions
            "games_played": [],
            "blocked_attempts": 0,
            "schedule_adherence": 100.0,
        }


# Global instance
_gaming_module = None


def get_gaming_module() -> GamingProtectionModule:
    """Get or create gaming module instance"""
    global _gaming_module
    if _gaming_module is None:
        _gaming_module = GamingProtectionModule()
    return _gaming_module


# MCP Tool functions
def check_game_content(game_title: str, child_id: str = "default") -> Dict[str, Any]:
    """Check if a game is appropriate for a child"""
    module = get_gaming_module()
    result = module.check_game_content(game_title, child_id)
    return asdict(result)


def get_gaming_time(child_id: str) -> Dict[str, Any]:
    """Get gaming time for a child"""
    module = get_gaming_module()
    return module.get_gaming_time(child_id)


def block_game(child_id: str, game_title: str) -> Dict[str, Any]:
    """Block a specific game"""
    module = get_gaming_module()
    return module.block_game(child_id, game_title)


def set_game_limit(child_id: str, minutes: int) -> Dict[str, Any]:
    """Set daily game time limit"""
    module = get_gaming_module()
    return module.set_game_limit(child_id, minutes)


def add_child_profile(child_id: str, name: str, age: int) -> Dict[str, Any]:
    """Add a child profile"""
    module = get_gaming_module()
    return module.add_child(child_id, name, age)


def moderate_chat(message: str) -> Dict[str, Any]:
    """Moderate a chat message"""
    module = get_gaming_module()
    return module.moderate_chat(message)


def get_activity_report(child_id: str, days: int = 7) -> Dict[str, Any]:
    """Get gaming activity report"""
    module = get_gaming_module()
    return module.get_activity_report(child_id, days)


def get_child_profiles() -> List[Dict[str, Any]]:
    """Get all child profiles"""
    module = get_gaming_module()
    return module.get_child_profiles()


def check_play_schedule(child_id: str) -> Dict[str, Any]:
    """Check if child can play now based on schedule"""
    module = get_gaming_module()
    return module.check_play_time(child_id)
