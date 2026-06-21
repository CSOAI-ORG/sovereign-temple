#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MESH HEALTH DASHBOARD — Real-time monitoring for Dual-Mac Inference Mesh    ║
║                                                                              ║
║  Provides:                                                                   ║
║    • Terminal-based live dashboard (curses/rich)                             ║
║    • Prometheus /metrics endpoint for Grafana                                ║
║    • Alerting when nodes go offline or latency spikes                        ║
║    • Historical latency tracking (JSONL)                                     ║
║    • SOV3 coordination integration                                           ║
║                                                                              ║
║  Run: python mesh_health_dashboard.py [--port 9090] [--mode terminal|api]   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Deque

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

MESH_ORCHESTRATOR = os.environ.get("MESH_ORCHESTRATOR", "http://localhost:3202")
SOV3_COORDINATOR = os.environ.get("SOV3_COORDINATOR", "http://localhost:3101")
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", 9090))
HISTORY_FILE = Path.home() / "clawd" / "memory" / "mesh_health_history.jsonl"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
MAX_HISTORY = 1000

ALERT_LATENCY_THRESHOLD_MS = int(os.environ.get("ALERT_LATENCY_MS", 5000))
ALERT_OFFLINE_THRESHOLD_SEC = int(os.environ.get("ALERT_OFFLINE_SEC", 30))


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeSnapshot:
    node_id: str
    status: str
    latency_ms: float
    models_loaded: int
    last_seen: float
    throughput_tok_s: float = 0.0
    error_rate: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MeshSnapshot:
    timestamp: float
    nodes: Dict[str, NodeSnapshot]
    speculative_ready: bool
    total_throughput: float
    mesh_status: str
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "speculative_ready": self.speculative_ready,
            "total_throughput": self.total_throughput,
            "mesh_status": self.mesh_status,
            "alerts": self.alerts,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Health Collector
# ═══════════════════════════════════════════════════════════════════════════════

class HealthCollector:
    """Polls mesh orchestrator and collects health data."""

    def __init__(self, poll_interval_sec: float = 5.0):
        self.poll_interval = poll_interval_sec
        self.history: Deque[MeshSnapshot] = deque(maxlen=MAX_HISTORY)
        self.current: Optional[MeshSnapshot] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        while True:
            await self._poll_once()
            await asyncio.sleep(self.poll_interval)

    async def _poll_once(self):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{MESH_ORCHESTRATOR}/health")
                resp.raise_for_status()
                data = resp.json()

            nodes = {}
            for node_id, node_data in data.get("nodes", {}).items():
                nodes[node_id] = NodeSnapshot(
                    node_id=node_id,
                    status=node_data.get("status", "unknown"),
                    latency_ms=node_data.get("latency_ms", 99999),
                    models_loaded=len(node_data.get("models_loaded", [])),
                    last_seen=node_data.get("last_seen", 0),
                    throughput_tok_s=node_data.get("throughput_tok_s", 0.0),
                )

            snapshot = MeshSnapshot(
                timestamp=time.time(),
                nodes=nodes,
                speculative_ready=data.get("speculative_ready", False),
                total_throughput=data.get("total_throughput_tok_s", 0.0),
                mesh_status=data.get("mesh_status", "unknown"),
                alerts=self._generate_alerts(nodes),
            )

            self.current = snapshot
            self.history.append(snapshot)

            # Persist to JSONL
            with open(HISTORY_FILE, "a") as f:
                f.write(json.dumps(snapshot.to_dict()) + "\n")

        except Exception as e:
            # Create degraded snapshot
            self.current = MeshSnapshot(
                timestamp=time.time(),
                nodes={},
                speculative_ready=False,
                total_throughput=0.0,
                mesh_status=f"collector_error: {e}",
                alerts=[f"Cannot reach mesh orchestrator at {MESH_ORCHESTRATOR}"],
            )

    def _generate_alerts(self, nodes: Dict[str, NodeSnapshot]) -> List[str]:
        alerts = []
        now = time.time()
        for node_id, node in nodes.items():
            if node.status != "online":
                alerts.append(f"CRITICAL: Node {node_id} is {node.status}")
            elif node.latency_ms > ALERT_LATENCY_THRESHOLD_MS:
                alerts.append(f"WARNING: Node {node_id} latency {node.latency_ms:.0f}ms > {ALERT_LATENCY_THRESHOLD_MS}ms")
            elif now - node.last_seen > ALERT_OFFLINE_THRESHOLD_SEC:
                alerts.append(f"WARNING: Node {node_id} stale ({now - node.last_seen:.0f}s since last seen)")
        return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# Terminal Dashboard (Rich)
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalDashboard:
    """Live terminal dashboard using Rich (if available) or simple prints."""

    def __init__(self, collector: HealthCollector):
        self.collector = collector
        self._task: Optional[asyncio.Task] = None
        self._rich_available = False
        try:
            from rich.live import Live
            from rich.table import Table
            from rich.console import Console
            from rich.panel import Panel
            self._rich_available = True
            self.console = Console()
        except ImportError:
            pass

    async def start(self):
        if self._rich_available:
            self._task = asyncio.create_task(self._rich_loop())
        else:
            self._task = asyncio.create_task(self._simple_loop())

    async def _rich_loop(self):
        from rich.live import Live
        from rich.table import Table
        from rich.panel import Panel
        from rich.layout import Layout
        from rich.text import Text

        with Live(refresh_per_second=1) as live:
            while True:
                snapshot = self.collector.current
                if not snapshot:
                    live.update(Text("Waiting for first poll...", style="yellow"))
                    await asyncio.sleep(1)
                    continue

                # Build node table
                table = Table(title=f"🌐 Mac Mesh Health — {datetime.fromtimestamp(snapshot.timestamp).strftime('%H:%M:%S')}")
                table.add_column("Node", style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Latency", justify="right")
                table.add_column("Models", justify="right")
                table.add_column("Throughput", justify="right")

                for node_id, node in snapshot.nodes.items():
                    status_style = "green" if node.status == "online" else "red"
                    latency_str = f"{node.latency_ms:.0f}ms" if node.latency_ms < 10000 else "∞"
                    table.add_row(
                        node_id,
                        f"[{status_style}]{node.status}[/{status_style}]",
                        latency_str,
                        str(node.models_loaded),
                        f"{node.throughput_tok_s:.0f} tok/s",
                    )

                # Speculative status
                spec_text = "✅ Available" if snapshot.speculative_ready else "❌ Unavailable"
                spec_style = "green" if snapshot.speculative_ready else "red"

                # Alerts panel
                if snapshot.alerts:
                    alerts_text = "\n".join(f"• {a}" for a in snapshot.alerts)
                    alerts_panel = Panel(alerts_text, title="🚨 Alerts", border_style="red")
                else:
                    alerts_panel = Panel("All systems operational", title="✅ Alerts", border_style="green")

                # Layout
                layout = Layout()
                layout.split_column(
                    Layout(Panel(f"Mesh Status: {snapshot.mesh_status} | Speculative: [{spec_style}]{spec_text}[/{spec_style}] | Total Throughput: {snapshot.total_throughput:.0f} tok/s", title="Overview")),
                    Layout(table),
                    Layout(alerts_panel, size=5 + len(snapshot.alerts)),
                )

                live.update(layout)
                await asyncio.sleep(1)

    async def _simple_loop(self):
        """Fallback for systems without Rich."""
        while True:
            snapshot = self.collector.current
            if snapshot:
                print(f"\n{'='*60}")
                print(f"MESH HEALTH — {datetime.fromtimestamp(snapshot.timestamp).strftime('%H:%M:%S')}")
                print(f"Status: {snapshot.mesh_status} | Speculative: {'YES' if snapshot.speculative_ready else 'NO'}")
                print(f"{'-'*60}")
                for node_id, node in snapshot.nodes.items():
                    status_icon = "✅" if node.status == "online" else "❌"
                    print(f"{status_icon} {node_id:10} | {node.status:8} | {node.latency_ms:6.0f}ms | {node.models_loaded} models")
                if snapshot.alerts:
                    print(f"{'-'*60}")
                    for alert in snapshot.alerts:
                        print(f"🚨 {alert}")
                print(f"{'='*60}")
            await asyncio.sleep(5)


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI Metrics Server
# ═══════════════════════════════════════════════════════════════════════════════

def create_metrics_app(collector: HealthCollector) -> FastAPI:
    app = FastAPI(title="Mesh Health Metrics")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/")
    async def root():
        return {"service": "mesh_health_dashboard", "mode": "api"}

    @app.get("/health")
    async def health():
        snap = collector.current
        if not snap:
            return {"status": "starting"}
        return snap.to_dict()

    @app.get("/metrics")
    async def prometheus():
        """Prometheus-compatible metrics for Grafana."""
        snap = collector.current
        if not snap:
            return "# No data yet"

        lines = [
            "# HELP mesh_nodes_total Total nodes in mesh",
            "# TYPE mesh_nodes_total gauge",
            f'mesh_nodes_total {len(snap.nodes)}',
            "",
            "# HELP mesh_nodes_online Nodes currently online",
            "# TYPE mesh_nodes_online gauge",
            f'mesh_nodes_online {sum(1 for n in snap.nodes.values() if n.status == "online")}',
            "",
            "# HELP mesh_speculative_ready Speculative decoding available",
            "# TYPE mesh_speculative_ready gauge",
            f'mesh_speculative_ready {1 if snap.speculative_ready else 0}',
            "",
            "# HELP mesh_total_throughputtok_s Aggregate throughput",
            "# TYPE mesh_total_throughputtok_s gauge",
            f'mesh_total_throughputtok_s {snap.total_throughput}',
        ]

        for node_id, node in snap.nodes.items():
            safe_id = node_id.replace('-', '_')
            lines.extend([
                f'mesh_node_latency_ms{{node="{safe_id}"}} {node.latency_ms}',
                f'mesh_node_models{{node="{safe_id}"}} {node.models_loaded}',
                f'mesh_node_online{{node="{safe_id}"}} {1 if node.status == "online" else 0}',
            ])

        return "\n".join(lines)

    @app.get("/history")
    async def history(minutes: int = 60):
        """Return recent history snapshots."""
        cutoff = time.time() - (minutes * 60)
        recent = [s.to_dict() for s in collector.history if s.timestamp > cutoff]
        return {"snapshots": recent, "count": len(recent)}

    @app.get("/sov3")
    async def sov3_proxy():
        """Proxy SOV3 status."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{SOV3_COORDINATOR}/mcp/coord_get_dashboard")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            return {"status": "sovereign_mode", "error": str(e)[:100]}

    return app


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Mesh Health Dashboard")
    parser.add_argument("--port", type=int, default=DASHBOARD_PORT, help="API port")
    parser.add_argument("--mode", choices=["terminal", "api", "both"], default="both", help="Display mode")
    parser.add_argument("--poll", type=float, default=5.0, help="Poll interval seconds")
    args = parser.parse_args()

    collector = HealthCollector(poll_interval_sec=args.poll)
    await collector.start()

    # Wait for first poll
    while collector.current is None:
        await asyncio.sleep(0.5)

    tasks = []

    if args.mode in ("terminal", "both"):
        dashboard = TerminalDashboard(collector)
        await dashboard.start()
        tasks.append(dashboard._task)

    if args.mode in ("api", "both"):
        import uvicorn
        app = create_metrics_app(collector)
        config = uvicorn.Config(app, host="0.0.0.0", port=args.port, log_level="warning")
        server = uvicorn.Server(config)
        tasks.append(asyncio.create_task(server.serve()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
