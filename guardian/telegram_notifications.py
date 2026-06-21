"""
Telegram Notification Integration for MEOK Guardian
Sends alerts to parents about children, security, and family events
"""

import os
import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class AlertType(Enum):
    """Types of Guardian alerts"""

    CHILD_GAME_BLOCKED = "child_game_blocked"
    CHILD_SCHEDULE_VIOLATION = "child_schedule_violation"
    UNKNOWN_DEVICE_DETECTED = "unknown_device_detected"
    SECURITY_THREAT = "security_threat"
    CHORE_COMPLETED = "chore_completed"
    EVENT_REMINDER = "event_reminder"
    DAILY_SUMMARY = "daily_summary"


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""

    bot_token: str
    chat_id: str
    enabled: bool = True


class TelegramNotifier:
    """
    Telegram notification service for Guardian
    Sends real-time alerts to family members
    """

    def __init__(self):
        self.config: Optional[TelegramConfig] = None
        self.api_url = None

    def configure(self, bot_token: str, chat_id: str, enabled: bool = True):
        """Configure Telegram bot"""
        self.config = TelegramConfig(bot_token, chat_id, enabled)
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def is_configured(self) -> bool:
        """Check if Telegram is configured"""
        return self.config is not None and self.config.enabled and self.config.bot_token

    async def send_message(
        self, text: str, parse_mode: str = "Markdown"
    ) -> Dict[str, Any]:
        """Send a message via Telegram"""
        if not self.is_configured():
            return {"error": "Telegram not configured", "success": False}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.config.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message_id": response.json()
                        .get("result", {})
                        .get("message_id"),
                    }
                return {"error": f"HTTP {response.status_code}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    async def send_alert(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a formatted alert"""

        # Format message based on type
        emojis = {
            AlertType.CHILD_GAME_BLOCKED: "🎮🚫",
            AlertType.CHILD_SCHEDULE_VIOLATION: "⏰⚠️",
            AlertType.UNKNOWN_DEVICE_DETECTED: "📶❓",
            AlertType.SECURITY_THREAT: "🔒🚨",
            AlertType.CHORE_COMPLETED: "✅🏠",
            AlertType.EVENT_REMINDER: "📅🔔",
            AlertType.DAILY_SUMMARY: "📊🌙",
        }

        emoji = emojis.get(alert_type, "📢")

        formatted = f"*{emoji} {title}*\n\n{message}"

        if details:
            formatted += "\n\n*Details:*\n"
            for key, value in details.items():
                formatted += f"• {key}: `{value}`\n"

        return await self.send_message(formatted)

    async def notify_game_blocked(
        self, child_name: str, game_title: str, reason: str
    ) -> Dict[str, Any]:
        """Notify that a game was blocked"""
        return await self.send_alert(
            AlertType.CHILD_GAME_BLOCKED,
            f"Game Blocked - {child_name}",
            f"*{game_title}* was blocked for {child_name}",
            {
                "Game": game_title,
                "Reason": reason,
                "Time": datetime.now().strftime("%H:%M"),
            },
        )

    async def notify_schedule_violation(
        self, child_name: str, activity: str
    ) -> Dict[str, Any]:
        """Notify of schedule violation"""
        return await self.send_alert(
            AlertType.CHILD_SCHEDULE_VIOLATION,
            f"Schedule Alert - {child_name}",
            f"{child_name} tried to {activity} outside allowed hours",
            {"Activity": activity, "Time": datetime.now().strftime("%H:%M")},
        )

    async def notify_unknown_device(
        self, device_info: str, network: str
    ) -> Dict[str, Any]:
        """Notify of unknown device on network"""
        return await self.send_alert(
            AlertType.UNKNOWN_DEVICE_DETECTED,
            "Unknown Device Detected",
            f"A new device was detected on your network",
            {
                "Device": device_info,
                "Network": network,
                "Time": datetime.now().strftime("%H:%M"),
            },
        )

    async def notify_security_alert(
        self, threat_type: str, details: str
    ) -> Dict[str, Any]:
        """Send security alert"""
        return await self.send_alert(
            AlertType.SECURITY_THREAT,
            "🚨 Security Alert",
            f"*{threat_type}* detected",
            {"Details": details, "Time": datetime.now().strftime("%H:%M")},
        )

    async def notify_chore_completed(
        self, child_name: str, chore: str, points: int
    ) -> Dict[str, Any]:
        """Notify of chore completion"""
        return await self.send_alert(
            AlertType.CHORE_COMPLETED,
            f"Chore Done - {child_name}",
            f"{child_name} completed: *{chore}*",
            {
                "Chore": chore,
                "Points": str(points),
                "Time": datetime.now().strftime("%H:%M"),
            },
        )

    async def send_daily_summary(
        self,
        children_status: Dict[str, Any],
        chores_completed: int,
        chores_pending: int,
        network_devices: int,
    ) -> Dict[str, Any]:
        """Send daily family summary"""
        message = "*🌙 MEOK Daily Summary*\n\n"

        message += "*Gaming:*\n"
        for child, status in children_status.items():
            playtime = status.get("playtime_used", 0)
            limit = status.get("daily_limit", 0)
            message += f"• {child}: {playtime}/{limit} min\n"

        message += f"\n*Chores:*\n• Completed: {chores_completed}\n• Pending: {chores_pending}\n"

        message += f"\n*Network:*\n• Devices: {network_devices}\n"

        return await self.send_message(message)


# Default notifier instance
_telegram_notifier = TelegramNotifier()


def configure_telegram(bot_token: str, chat_id: str, enabled: bool = True):
    """Configure Telegram notifications"""
    _telegram_notifier.configure(bot_token, chat_id, enabled)


async def send_telegram_alert(
    alert_type: str,
    title: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send alert via Telegram"""
    try:
        alert = AlertType(alert_type)
    except ValueError:
        alert = AlertType.DAILY_SUMMARY

    return await _telegram_notifier.send_alert(alert, title, message, details)


async def notify_game_blocked(
    child_name: str, game_title: str, reason: str
) -> Dict[str, Any]:
    """Notify game was blocked"""
    return await _telegram_notifier.notify_game_blocked(child_name, game_title, reason)


async def notify_schedule_violation(child_name: str, activity: str) -> Dict[str, Any]:
    """Notify schedule violation"""
    return await _telegram_notifier.notify_schedule_violation(child_name, activity)


async def notify_unknown_device(device_info: str, network: str) -> Dict[str, Any]:
    """Notify unknown device"""
    return await _telegram_notifier.notify_unknown_device(device_info, network)


async def notify_security_alert(threat_type: str, details: str) -> Dict[str, Any]:
    """Send security alert"""
    return await _telegram_notifier.notify_security_alert(threat_type, details)


async def send_daily_summary(
    children_status: Dict[str, Any],
    chores_completed: int,
    chores_pending: int,
    network_devices: int,
) -> Dict[str, Any]:
    """Send daily summary"""
    return await _telegram_notifier.send_daily_summary(
        children_status, chores_completed, chores_pending, network_devices
    )
