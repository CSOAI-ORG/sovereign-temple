"""
MEOKBRIDGE — Universal Compute & Service Connector

One bridge to connect them all:
  • MacBooks, PCs, Raspberry Pis
  • Local GPUs, cloud GPUs, browser GPUs
  • Ollama, llama.cpp, vLLM, MLX
  • OpenAI, Anthropic, DeepSeek, Qwen APIs
  • MCP servers (tools, databases, browsers)
  • A2A agents (peer-to-peer agents)

Usage:
    from meokbridge import MeokBridge, Node, NodeType

    bridge = MeokBridge()
    bridge.add_node(Node(id="m4", name="MacBook M4", node_type=NodeType.OLLAMA, url="http://localhost:11434"))
    result = await bridge.chat("Hello world")
"""

from .core import MeokBridge, Node, NodeType, NodeStatus, NodeCapability, BridgeResult
from .config import BridgeConfig
from .discovery import NodeDiscovery

__all__ = [
    "MeokBridge",
    "Node",
    "NodeType",
    "NodeStatus",
    "NodeCapability",
    "BridgeResult",
    "BridgeConfig",
    "NodeDiscovery",
]

__version__ = "1.0.0"
