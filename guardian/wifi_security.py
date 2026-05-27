"""
Guardian WiFi Security Module for MEOK OS
Network monitoring, device discovery, and security features
"""

import asyncio
import json
import subprocess
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import socket
import struct


@dataclass
class NetworkDevice:
    """Represents a device on the network"""

    mac_address: str
    ip_address: str
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    first_seen: datetime = None
    last_seen: datetime = None
    device_type: str = "unknown"  # phone, laptop, iot, router, etc.
    is_trusted: bool = False
    risk_level: str = "low"  # low, medium, high


@dataclass
class WifiSecurityReport:
    """WiFi security assessment report"""

    network_name: str
    security_type: str  # WPA3, WPA2, WPA, WEP, None
    encryption_strength: int  # 1-5
    has_default_password: bool
    has_wps_enabled: bool
    connected_devices: int
    trusted_devices: int
    unknown_devices: int
    iot_devices: int
    router_firmware: Optional[str] = None
    vulnerabilities: List[str] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.vulnerabilities is None:
            self.vulnerabilities = []
        if self.recommendations is None:
            self.recommendations = []


class WifiSecurityModule:
    """
    Guardian WiFi Security Module
    Provides network monitoring, device discovery, and security assessment
    """

    # OUI database - first 3 bytes of MAC to vendor
    OUI_PREFIXES = {
        "00:1A:2B": "Cisco",
        "00:25:00": "Apple",
        "00:26:BB": "Apple",
        "00:50:56": "VMware",
        "00:1C:42": "Parallels",
        "A4:83:E7": "Apple",
        "F0:18:98": "Apple",
        "3C:06:30": "Apple",
        "58:B0:35": "Apple",
        "DC:2B:2A": "Apple",
        "00:0C:29": "VMware",
        "B8:27:EB": "Raspberry Pi",
        "E4:5F:01": "Raspberry Pi",
        "00:1D:0F": "TP-Link",
        "00:27:19": "TP-Link",
        "50:C7:BF": "TP-Link",
        "D4:3D:7E": "Xiaomi",
        "74:23:44": "Xiaomi",
        "9C:99:A0": "Samsung",
        "00:1F:CC": "Samsung",
        "00:24:54": "Netgear",
        "00:09:5B": "Netgear",
        "C0:3F:0E": "Netgear",
        "00:14:6C": "Netgear",
        "00:1E:2A": "D-Link",
        "00:1B:11": "D-Link",
        "00:22:B0": "D-Link",
        "00:26:5A": "ASUS",
        "00:1D:7E": "ASUS",
        "AC:9E:17": "ASUS",
        "00:11:2F": "Dell",
        "00:14:22": "Dell",
        "18:66:DA": "Dell",
        "00:1C:C0": "Dell",
        "00:15:C5": "HP",
        "00:26:B9": "HP",
        "00:17:08": "HP",
        "3C:D9:2B": "HP",
    }

    # Device type signatures
    DEVICE_SIGNATURES = {
        "router": [
            "router",
            "gateway",
            "netgear",
            "tp-link",
            "asus",
            "cisco",
            "linksys",
        ],
        "phone": ["iphone", "android", "samsung", "huawei", "pixel"],
        "laptop": ["laptop", "macbook", "dell", "lenovo", "thinkpad", "hp-", "asus-"],
        "iot": [
            "raspberry",
            "esp32",
            "arduino",
            "sonoff",
            "tuya",
            "smart",
            "bulb",
            "plug",
        ],
        "tv": ["tv", "roku", "firetv", "apple-tv", "chromecast", "smart-tv"],
        "game": ["playstation", "xbox", "nintendo", "steam", "deck"],
    }

    def __init__(self):
        self.devices: Dict[str, NetworkDevice] = {}
        self.network_range: Optional[str] = None
        self.gateway: Optional[str] = None
        self.ssid: Optional[str] = None
        self._initialize_network_info()

    def _initialize_network_info(self):
        """Get initial network information"""
        try:
            # Get default gateway
            result = subprocess.run(
                ["route", "-n", "get", "default"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "gateway:" in line:
                    self.gateway = line.split(":")[-1].strip()
                    break

            # Get network range
            if self.gateway:
                # Assume /24 network
                self.network_range = ".".join(self.gateway.split(".")[:3]) + ".0/24"
                self.ssid = self._get_current_ssid()
        except Exception as e:
            print(f"Error initializing network info: {e}")

    def _get_current_ssid(self) -> Optional[str]:
        """Get current WiFi SSID"""
        try:
            result = subprocess.run(
                [
                    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                    "-I",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "SSID:" in line:
                    return line.split(":")[-1].strip()
        except:
            pass
        return None

    def _mac_to_vendor(self, mac: str) -> Optional[str]:
        """Look up MAC vendor from OUI"""
        if not mac or len(mac) < 8:
            return None
        prefix = ":".join(mac.upper().split(":")[:3])
        return self.OUI_PREFIXES.get(prefix)

    def _detect_device_type(self, mac: str, hostname: str) -> str:
        """Detect device type from MAC vendor and hostname"""
        vendor = self._mac_to_vendor(mac)
        combined = f"{vendor or ''} {hostname or ''}".lower()

        for device_type, signatures in self.DEVICE_SIGNATURES.items():
            for sig in signatures:
                if sig in combined:
                    return device_type
        return "unknown"

    def _ping_device(self, ip: str) -> bool:
        """Ping a device to check if it's online"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-t", "2", ip], capture_output=True, timeout=2
            )
            return result.returncode == 0
        except:
            return False

    async def scan_network(
        self, scan_range: Optional[str] = None
    ) -> List[NetworkDevice]:
        """
        Scan the network for devices
        Uses ARP scanning for device discovery
        """
        if scan_range:
            self.network_range = scan_range

        # Parse network range
        if not self.network_range:
            return []

        network = self.network_range.replace("/24", "")
        devices_found = []

        # Common local IP range (home network)
        base = network if network else "192.168.1"

        # Quick scan - check common gateway and local IPs
        scan_ips = []

        # Add gateway
        if self.gateway:
            scan_ips.append(self.gateway)

        # Scan common ranges
        for last_octet in range(1, 255):
            ip = f"{base}.{last_octet}"
            if ip != self.gateway:
                scan_ips.append(ip)

        # Concurrent scan with limited workers
        semaphore = asyncio.Semaphore(50)

        async def check_ip(ip: str) -> Optional[NetworkDevice]:
            async with semaphore:
                if self._ping_device(ip):
                    return await self._create_device(ip)
                return None

        # Run concurrent scans
        tasks = [check_ip(ip) for ip in scan_ips[:254]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, NetworkDevice):
                devices_found.append(result)
                self.devices[result.mac_address] = result

        return devices_found

    async def _create_device(self, ip: str) -> Optional[NetworkDevice]:
        """Create a NetworkDevice from an IP"""
        try:
            # Get MAC address
            mac = self._get_mac_from_ip(ip)
            if not mac:
                return None

            # Get hostname
            hostname = self._get_hostname(ip)

            # Determine device type
            device_type = self._detect_device_type(mac, hostname or "")
            vendor = self._mac_to_vendor(mac)

            now = datetime.utcnow()
            return NetworkDevice(
                mac_address=mac,
                ip_address=ip,
                hostname=hostname,
                vendor=vendor,
                first_seen=now,
                last_seen=now,
                device_type=device_type,
            )
        except Exception as e:
            print(f"Error creating device for IP {ip}: {e}")
            return None

    def _get_mac_from_ip(self, ip: str) -> Optional[str]:
        """Get MAC address for an IP using ARP"""
        try:
            result = subprocess.run(
                ["arp", "-a", ip], capture_output=True, text=True, timeout=3
            )

            # Parse MAC from ARP output
            # Format: hostname (xx:xx:xx:xx:xx:xx) at ...
            match = re.search(r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", result.stdout)
            if match:
                return match.group(0).replace("-", ":").upper()
        except:
            pass
        return None

    def _get_hostname(self, ip: str) -> Optional[str]:
        """Get hostname for an IP"""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except:
            return None

    async def check_wifi_security(self) -> WifiSecurityReport:
        """Perform a comprehensive WiFi security check"""

        # Get connected devices
        devices = await self.scan_network()

        # Analyze security
        security_type = await self._detect_security_type()

        # Count device types
        trusted = sum(1 for d in devices if d.is_trusted)
        unknown = sum(1 for d in devices if not d.is_trusted)
        iot = sum(1 for d in devices if d.device_type == "iot")

        # Build report
        report = WifiSecurityReport(
            network_name=self.ssid or "Unknown",
            security_type=security_type,
            encryption_strength=self._get_encryption_strength(security_type),
            has_default_password=False,  # Would need router access
            has_wps_enabled=False,  # Would need router access
            connected_devices=len(devices),
            trusted_devices=trusted,
            unknown_devices=unknown,
            iot_devices=iot,
            vulnerabilities=[],
            recommendations=[],
        )

        # Add recommendations based on findings
        if unknown > 3:
            report.vulnerabilities.append("Multiple unknown devices detected")
            report.recommendations.append("Review and mark known devices as trusted")

        if iot > 5:
            report.vulnerabilities.append("Many IoT devices may have weak security")
            report.recommendations.append("Isolate IoT devices on separate network")

        if security_type in ["WPA", "WEP", "None"]:
            report.vulnerabilities.append(f"Weak security type: {security_type}")
            report.recommendations.append("Upgrade to WPA3 or WPA2-AES")

        return report

    async def _detect_security_type(self) -> str:
        """Detect WiFi security type"""
        try:
            result = subprocess.run(
                [
                    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                    "-I",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.split("\n"):
                if "auth mode:" in line.lower():
                    auth_mode = line.split(":")[-1].strip().lower()
                    if "wpa3" in auth_mode:
                        return "WPA3"
                    elif "wpa2" in auth_mode:
                        return "WPA2"
                    elif "wpa" in auth_mode:
                        return "WPA"
                    elif "wep" in auth_mode:
                        return "WEP"
                    elif "none" in auth_mode:
                        return "Open"
        except:
            pass
        return "Unknown"

    def _get_encryption_strength(self, security_type: str) -> int:
        """Get encryption strength rating (1-5)"""
        strength_map = {
            "WPA3": 5,
            "WPA2": 4,
            "WPA": 2,
            "WEP": 1,
            "Open": 0,
            "Unknown": 3,
        }
        return strength_map.get(security_type, 3)

    def get_device(self, mac_address: str) -> Optional[NetworkDevice]:
        """Get a specific device by MAC"""
        return self.devices.get(mac_address.upper())

    def mark_device_trusted(self, mac_address: str, trusted: bool = True) -> bool:
        """Mark a device as trusted"""
        device = self.get_device(mac_address)
        if device:
            device.is_trusted = trusted
            return True
        return False

    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        device_counts = {
            "total": len(self.devices),
            "trusted": sum(1 for d in self.devices.values() if d.is_trusted),
            "unknown": sum(1 for d in self.devices.values() if not d.is_trusted),
            "by_type": {},
        }

        for device in self.devices.values():
            device_counts["by_type"][device.device_type] = (
                device_counts["by_type"].get(device.device_type, 0) + 1
            )

        return {
            "network_range": self.network_range,
            "gateway": self.gateway,
            "ssid": self.ssid,
            "devices": device_counts,
            "last_scan": datetime.utcnow().isoformat(),
        }

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices as dictionaries"""
        return [asdict(d) for d in self.devices.values()]


# MCP Tool functions
async def scan_network_devices(scan_range: Optional[str] = None) -> Dict[str, Any]:
    """Scan network for devices"""
    module = WifiSecurityModule()
    devices = await module.scan_network(scan_range)

    return {
        "devices": [asdict(d) for d in devices],
        "count": len(devices),
        "network_range": module.network_range,
        "ssid": module.ssid,
    }


async def check_wifi_security() -> Dict[str, Any]:
    """Check WiFi security status"""
    module = WifiSecurityModule()
    report = await module.check_wifi_security()
    return asdict(report)


def block_device(mac_address: str) -> Dict[str, Any]:
    """
    Block a device (simulated - would need router integration)
    In production, this would interface with router APIs
    """
    return {
        "success": False,
        "message": "Device blocking requires router integration (OpenWRT, UniFi, etc.)",
        "mac_address": mac_address,
        "note": "Configure router API in settings to enable device blocking",
    }


def get_network_stats() -> Dict[str, Any]:
    """Get network statistics"""
    module = WifiSecurityModule()
    return module.get_network_stats()


def get_device_info(mac_address: str) -> Dict[str, Any]:
    """Get information about a specific device"""
    module = WifiSecurityModule()
    device = module.get_device(mac_address)

    if device:
        return asdict(device)
    return {"error": "Device not found", "mac_address": mac_address}


def mark_device_trusted(mac_address: str, trusted: bool = True) -> Dict[str, Any]:
    """Mark a device as trusted or untrusted"""
    module = WifiSecurityModule()
    success = module.mark_device_trusted(mac_address, trusted)

    return {
        "success": success,
        "mac_address": mac_address,
        "trusted": trusted,
        "message": "Device marked as trusted"
        if trusted
        else "Device marked as untrusted",
    }
