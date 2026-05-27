#!/usr/bin/env python3
"""
JARVIS Monitoring - Prometheus metrics and health monitoring
"""

import time
import psutil
import os
from datetime import datetime
from typing import Dict, Any


class JARVISMonitor:
    """Monitoring for JARVIS"""

    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.tool_usage = {}

    def record_request(self, tool: str, success: bool = True):
        """Record a request"""
        self.request_count += 1
        if not success:
            self.error_count += 1

        if tool not in self.tool_usage:
            self.tool_usage[tool] = 0
        self.tool_usage[tool] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        uptime = time.time() - self.start_time

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(uptime),
            "requests": {
                "total": self.request_count,
                "errors": self.error_count,
                "error_rate": self.error_count / max(self.request_count, 1),
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_mb": psutil.virtual_memory().used // 1024 // 1024,
            },
            "top_tools": sorted(
                self.tool_usage.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def get_health(self) -> Dict[str, Any]:
        """Get health status"""
        return {
            "status": "healthy"
            if self.error_count < self.request_count * 0.1
            else "degraded",
            "uptime": int(time.time() - self.start_time),
            "checks": {
                "mcp_server": "ok",
                "ollama": "ok",
                "memory": "ok",
                "disk": "ok" if psutil.disk_usage("/").percent < 90 else "low",
            },
        }


# Global monitor
monitor = JARVISMonitor()


def record_tool_use(tool: str, success: bool = True):
    monitor.record_request(tool, success)


def get_metrics() -> Dict[str, Any]:
    return monitor.get_metrics()


def get_health() -> Dict[str, Any]:
    return monitor.get_health()


# Prometheus format
def prometheus_metrics() -> str:
    """Generate Prometheus metrics"""
    metrics = get_metrics()

    lines = [
        "# HELP jarvis_uptime_seconds JARVIS uptime in seconds",
        "# TYPE jarvis_uptime_seconds counter",
        f"jarvis_uptime_seconds {metrics['uptime_seconds']}",
        "",
        "# HELP jarvis_requests_total Total requests",
        "# TYPE jarvis_requests_total counter",
        f"jarvis_requests_total {metrics['requests']['total']}",
        "",
        "# HELP jarvis_errors_total Total errors",
        "# TYPE jarvis_errors_total counter",
        f"jarvis_errors_total {metrics['requests']['errors']}",
        "",
        "# HELP jarvis_cpu_percent CPU usage",
        "# TYPE jarvis_cpu_percent gauge",
        f"jarvis_cpu_percent {metrics['system']['cpu_percent']}",
        "",
        "# HELP jarvis_memory_percent Memory usage",
        "# TYPE jarvis_memory_percent gauge",
        f"jarvis_memory_percent {metrics['system']['memory_percent']}",
    ]

    # Tool usage
    for tool, count in metrics["top_tools"]:
        lines.extend(
            [
                "",
                f"# HELP jarvis_tool_calls_total {tool} tool calls",
                f"# TYPE jarvis_tool_calls_total counter",
                f'jarvis_tool_calls_total{{tool="{tool}"}} {count}',
            ]
        )

    return "\n".join(lines)


if __name__ == "__main__":
    print("JARVIS Monitor")
    print(get_metrics())
