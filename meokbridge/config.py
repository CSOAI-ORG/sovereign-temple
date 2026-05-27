#!/usr/bin/env python3
"""
MEOKBRIDGE Config — YAML-based configuration management
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

from .core import Node, NodeType, NodeCapability


DEFAULT_CONFIG = """# MEOKBRIDGE Configuration
# Add any compute node or API endpoint here.
# Run: meokbridge scan — to auto-discover local nodes

nodes:
  # Your MacBook M4 (local)
  - id: m4-local
    name: MacBook M4
    type: ollama
    url: http://localhost:11434
    priority: 10
    tags: [local, primary]

  # Your MacBook Air M2 (local mesh peer)
  - id: m2-sidekick
    name: MacBook Air M2
    type: ollama
    url: http://m2-air.local:11434
    priority: 5
    tags: [local, mesh, draft]

  # Vast.ai cloud GPU (SSH tunnel)
  - id: vast-cloud
    name: Vast.ai GPU
    type: ollama
    url: http://localhost:11436
    priority: 3
    tags: [cloud, heavy]

  # OpenRouter (API fallback)
  - id: openrouter
    name: OpenRouter
    type: openai_api
    url: https://openrouter.ai/api/v1
    api_key: ${OPENROUTER_API_KEY}
    priority: 1
    tags: [cloud, api, fallback]

  # Example: MCP server
  # - id: postgres-mcp
  #   name: PostgreSQL MCP
  #   type: mcp
  #   transport: stdio
  #   command: npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb
  #   tags: [tool, database]

  # Example: A2A agent
  # - id: research-agent
  #   name: Research Agent
  #   type: a2a
  #   url: http://research-agent.local:8080
  #   tags: [agent, research]

settings:
  health_check_interval: 30
  default_temperature: 0.7
  default_max_tokens: 2048
  prefer_local: true
  council_mode_min_nodes: 3
"""


class BridgeConfig:
    """Load and manage MEOKBRIDGE YAML configuration."""

    CONFIG_PATH = Path.home() / ".meokbridge" / "config.yaml"

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path) if path else self.CONFIG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_default()

    def _write_default(self):
        with open(self.path, "w") as f:
            f.write(DEFAULT_CONFIG)

    def load(self) -> Dict:
        """Load config from YAML."""
        if yaml is None:
            raise ImportError("PyYAML required. Install: pip install pyyaml")
        with open(self.path) as f:
            return yaml.safe_load(f) or {}

    def save(self, config: Dict):
        """Save config to YAML."""
        if yaml is None:
            raise ImportError("PyYAML required. Install: pip install pyyaml")
        with open(self.path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def load_nodes(self) -> List[Node]:
        """Load nodes from config file."""
        config = self.load()
        nodes = []
        for nd in config.get("nodes", []):
            node = self._dict_to_node(nd)
            if node:
                nodes.append(node)
        return nodes

    def _dict_to_node(self, d: Dict) -> Optional[Node]:
        """Convert config dict to Node."""
        try:
            api_key = d.get("api_key", "")
            # Resolve env vars
            if api_key and api_key.startswith("${") and api_key.endswith("}"):
                env_var = api_key[2:-1]
                api_key = os.environ.get(env_var, "")

            caps = d.get("capabilities", {})
            return Node(
                id=d["id"],
                name=d.get("name", d["id"]),
                node_type=NodeType(d["type"]),
                url=d["url"],
                api_key=api_key or None,
                models=d.get("models", []),
                capabilities=NodeCapability(
                    chat=caps.get("chat", True),
                    embed=caps.get("embed", False),
                    vision=caps.get("vision", False),
                    code=caps.get("code", False),
                    reasoning=caps.get("reasoning", False),
                    tool_use=caps.get("tool_use", False),
                    streaming=caps.get("streaming", True),
                    max_tokens=caps.get("max_tokens", 4096),
                    context_window=caps.get("context_window", 32768),
                    languages=caps.get("languages", ["en"]),
                ),
                priority=d.get("priority", 0),
                tags=d.get("tags", []),
                transport=d.get("transport"),
                command=d.get("command"),
            )
        except Exception as e:
            print(f"[MEOKBRIDGE] Failed to parse node config: {e}")
            return None

    def add_node(self, node: Node):
        """Add a node to the config file."""
        config = self.load()
        if "nodes" not in config:
            config["nodes"] = []

        # Remove existing node with same ID
        config["nodes"] = [n for n in config["nodes"] if n.get("id") != node.id]

        node_dict = {
            "id": node.id,
            "name": node.name,
            "type": node.node_type.value,
            "url": node.url,
            "priority": node.priority,
            "tags": node.tags,
        }
        if node.api_key:
            node_dict["api_key"] = node.api_key
        if node.transport:
            node_dict["transport"] = node.transport
        if node.command:
            node_dict["command"] = node.command

        config["nodes"].append(node_dict)
        self.save(config)
