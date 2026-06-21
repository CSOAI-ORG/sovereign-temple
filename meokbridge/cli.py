#!/usr/bin/env python3
"""
MEOKBRIDGE CLI — One command to connect everything
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional

from .core import MeokBridge, Node, NodeType, NodeCapability
from .config import BridgeConfig
from .discovery import NodeDiscovery


def print_banner():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                    MEOKBRIDGE v1.0                             ║
║           Universal Compute & Service Connector                ║
╚════════════════════════════════════════════════════════════════╝
""")


def cmd_add(args):
    """Add a node to MEOKBRIDGE."""
    config = BridgeConfig(args.config)
    node = Node(
        id=args.id,
        name=args.name or args.id,
        node_type=NodeType(args.type),
        url=args.url,
        api_key=args.api_key,
        priority=args.priority,
        tags=args.tag or [],
        transport=args.transport,
        command=args.command,
    )
    config.add_node(node)
    print(f"✅ Added {args.type} node: {args.id} -> {args.url}")


def cmd_remove(args):
    """Remove a node."""
    config = BridgeConfig(args.config)
    cfg = config.load()
    original = len(cfg.get("nodes", []))
    cfg["nodes"] = [n for n in cfg.get("nodes", []) if n.get("id") != args.id]
    config.save(cfg)
    removed = original - len(cfg["nodes"])
    if removed:
        print(f"✅ Removed node: {args.id}")
    else:
        print(f"⚠️  Node not found: {args.id}")


def cmd_list(args):
    """List all configured nodes."""
    config = BridgeConfig(args.config)
    nodes = config.load_nodes()

    if not nodes:
        print("No nodes configured. Add one with: meokbridge add")
        return

    print(f"\n{'ID':<20} {'Type':<12} {'URL':<35} {'Priority':<8} {'Tags'}")
    print("-" * 100)
    for n in nodes:
        tags = ", ".join(n.tags) if n.tags else "-"
        print(f"{n.id:<20} {n.node_type.value:<12} {n.url:<35} {n.priority:<8} {tags}")
    print()


async def cmd_scan(args):
    """Scan network for inference nodes."""
    print("🔍 Scanning network for inference nodes...")
    discovery = NodeDiscovery(timeout_sec=args.timeout)

    all_nodes = []

    # mDNS discovery
    print("  → Checking mDNS/Bonjour hosts...")
    mdns_nodes = await discovery.discover_mdns()
    all_nodes.extend(mdns_nodes)
    print(f"     Found {len(mdns_nodes)} via mDNS")

    # Vast tunnel discovery
    print("  → Checking for Vast.ai SSH tunnels...")
    vast_nodes = await discovery.discover_vast_tunnel()
    all_nodes.extend(vast_nodes)
    print(f"     Found {len(vast_nodes)} via tunnel ports")

    # LAN scan (optional, can be slow)
    if args.lan:
        print("  → Scanning local subnet (this may take a minute)...")
        lan_nodes = await discovery.discover_lan()
        all_nodes.extend(lan_nodes)
        print(f"     Found {len(lan_nodes)} via LAN scan")

    print(f"\n✅ Total discovered: {len(all_nodes)} nodes\n")

    if all_nodes:
        config = BridgeConfig(args.config)
        for node in all_nodes:
            config.add_node(node)
            print(f"  + Added: {node.name} ({node.url})")
        print(f"\n💾 Saved to {config.path}")
    else:
        print("💡 No nodes found. Try:")
        print("   • Make sure Ollama is running: ollama serve")
        print("   • Check your SSH tunnel: ssh -L 11436:localhost:11434 root@<vast-ip>")
        print("   • Use --lan for full subnet scan")


async def cmd_chat(args):
    """Chat through MEOKBRIDGE."""
    config = BridgeConfig(args.config)
    bridge = MeokBridge()
    for node in config.load_nodes():
        bridge.add_node(node)

    # Quick health check
    await bridge.health_check()

    print(f"💬 MEOKBRIDGE Chat → {args.node or 'auto-routed'}\n")
    print("Type your message, or 'exit' to quit.\n")

    while True:
        try:
            msg = input("You: ").strip()
            if msg.lower() in ("exit", "quit", "q"):
                break
            if not msg:
                continue

            result = await bridge.chat(
                msg,
                node_id=args.node,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                prefer_local=args.local,
            )

            print(f"\n[{result.node_id}] {result.model} | {result.latency_ms:.0f}ms")
            print(f"{result.text}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}\n")


async def cmd_council(args):
    """Council mode: query multiple nodes."""
    config = BridgeConfig(args.config)
    bridge = MeokBridge()
    for node in config.load_nodes():
        bridge.add_node(node)

    print(f"🏛️  Council Mode — Querying all online nodes...\n")
    result = await bridge.council_chat(args.message)

    print(f"Consensus: {result['consensus_score']:.0%} agreement ({result['total_nodes']} nodes)")
    print(f"Failed: {result['failed_nodes']} | Latency: {result['total_latency_ms']:.0f}ms")
    print(f"\n📜 Consensus Answer:\n{result['consensus_text']}\n")

    if args.verbose:
        print("Individual Responses:")
        for resp in result['responses']:
            print(f"  [{resp['node']}] {resp['model']}: {resp['text'][:200]}...")


async def cmd_health(args):
    """Check health of all nodes."""
    config = BridgeConfig(args.config)
    bridge = MeokBridge()
    for node in config.load_nodes():
        bridge.add_node(node)

    print("🏥 Health Check...\n")
    statuses = await bridge.health_check()

    for node_id, status in statuses.items():
        icon = "🟢" if status.value == "online" else "🟡" if status.value == "degraded" else "🔴"
        print(f"  {icon} {node_id:<20} {status.value}")
    print()


def cmd_config(args):
    """Show or edit config."""
    config = BridgeConfig(args.config)
    if args.edit:
        import subprocess
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(config.path)])
    else:
        print(f"Config path: {config.path}")
        with open(config.path) as f:
            print(f.read())


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="meokbridge",
        description="Universal connector for AI compute and services",
    )
    parser.add_argument("--config", "-c", help="Path to config file", default=None)
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add
    add_parser = subparsers.add_parser("add", help="Add a node")
    add_parser.add_argument("id", help="Unique node ID")
    add_parser.add_argument("type", choices=[t.value for t in NodeType], help="Node type")
    add_parser.add_argument("url", help="Node URL")
    add_parser.add_argument("--name", help="Display name")
    add_parser.add_argument("--api-key", help="API key (or ${ENV_VAR})")
    add_parser.add_argument("--priority", type=int, default=0, help="Routing priority")
    add_parser.add_argument("--tag", action="append", help="Tag (repeatable)")
    add_parser.add_argument("--transport", help="Transport (stdio/sse/http)")
    add_parser.add_argument("--command", help="Command (for stdio MCP)")
    add_parser.set_defaults(func=cmd_add)

    # remove
    rm_parser = subparsers.add_parser("remove", help="Remove a node")
    rm_parser.add_argument("id", help="Node ID to remove")
    rm_parser.set_defaults(func=cmd_remove)

    # list
    list_parser = subparsers.add_parser("list", help="List nodes")
    list_parser.set_defaults(func=cmd_list)

    # scan
    scan_parser = subparsers.add_parser("scan", help="Auto-discover nodes")
    scan_parser.add_argument("--lan", action="store_true", help="Full LAN subnet scan")
    scan_parser.add_argument("--timeout", type=float, default=2.0, help="Timeout per check")
    scan_parser.set_defaults(func=lambda args: asyncio.run(cmd_scan(args)))

    # chat
    chat_parser = subparsers.add_parser("chat", help="Interactive chat")
    chat_parser.add_argument("--node", help="Specific node ID")
    chat_parser.add_argument("--temperature", type=float, default=0.7)
    chat_parser.add_argument("--max-tokens", type=int, default=2048)
    chat_parser.add_argument("--local", action="store_true", help="Prefer local nodes")
    chat_parser.set_defaults(func=lambda args: asyncio.run(cmd_chat(args)))

    # council
    council_parser = subparsers.add_parser("council", help="Council mode (multi-node)")
    council_parser.add_argument("message", help="Message to send")
    council_parser.add_argument("--verbose", "-v", action="store_true")
    council_parser.set_defaults(func=lambda args: asyncio.run(cmd_council(args)))

    # health
    health_parser = subparsers.add_parser("health", help="Check node health")
    health_parser.set_defaults(func=lambda args: asyncio.run(cmd_health(args)))

    # config
    config_parser = subparsers.add_parser("config", help="Show/edit config")
    config_parser.add_argument("--edit", action="store_true", help="Open in editor")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)


if __name__ == "__main__":
    main()
