#!/usr/bin/env python3
"""
JARVIS CLI - Command line interface
Usage: jarvis [command] [args]
"""

import sys
import os
import json
import argparse
import subprocess

# Add parent dir to path
sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")

BASE_URL = "http://localhost:3200"


def call_tool(tool: str, args: dict = None) -> dict:
    """Call MCP tool"""
    import httpx

    if args is None:
        args = {}

    r = httpx.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
            "id": "cli",
        },
        timeout=60,
    )

    data = r.json()
    if "result" in data and "content" in data["result"]:
        return json.loads(data["result"]["content"][0]["text"])
    return {"error": "No result"}


def cmd_chat(args):
    """Chat with JARVIS"""
    result = call_tool("ask_sovereign", {"message": args.message})
    print(f"\n🤖 JARVIS: {result.get('response', 'No response')}")


def cmd_voice(args):
    """Use voice mode"""
    print("Starting voice mode...")
    os.chdir("/Users/nicholas/clawd/sovereign-temple")
    subprocess.run(
        [
            "source",
            "jarvis-env/bin/activate",
            "&&",
            "python",
            "voice_pipeline/jarvis_conversational.py",
            "demo",
        ],
        shell=True,
    )


def cmd_status(args):
    """Get system status"""
    health = call_tool("get_health")
    caps = call_tool("get_capabilities")
    metrics = call_tool("get_metrics")

    print(f"""
╔══════════════════════════════════════════╗
║          JARVIS SYSTEM STATUS             ║
╠══════════════════════════════════════════╣
║ Status: {health.get("status", "unknown"):<35}║
║ Uptime: {health.get("uptime", "?")}s{" " * 28}║
║                                          ║
║ Tools: {caps.get("tools", 0):<35}║
║ Providers: {caps.get("providers", 0):<30}║
║                                          ║
║ Requests: {metrics.get("requests", {}).get("total", 0):<32}║
║ CPU: {metrics.get("system", {}).get("cpu_percent", 0):.1f}%{" " * 31}║
║ Memory: {metrics.get("system", {}).get("memory_percent", 0):.1f}%{" " * 30}║
╚══════════════════════════════════════════╝
""")


def cmd_tools(args):
    """List all tools"""
    import httpx

    r = httpx.post(
        f"{BASE_URL}/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": "cli"}
    )
    tools = r.json()["result"]["tools"]

    print(f"\n📦 Available Tools ({len(tools)}):")
    for tool in sorted(tools, key=lambda t: t["name"]):
        print(f"  • {tool['name']}")


def cmd_remember(args):
    """Remember a fact"""
    result = call_tool(
        "remember_fact", {"fact": args.fact, "category": args.category or "general"}
    )
    print(f"\n✅ {result.get('status', 'done')}")


def cmd_info(args):
    """Get user info"""
    result = call_tool("get_user_info")
    print(f"\n📚 User Facts:")
    for key, val in result.get("facts", {}).items():
        print(f"  {key}: {val}")


def cmd_search(args):
    """Search memory"""
    result = call_tool("search_memory", {"query": args.query})
    print(f"\n🔍 Results:")
    for r in result.get("results", []):
        print(f"  - {r.get('content', '')[:80]}")


def cmd_speak(args):
    """Speak text"""
    import requests

    r = requests.post(f"{BASE_URL}/speak", json={"text": args.text})
    if r.status_code == 200:
        print(f"\n🔊 Playing TTS...")
        # Play audio
        import subprocess

        subprocess.run(["afplay", "/dev/stdin"], input=r.content)
    else:
        print(f"\n❌ TTS failed")


def cmd_websearch(args):
    """Web search"""
    result = call_tool("web_search", {"query": args.query, "limit": args.limit or 5})
    print(f"\n🌐 Results for '{args.query}':")
    for i, r in enumerate(result.get("results", [])[:5], 1):
        print(f"  {i}. {r.get('title', 'No title')}")


def cmd_metrics(args):
    """Get metrics"""
    result = call_tool("get_metrics")
    print(json.dumps(result, indent=2))


def cmd_test(args):
    """Run tests"""
    import jarvis_test

    results = jarvis_test.run_tests()
    print(f"\n{'=' * 50}")
    print(f"RESULTS: {results['passed']}/{results['total']} passed")
    print(f"{'=' * 50}")
    for r in results["results"]:
        icon = "✅" if r["status"] == "pass" else "❌"
        print(f"{icon} {r['category']}: {r['name']}")


def cmd_docs(args):
    """Open documentation"""
    print("\n📖 Documentation:")
    print("  - API: /Users/nicholas/clawd/sovereign-temple/docs/API.md")
    print(
        "  - Voice: /Users/nicholas/clawd/sovereign-temple/docs/JARVIS_VOICE_GUIDE.md"
    )
    print(
        "  - Architecture: /Users/nicholas/clawd/sovereign-temple/docs/VOICE_ARCHITECTURE.md"
    )


def main():
    parser = argparse.ArgumentParser(
        description="JARVIS CLI - Your AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers()

    # chat
    chat_parser = subparsers.add_parser("chat", help="Chat with JARVIS")
    chat_parser.add_argument("message", help="Message to send")
    chat_parser.set_defaults(func=cmd_chat)

    # voice
    subparsers.add_parser("voice", help="Use voice mode").set_defaults(func=cmd_voice)

    # status
    subparsers.add_parser("status", help="Get system status").set_defaults(
        func=cmd_status
    )

    # tools
    subparsers.add_parser("tools", help="List all tools").set_defaults(func=cmd_tools)

    # remember
    remember_parser = subparsers.add_parser("remember", help="Remember a fact")
    remember_parser.add_argument("fact", help="Fact to remember")
    remember_parser.add_argument("-c", "--category", help="Category")
    remember_parser.set_defaults(func=cmd_remember)

    # info
    subparsers.add_parser("info", help="Get user info").set_defaults(func=cmd_info)

    # search
    search_parser = subparsers.add_parser("search", help="Search memory")
    search_parser.add_argument("query", help="Search query")
    search_parser.set_defaults(func=cmd_search)

    # speak
    speak_parser = subparsers.add_parser("speak", help="Speak text")
    speak_parser.add_argument("text", help="Text to speak")
    speak_parser.set_defaults(func=cmd_speak)

    # websearch
    web_parser = subparsers.add_parser("web", help="Web search")
    web_parser.add_argument("query", help="Search query")
    web_parser.add_argument("-l", "--limit", type=int, help="Limit results")
    web_parser.set_defaults(func=cmd_websearch)

    # metrics
    subparsers.add_parser("metrics", help="Get metrics").set_defaults(func=cmd_metrics)

    # test
    subparsers.add_parser("test", help="Run tests").set_defaults(func=cmd_test)

    # docs
    subparsers.add_parser("docs", help="Show documentation").set_defaults(func=cmd_docs)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
