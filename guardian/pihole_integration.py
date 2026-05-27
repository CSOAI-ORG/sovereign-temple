"""
Pi-hole DNS Integration for MEOK Guardian
Provides DNS-level content filtering and ad blocking
"""

import os
import json
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class PiHoleConfig:
    """Pi-hole server configuration"""

    host: str
    password: str
    port: int = 80
    use_https: bool = False


@dataclass
class PiHoleStats:
    """Pi-hole statistics"""

    domains_being_blocked: int
    dns_queries_today: int
    ads_blocked_today: int
    ads_percentage_today: float
    queries_cached: float
    queries_forwarded: float


class PiHoleClient:
    """
    Pi-hole API client for DNS filtering
    Integrates with Guardian for network-level protection
    """

    def __init__(self, config: Optional[PiHoleConfig] = None):
        self.config = config
        self.base_url = None
        if config:
            protocol = "https" if config.use_https else "http"
            self.base_url = f"{protocol}://{config.host}:{config.port}"

    def configure(
        self, host: str, password: str, port: int = 80, use_https: bool = False
    ):
        """Configure Pi-hole connection"""
        self.config = PiHoleConfig(host, password, port, use_https)
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}:{port}"

    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make authenticated request to Pi-hole"""
        if not self.config or not self.base_url:
            return {"error": "Pi-hole not configured"}

        try:
            response = httpx.get(
                f"{self.base_url}/api/{endpoint}",
                auth=("", self.config.password),
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get Pi-hole status"""
        return self._make_request("status")

    def get_summary(self) -> Dict[str, Any]:
        """Get Pi-hole summary statistics"""
        return self._make_request("summary")

    def get_stats(self) -> PiHoleStats:
        """Get detailed statistics"""
        data = self._make_request("stats")

        if "error" in data:
            return PiHoleStats(0, 0, 0, 0, 0, 0)

        return PiHoleStats(
            domains_being_blocked=data.get("domains_being_blocked", 0),
            dns_queries_today=data.get("dns_queries_today", 0),
            ads_blocked_today=data.get("ads_blocked_today", 0),
            ads_percentage_today=data.get("ads_percentage_today", 0),
            queries_cached=data.get("queries_cached", 0),
            queries_forwarded=data.get("queries_forwarded", 0),
        )

    def get_recent_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent DNS queries"""
        data = self._make_request(f"queries?limit={limit}")
        if "error" in data:
            return []
        return data.get("data", [])[:limit]

    def get_top_domains(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top queried domains"""
        data = self._make_request(f"topDomains?limit={limit}")
        return data.get("top_domains", [])

    def get_top_blocked(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most frequently blocked domains"""
        data = self._make_request(f"topBlockedDomains?limit={limit}")
        return data.get("top_blocked", [])

    def add_to_whitelist(self, domain: str) -> Dict[str, Any]:
        """Add domain to whitelist"""
        if not self.config:
            return {"error": "Pi-hole not configured"}

        try:
            response = httpx.post(
                f"{self.base_url}/api/whitelist",
                data={"domain": domain},
                auth=("", self.config.password),
                timeout=10,
            )
            return {"success": response.status_code == 200, "domain": domain}
        except Exception as e:
            return {"error": str(e)}

    def add_to_blacklist(
        self, domain: str, list_type: str = "blacklist"
    ) -> Dict[str, Any]:
        """Add domain to blacklist"""
        if not self.config:
            return {"error": "Pi-hole not configured"}

        try:
            response = httpx.post(
                f"{self.base_url}/api/{list_type}",
                data={"domain": domain},
                auth=("", self.config.password),
                timeout=10,
            )
            return {"success": response.status_code == 200, "domain": domain}
        except Exception as e:
            return {"error": str(e)}

    def enable(self) -> Dict[str, Any]:
        """Enable Pi-hole filtering"""
        if not self.config:
            return {"error": "Pi-hole not configured"}

        try:
            response = httpx.get(
                f"{self.base_url}/api/enable",
                auth=("", self.config.password),
                timeout=10,
            )
            return {"success": response.status_code == 200}
        except Exception as e:
            return {"error": str(e)}

    def disable(self, seconds: int = 0) -> Dict[str, Any]:
        """Disable Pi-hole filtering (optionally temporarily)"""
        if not self.config:
            return {"error": "Pi-hole not configured"}

        try:
            endpoint = (
                f"api/disable" if seconds == 0 else f"api/disable?disable={seconds}"
            )
            response = httpx.get(
                f"{self.base_url}/{endpoint}",
                auth=("", self.config.password),
                timeout=10,
            )
            return {"success": response.status_code == 200, "temporary": seconds > 0}
        except Exception as e:
            return {"error": str(e)}

    def get_lists(self) -> Dict[str, Any]:
        """Get current block/allow lists"""
        return self._make_request("lists")


# Default instance
_pihole_client = PiHoleClient()


def configure_pihole(host: str, password: str, port: int = 80, use_https: bool = False):
    """Configure Pi-hole connection"""
    _pihole_client.configure(host, password, port, use_https)


def get_pihole_status() -> Dict[str, Any]:
    """Get Pi-hole status"""
    return _pihole_client.get_status()


def get_pihole_stats() -> Dict[str, Any]:
    """Get Pi-hole statistics"""
    stats = _pihole_client.get_stats()
    return {
        "domains_blocked": stats.domains_being_blocked,
        "queries_today": stats.dns_queries_today,
        "ads_blocked": stats.ads_blocked_today,
        "ads_percentage": round(stats.ads_percentage_today, 1),
        "cached": round(stats.queries_cached, 1),
        "forwarded": round(stats.queries_forwarded, 1),
    }


def get_top_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top queried domains"""
    return _pihole_client.get_top_domains(limit)


def get_top_blocked(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top blocked domains"""
    return _pihole_client.get_top_blocked(limit)


def whitelist_domain(domain: str) -> Dict[str, Any]:
    """Add domain to whitelist"""
    return _pihole_client.add_to_whitelist(domain)


def blacklist_domain(domain: str) -> Dict[str, Any]:
    """Add domain to blacklist"""
    return _pihole_client.add_to_blacklist(domain)


def enable_pihole() -> Dict[str, Any]:
    """Enable Pi-hole"""
    return _pihole_client.enable()


def disable_pihole(seconds: int = 0) -> Dict[str, Any]:
    """Disable Pi-hole"""
    return _pihole_client.disable(seconds)
