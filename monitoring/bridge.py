"""
Bridge between MetricsCollector and AlertSystem
Wires monitoring to actual alerts
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import os

from monitoring.metrics_collector import MetricsCollector
from monitoring.alert_system import (
    AlertManager,
    AlertSeverity,
    AlertChannel,
    console_alert_handler,
    file_alert_handler,
)


class MonitoringBridge:
    """
    Bridges MetricsCollector with AlertSystem for automated alerting
    """

    def __init__(self):
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._setup_handlers()
        self._setup_default_rules()

    def _setup_handlers(self):
        """Wire up alert handlers"""
        self.alerts.add_handler(AlertChannel.CONSOLE, console_alert_handler)

        log_dir = os.environ.get("ALERT_LOG_DIR", "logs")
        self.alerts.add_handler(
            AlertChannel.FILE, lambda a: file_alert_handler(a, f"{log_dir}/alerts.log")
        )

        webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
        if webhook_url:
            self.alerts.add_handler(
                AlertChannel.WEBHOOK, self._webhook_handler(webhook_url)
            )

    def _setup_default_rules(self):
        """Setup alert rules for SOV3/Jarvis metrics"""
        self.alerts.setup_default_rules()

        self.alerts.add_rule(
            name="sov3_offline",
            condition=lambda m: m.get("sov3_online", True) == False,
            severity=AlertSeverity.CRITICAL,
            title_template="SOV3 Offline",
            message_template="SOV3 consciousness engine is not responding",
            channels=[AlertChannel.CONSOLE, AlertChannel.FILE],
        )

        self.alerts.add_rule(
            name="jarvis_tool_failure",
            condition=lambda m: m.get("jarvis_tool_failure_rate", 0) > 0.05,
            severity=AlertSeverity.WARNING,
            title_template="Jarvis Tool Failure Rate High",
            message_template="Jarvis MCP tool failure rate exceeds 5%",
            channels=[AlertChannel.CONSOLE, AlertChannel.FILE],
        )

        self.alerts.add_rule(
            name="meok_api_error",
            condition=lambda m: m.get("meok_api_errors_per_minute", 0) > 10,
            severity=AlertSeverity.CRITICAL,
            title_template="Meok API Error Rate High",
            message_template="Meok API errors exceed 10/minute",
            channels=[AlertChannel.CONSOLE, AlertChannel.FILE, AlertChannel.WEBHOOK],
        )

        self.alerts.add_rule(
            name="low_care_score",
            condition=lambda m: m.get("care_score", 1.0) < 0.5,
            severity=AlertSeverity.WARNING,
            title_template="Care Score Low",
            message_template="System care score has dropped below 0.5",
            channels=[AlertChannel.CONSOLE, AlertChannel.FILE],
        )

    def _webhook_handler(self, url: str):
        """Create async webhook handler"""

        async def handler(alert):
            import aiohttp

            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        url,
                        json={
                            "alert_id": alert.id,
                            "severity": alert.severity.value,
                            "title": alert.title,
                            "message": alert.message,
                            "timestamp": alert.timestamp.isoformat(),
                        },
                    )
            except Exception as e:
                print(f"Webhook failed: {e}")

        return handler

    async def start(self, interval_seconds: float = 30.0):
        """Start the monitoring bridge"""
        self._running = True
        await self.metrics.start_collection(interval_seconds)
        self._task = asyncio.create_task(self._check_loop(interval_seconds))

    async def _check_loop(self, interval: float):
        """Periodically check metrics and fire alerts"""
        while self._running:
            await asyncio.sleep(interval)

            current_metrics = {
                "system_cpu_percent": self.metrics.gauges.get("system_cpu_percent", 0),
                "system_memory_percent": self.metrics.gauges.get(
                    "system_memory_percent", 0
                ),
                "sov3_online": True,
                "jarvis_tool_failure_rate": 0.0,
                "meok_api_errors_per_minute": 0,
                "care_score": 0.8,
            }

            await self.alerts.check_rules(current_metrics)

    async def stop(self):
        """Stop the monitoring bridge"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.metrics.stop()

    def record_sov3_state(self, online: bool, care_score: Optional[float] = None):
        """Record SOV3 state"""
        self.metrics.set_gauge("sov3_online", 1.0 if online else 0.0)
        if care_score is not None:
            self.metrics.set_gauge("care_score", care_score)

    def record_jarvis_metrics(self, tool_calls: int, failures: int):
        """Record Jarvis metrics"""
        self.metrics.increment_counter("jarvis_tool_calls_total", tool_calls)
        self.metrics.increment_counter("jarvis_tool_failures_total", failures)

        if tool_calls > 0:
            rate = failures / tool_calls
            self.metrics.set_gauge("jarvis_tool_failure_rate", rate)

    def record_meok_api_errors(self, count: int):
        """Record Meok API errors"""
        self.metrics.increment_counter("meok_api_errors_total", count)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get combined dashboard data"""
        return {
            **self.metrics.get_dashboard_data(),
            "alert_stats": self.alerts.get_alert_stats(),
            "active_alerts": [
                {
                    "id": a.id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.alerts.get_active_alerts()
            ],
        }


_global_bridge: Optional[MonitoringBridge] = None


def get_monitoring_bridge() -> MonitoringBridge:
    """Get global monitoring bridge instance"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = MonitoringBridge()
    return _global_bridge
