#!/usr/bin/env python3
"""
MEOKBRIDGE Discovery — Auto-find nodes on your network
"""
from __future__ import annotations

import asyncio
import json
import socket
from typing import List, Optional

from .core import Node, NodeType, NodeCapability


class NodeDiscovery:
    """Discovers inference nodes on local network and beyond."""

    # Common Ollama ports
    OLLAMA_PORTS = [11434, 11435, 11436, 8080, 8081]
    # Common llama.cpp / vLLM ports
    LLAMACPP_PORTS = [8080, 8081, 8000, 8001]
    VLLM_PORTS = [8000, 8001]

    def __init__(self, timeout_sec: float = 2.0):
        self.timeout = timeout_sec

    async def discover_lan(self, subnet: Optional[str] = None) -> List[Node]:
        """Scan local network for inference nodes."""
        discovered = []

        # Get local IP subnet
        if not subnet:
            subnet = self._get_local_subnet()

        if not subnet:
            return discovered

        # Scan common ports on local subnet
        base_ip = ".".join(subnet.split(".")[:3])
        tasks = []
        for i in range(1, 255):
            ip = f"{base_ip}.{i}"
            for port in self.OLLAMA_PORTS:
                tasks.append(self._check_ollama(ip, port))
            for port in self.LLAMACPP_PORTS:
                tasks.append(self._check_llamacpp(ip, port))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Node):
                discovered.append(result)

        return discovered

    async def discover_mdns(self) -> List[Node]:
        """Discover via mDNS/Bonjour (macOS-friendly)."""
        discovered = []
        # Common mDNS hostnames
        hosts = [
            "m2-air.local",
            "m2-macbook.local",
            "m4-macbook.local",
            "m4-pro.local",
            "m4-max.local",
            "macbook-air.local",
            "macbook-pro.local",
            "ollama.local",
            "meokclaw.local",
        ]

        for host in hosts:
            try:
                ip = socket.gethostbyname(host)
                node = await self._check_ollama(ip, 11434)
                if node:
                    node.name = host.replace(".local", "")
                    discovered.append(node)
            except socket.gaierror:
                pass

        return discovered

    async def discover_vast_tunnel(self, local_ports: List[int] = None) -> List[Node]:
        """Check for existing Vast.ai SSH tunnels."""
        ports = local_ports or [11436, 11437, 11438]
        discovered = []
        for port in ports:
            node = await self._check_ollama("localhost", port)
            if node:
                node.name = f"vast-gpu-{port}"
                node.tags.append("cloud")
                discovered.append(node)
        return discovered

    async def _check_ollama(self, host: str, port: int) -> Optional[Node]:
        try:
            import httpx
            url = f"http://{host}:{port}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return Node(
                        id=f"ollama-{host.replace('.', '-')}-{port}",
                        name=f"Ollama @ {host}:{port}",
                        node_type=NodeType.OLLAMA,
                        url=url,
                        models=models,
                        capabilities=NodeCapability(
                            chat=True, embed=True, vision="vision" in str(models).lower(),
                            streaming=True
                        ),
                        tags=["auto-discovered"],
                    )
        except Exception:
            pass
        return None

    async def _check_llamacpp(self, host: str, port: int) -> Optional[Node]:
        try:
            import httpx
            url = f"http://{host}:{port}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{url}/health")
                if resp.status_code == 200:
                    return Node(
                        id=f"llamacpp-{host.replace('.', '-')}-{port}",
                        name=f"llama.cpp @ {host}:{port}",
                        node_type=NodeType.LLAMACPP,
                        url=url,
                        capabilities=NodeCapability(chat=True, streaming=True),
                        tags=["auto-discovered"],
                    )
        except Exception:
            pass
        return None

    def _get_local_subnet(self) -> Optional[str]:
        """Get local IP subnet."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
