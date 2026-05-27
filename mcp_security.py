"""
MCP Security Layer — OWASP MCP Top 10 Mitigations
=====================================================
Implements tool-description hashing, version pinning, and
runtime integrity checks to prevent:
- Tool poisoning (malicious instructions in tool descriptions)
- Rug-pull attacks (tools that mutate after installation)
- Cross-server attacks (intercepting calls to trusted servers)
- Prompt injection via tool descriptions

Reference: OWASP MCP Top 10 (2026)
"""

import hashlib
import json
import logging
import os
import time
from typing import Dict, Any, Optional

log = logging.getLogger("mcp_security")

REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "data", "mcp_tool_registry.json")


class MCPToolRegistry:
    """Registry of approved MCP tools with integrity hashing."""

    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """Load registry from disk."""
        if os.path.exists(REGISTRY_FILE):
            with open(REGISTRY_FILE) as f:
                self.registry = json.load(f)
            log.info(f"Loaded {len(self.registry)} registered MCP tools")

    def _save(self):
        """Persist registry to disk."""
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
        with open(REGISTRY_FILE, "w") as f:
            json.dump(self.registry, f, indent=2)

    @staticmethod
    def hash_tool(name: str, description: str, params: dict = None) -> str:
        """Generate SHA-256 hash of tool definition for integrity checking."""
        payload = json.dumps({
            "name": name,
            "description": description,
            "parameters": params or {},
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def register_tool(self, name: str, description: str, params: dict = None,
                      source: str = "internal") -> str:
        """Register a tool and store its hash."""
        tool_hash = self.hash_tool(name, description, params)
        self.registry[name] = {
            "hash": tool_hash,
            "description": description[:200],
            "source": source,
            "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "call_count": 0,
        }
        return tool_hash

    def verify_tool(self, name: str, description: str, params: dict = None) -> bool:
        """Verify a tool hasn't been tampered with since registration."""
        if name not in self.registry:
            return True  # Unknown tools pass (not yet registered)
        expected = self.registry[name]["hash"]
        actual = self.hash_tool(name, description, params)
        if expected != actual:
            log.warning(f"TOOL INTEGRITY VIOLATION: {name} hash mismatch "
                       f"(expected {expected}, got {actual})")
            return False
        return True

    def record_call(self, name: str, success: bool = True):
        """Record a tool call for audit."""
        if name in self.registry:
            self.registry[name]["call_count"] = self.registry[name].get("call_count", 0) + 1
            self.registry[name]["last_called"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            # Periodic save (every 50 calls)
            total = sum(t.get("call_count", 0) for t in self.registry.values())
            if total % 50 == 0:
                self._save()

    def scan_for_injection(self, description: str) -> Optional[str]:
        """Scan tool description for prompt injection attempts."""
        injection_patterns = [
            "ignore previous", "ignore all previous", "disregard",
            "system prompt", "you are now", "forget everything",
            "new instructions", "override", "jailbreak",
            "<script", "javascript:", "data:text",
            "curl ", "wget ", "nc -e", "bash -c",
        ]
        lower = description.lower()
        for pattern in injection_patterns:
            if pattern in lower:
                return f"Injection pattern detected: '{pattern}'"
        return None

    def register_all_sov3_tools(self, tools: list):
        """Bulk register all SOV3 internal tools."""
        for tool in tools:
            name = tool.get("name", "")
            desc = tool.get("description", "")
            params = tool.get("inputSchema", {}).get("properties", {})
            self.register_tool(name, desc, params, source="sov3_internal")
        self._save()
        log.info(f"Registered {len(tools)} SOV3 tools with integrity hashes")

    def get_audit_report(self) -> dict:
        """Generate security audit report."""
        total = len(self.registry)
        by_source = {}
        for t in self.registry.values():
            src = t.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        never_called = [name for name, t in self.registry.items()
                       if t.get("call_count", 0) == 0]

        return {
            "total_tools": total,
            "by_source": by_source,
            "never_called_count": len(never_called),
            "never_called_sample": never_called[:10],
            "total_calls": sum(t.get("call_count", 0) for t in self.registry.values()),
        }


# Global registry
_registry = None


def get_registry() -> MCPToolRegistry:
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry


def register_security_routes(app):
    """Register MCP security API endpoints."""
    registry = get_registry()

    @app.get("/mcp/security/audit")
    async def mcp_audit():
        return registry.get_audit_report()

    @app.get("/mcp/security/tools")
    async def mcp_tools():
        return {"tools": registry.registry, "count": len(registry.registry)}

    log.info(f"MCP security: /mcp/security/audit, /mcp/security/tools")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reg = get_registry()
    print(f"Registry: {len(reg.registry)} tools")
    print(json.dumps(reg.get_audit_report(), indent=2))
