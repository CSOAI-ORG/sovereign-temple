#!/usr/bin/env python3
"""
Topology Refresh — Pulls live data from all sources and rebuilds live_graph.json.

Sources:
  1. SOV3 health + memory stats
  2. NATS JetStream stream stats
  3. Vercel project list (if VERCEL_TOKEN set)
  4. PyPI download counts (cached, hourly)

Usage:
    python3 topology_refresh.py              # Refresh once
    python3 topology_refresh.py --daemon     # Refresh every 5 minutes
"""
import json
import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "_TOPOLOGY" / "live_graph.json"
SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
NATS_URL = os.environ.get("NATS_MONITOR", "http://localhost:8222")
DASHBOARD_BUILD = Path(__file__).parent.parent / "topology-dashboard" / "build.py"


def refresh_sov3_node(nodes):
    """Update SOV3 infrastructure node with live data."""
    try:
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        health = r.json()
        for node in nodes:
            if node.get("name") == "SOV3":
                cons = health.get("components", {}).get("consciousness", {})
                node["status"] = health.get("status", "unknown")
                node["consciousness_level"] = round(cons.get("consciousness_level", 0) * 100, 1)
                node["emotional_state"] = cons.get("emotional_summary", {}).get("trend", "unknown")
                node["reflections"] = cons.get("reflections", 0)
                node["dreams"] = cons.get("dreams", 0)
                node["agents"] = len(health.get("components", {}).get("neural_models", {}))

                # Models
                models = health.get("components", {}).get("neural_models", {})
                trained = sum(1 for m in models.values() if isinstance(m, dict) and m.get("is_trained"))
                node["trained_models"] = trained
                break

        # Memory count
        r2 = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "method": "tools/call", "id": "refresh",
            "params": {"name": "get_memory_stats", "arguments": {}}
        }, timeout=10)
        result = r2.json().get("result", {})
        if isinstance(result, dict):
            content = result.get("content", [{}])
            if isinstance(content, list) and content:
                text = content[0].get("text", "{}")
                stats = json.loads(text)
                for node in nodes:
                    if node.get("name") == "SOV3":
                        node["memories"] = stats.get("total_episodes", 0)
                        break

        print(f"  SOV3: refreshed ✅")
    except Exception as e:
        print(f"  SOV3: {e}")


def refresh_nats_node(nodes):
    """Update NATS infrastructure data."""
    try:
        r = requests.get(f"{NATS_URL}/jsz", timeout=3)
        jsz = r.json()
        streams = jsz.get("streams", 0)
        consumers = jsz.get("consumers", 0)
        messages = jsz.get("messages", 0)

        # Add NATS node if not exists
        nats_exists = any(n.get("name") == "NATS JetStream" for n in nodes)
        if not nats_exists:
            nodes.append({
                "id": f"n{len(nodes)+100}",
                "category": "infrastructure",
                "name": "NATS JetStream",
                "port": 4222,
                "status": "healthy",
                "streams": streams,
                "consumers": consumers,
                "messages": messages,
            })
        else:
            for node in nodes:
                if node.get("name") == "NATS JetStream":
                    node["status"] = "healthy"
                    node["streams"] = streams
                    node["consumers"] = consumers
                    node["messages"] = messages
                    break

        print(f"  NATS: {streams} streams, {messages} msgs ✅")
    except Exception as e:
        print(f"  NATS: {e}")


def refresh_ollama_node(nodes):
    """Update Ollama model list."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        for node in nodes:
            if node.get("name") == "Ollama Local":
                node["models"] = models
                node["status"] = "healthy"
                break
        print(f"  Ollama: {len(models)} models ✅")
    except Exception as e:
        print(f"  Ollama: {e}")


def refresh_hermes_node(nodes):
    """Check Hermes status."""
    try:
        r = requests.get("http://localhost:3000/health", timeout=3)
        status = "healthy" if r.status_code == 200 else "degraded"
        for node in nodes:
            if node.get("name") == "Hermes":
                node["status"] = status
                break
        print(f"  Hermes: {status}")
    except:
        for node in nodes:
            if node.get("name") == "Hermes":
                node["status"] = "disconnected"
                break
        print(f"  Hermes: disconnected")


def refresh():
    """Full topology refresh."""
    print(f"Topology refresh at {datetime.now().strftime('%H:%M:%S')}")

    # Load current graph
    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    nodes = graph["nodes"]

    # Refresh all sources
    refresh_sov3_node(nodes)
    refresh_nats_node(nodes)
    refresh_ollama_node(nodes)
    refresh_hermes_node(nodes)

    # Update timestamp
    graph["last_refresh"] = datetime.now().isoformat()
    graph["generated"] = graph.get("generated", datetime.now().isoformat())

    # Save
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"  Graph saved: {len(nodes)} nodes, {len(graph['edges'])} edges")

    # Rebuild dashboard if build.py exists
    if DASHBOARD_BUILD.exists():
        os.system(f"cd {DASHBOARD_BUILD.parent} && python3 build.py --live > /dev/null 2>&1")
        print(f"  Dashboard rebuilt ✅")

    return graph


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        print("Topology refresh daemon starting (every 5 min)...")
        while True:
            try:
                refresh()
            except Exception as e:
                print(f"  Refresh error: {e}")
            print()
            time.sleep(300)
    else:
        refresh()
