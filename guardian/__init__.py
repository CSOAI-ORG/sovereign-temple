"""
MEOK OS Guardian Module
WiFi Security, Gaming Protection, and Child Safety
"""

from .wifi_security import (
    WifiSecurityModule,
    NetworkDevice,
    WifiSecurityReport,
    scan_network_devices,
    check_wifi_security,
    block_device,
    get_network_stats,
    get_device_info,
    mark_device_trusted,
)

from .gaming_protection import (
    GamingProtectionModule,
    GameRating,
    Platform,
    GameProfile,
    ChildProfile,
    GamingSession,
    ContentCheckResult,
    check_game_content,
    get_gaming_time,
    block_game,
    set_game_limit,
    add_child_profile,
    moderate_chat,
    get_activity_report,
    get_child_profiles,
    check_play_schedule,
)

__all__ = [
    # WiFi Security
    "WifiSecurityModule",
    "NetworkDevice",
    "WifiSecurityReport",
    "scan_network_devices",
    "check_wifi_security",
    "block_device",
    "get_network_stats",
    "get_device_info",
    "mark_device_trusted",
    # Gaming Protection
    "GamingProtectionModule",
    "GameRating",
    "Platform",
    "GameProfile",
    "ChildProfile",
    "GamingSession",
    "ContentCheckResult",
    "check_game_content",
    "get_gaming_time",
    "block_game",
    "set_game_limit",
    "add_child_profile",
    "moderate_chat",
    "get_activity_report",
    "get_child_profiles",
    "check_play_schedule",
]
