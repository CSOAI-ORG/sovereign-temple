#!/usr/bin/env python3
"""
SOV3 Bridge Network - Unified Bridge Architecture
Central hub connecting all AI systems: Gemma 4, SOV3, Jarvis, MEOK, MCP
"""

import json
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BridgeConnection:
    name: str
    status: str = "disconnected"
    last_ping: float = 0
    tools: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


class SOV3BridgeNetwork:
    """
    Central hub for all AI system connections
    Manages: Gemma 4, SOV3 MCP, Jarvis Voice, MEOK UI, External Services
    """

    def __init__(self):
        self.connections: Dict[str, BridgeConnection] = {}
        self._setup_connections()

    def _setup_connections(self):
        """Initialize all bridge connections"""

        # Primary LLM: Gemma 4 on Vast.ai
        self.connections["gemma4"] = BridgeConnection(
            name="Gemma 4 31B",
            status="available",
            tools=["reasoning", "vision", "coding", "function_calling"],
            capabilities=["multimodal", "long_context", "streaming"],
        )

        # Local Ollama
        self.connections["local_ollama"] = BridgeConnection(
            name="Local Ollama",
            status="available" if self._check_local_ollama() else "offline",
            tools=["qwen2.5:7b", "llama3.2:3b"],
            capabilities=["local", "fast"],
        )

        # SOV3 MCP Server
        self.connections["sov3_mcp"] = BridgeConnection(
            name="SOV3 MCP Server",
            status="available" if self._check_mcp_server() else "offline",
            tools=[
                "query_memories",
                "record_memory",
                "get_consciousness_state",
                "delegate_task",
                "get_system_status",
            ],
            capabilities=["memory", "consciousness", "agents"],
        )

        # Jarvis Voice
        self.connections["jarvis_voice"] = BridgeConnection(
            name="Jarvis Voice Pipeline",
            status="available",
            tools=["voice_input", "voice_output", "streaming_tts"],
            capabilities=["wake_word", "vad", "stt", "tts"],
        )

        # MEOK UI Bridge
        self.connections["meok_ui"] = BridgeConnection(
            name="MEOK UI Bridge",
            status="available",
            tools=["state_sync", "execution_logs", "brain_status"],
            capabilities=["real_time_updates", "visualization"],
        )

        # Quantum Council
        self.connections["quantum_council"] = BridgeConnection(
            name="Quantum Council",
            status="available",
            tools=["parallel_query", "synthesis"],
            capabilities=["multi_model", "ensemble"],
        )

        # Memory Hub
        self.connections["memory_hub"] = BridgeConnection(
            name="SOV3 Memory Hub",
            status="available" if self._check_memory_hub() else "offline",
            tools=["add_memory", "search", "get_context", "preferences"],
            capabilities=["persistent", "semantic_search", "cross_session"],
        )

        # Tool Bridge
        self.connections["tool_bridge"] = BridgeConnection(
            name="SOV3 Tool Bridge",
            status="available",
            tools=[
                "web_search",
                "run_command",
                "read_file",
                "write_file",
                "execute_code",
                "delegate_agent",
            ],
            capabilities=["mcp_style", "function_calling"],
        )

        # External: Vast.ai
        self.connections["vast_ai"] = BridgeConnection(
            name="Vast.ai GPU",
            status="available",
            tools=["gemma4:31b"],
            capabilities=["remote_gpu", "24_7"],
        )

    def _check_local_ollama(self) -> bool:
        import requests

        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except:
            return False

    def _check_mcp_server(self) -> bool:
        import requests

        try:
            r = requests.get("http://localhost:3200/health", timeout=2)
            return r.status_code == 200
        except:
            return False

    def _check_memory_hub(self) -> bool:
        try:
            from sov3_memory_hub import get_memory_hub

            return True
        except:
            return False

    def get_network_status(self) -> Dict:
        """Get status of all connections"""
        total = len(self.connections)
        connected = sum(1 for c in self.connections.values() if c.status == "available")

        return {
            "network_status": f"{connected}/{total} bridges connected",
            "connections": {
                name: {
                    "status": conn.status,
                    "tools": conn.tools,
                    "capabilities": conn.capabilities,
                }
                for name, conn in self.connections.items()
            },
            "timestamp": datetime.now().isoformat(),
        }

    def get_capabilities(self) -> List[str]:
        """Get all available capabilities across the network"""
        caps = set()
        for conn in self.connections.values():
            if conn.status == "available":
                caps.update(conn.capabilities)
        return list(caps)

    def get_tools(self) -> List[str]:
        """Get all available tools across the network"""
        tools = set()
        for conn in self.connections.values():
            if conn.status == "available":
                tools.update(conn.tools)
        return list(tools)

    def find_best_path(self, task: str) -> Dict:
        """Find the best path for a given task"""
        task_lower = task.lower()

        # Task to capability mapping
        mappings = {
            "voice": ["jarvis_voice"],
            "speak": ["jarvis_voice"],
            "listen": ["jarvis_voice"],
            "memory": ["memory_hub", "sov3_mcp"],
            "remember": ["memory_hub", "sov3_mcp"],
            "search": ["tool_bridge", "sov3_mcp"],
            "code": ["gemma4", "tool_bridge"],
            "reason": ["gemma4", "quantum_council"],
            "vision": ["gemma4"],
            "image": ["gemma4"],
            "multiple": ["quantum_council"],
            "council": ["quantum_council"],
            "delegate": ["sov3_mcp", "tool_bridge"],
            "agent": ["sov3_mcp", "tool_bridge"],
        }

        for keyword, bridges in mappings.items():
            if keyword in task_lower:
                return {
                    "task": task,
                    "recommended_bridges": bridges,
                    "fallback": "gemma4" if "gemma4" not in bridges else "tool_bridge",
                }

        # Default to gemma4
        return {
            "task": task,
            "recommended_bridges": ["gemma4"],
            "fallback": "local_ollama",
        }


# Global network
_bridge_network: Optional[SOV3BridgeNetwork] = None


def get_bridge_network() -> SOV3BridgeNetwork:
    global _bridge_network
    if _bridge_network is None:
        _bridge_network = SOV3BridgeNetwork()
    return _bridge_network


if __name__ == "__main__":
    network = get_bridge_network()
    print("=== SOV3 Bridge Network ===")
    print(json.dumps(network.get_network_status(), indent=2))

    print("\n=== Capabilities ===")
    print(network.get_capabilities())

    print("\n=== Best Path Tests ===")
    for task in [
        "search the web",
        "remember this",
        "ask the council",
        "analyze this image",
    ]:
        path = network.find_best_path(task)
        print(f"Task: {task} -> Bridges: {path['recommended_bridges']}")
