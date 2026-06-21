#!/usr/bin/env python3
"""
LETTA MEMORY INTEGRATION (MemGPT successor)
=============================================
Tiered memory for SOV3:
  - Core Memory: Always in context (identity, preferences, current goals)
  - Recall Memory: Searchable conversation history
  - Archival Memory: Long-term knowledge base

Runs via Python 3.11 subprocess to avoid mcp/ module collision.
Letta scores 83.2% on LongMemEval — best in class.
"""

import subprocess
import json
import logging
import os
from typing import Dict, List, Optional, Any

log = logging.getLogger("sovereign.letta")

PYTHON311 = "/opt/homebrew/bin/python3.11"


class LettaMemory:
    """Tiered memory via Letta (MemGPT successor)."""

    def __init__(self):
        self._available = os.path.exists(PYTHON311)
        if self._available:
            try:
                result = subprocess.run(
                    [PYTHON311, "-c", "import letta; print('ok')"],
                    capture_output=True, text=True, timeout=10,
                    cwd="/tmp",
                )
                self._available = result.stdout.strip() == "ok"
            except Exception:
                self._available = False

        if self._available:
            log.info("Letta memory: available (Python 3.11)")
        else:
            log.warning("Letta memory: not available")

    def _run_letta(self, code: str) -> Optional[Dict]:
        """Run Letta code via Python 3.11 subprocess."""
        if not self._available:
            return {"error": "Letta not available"}
        try:
            result = subprocess.run(
                [PYTHON311, "-c", code],
                capture_output=True, text=True, timeout=30,
                cwd="/tmp",
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    return {"raw": result.stdout.strip()[:500]}
            return {"error": result.stderr[:500] or "No output"}
        except subprocess.TimeoutExpired:
            return {"error": "Letta operation timed out"}
        except Exception as e:
            return {"error": str(e)}

    @property
    def available(self) -> bool:
        return self._available

    def add_core(self, fact: str) -> Dict:
        """Add to core memory (always in context)."""
        escaped = fact.replace("'", "\\'").replace('"', '\\"')
        return self._run_letta(f"""
import json
from letta import create_client
client = create_client()
agents = client.list_agents()
if not agents:
    agent = client.create_agent(name="sovereign")
else:
    agent = agents[0]
client.update_agent(agent.id, core_memory_update='{escaped}')
print(json.dumps({{"status": "added", "fact": "{escaped[:80]}"}}))
""")

    def search_recall(self, query: str, limit: int = 5) -> Dict:
        """Search recall memory (conversation history)."""
        escaped = query.replace("'", "\\'").replace('"', '\\"')
        return self._run_letta(f"""
import json
from letta import create_client
client = create_client()
agents = client.list_agents()
if not agents:
    print(json.dumps({{"results": [], "count": 0}}))
else:
    agent = agents[0]
    results = client.get_messages(agent.id, limit={limit})
    out = []
    for m in results:
        out.append({{"role": getattr(m, "role", "?"), "text": str(getattr(m, "text", ""))[:200]}})
    print(json.dumps({{"results": out, "count": len(out)}}))
""")

    def archive(self, content: str, tags: List[str] = None) -> Dict:
        """Add to archival memory (long-term knowledge base)."""
        escaped = content.replace("'", "\\'").replace('"', '\\"')
        return self._run_letta(f"""
import json
from letta import create_client
client = create_client()
agents = client.list_agents()
if not agents:
    agent = client.create_agent(name="sovereign")
else:
    agent = agents[0]
client.insert_archival_memory(agent.id, memory='{escaped[:1000]}')
print(json.dumps({{"status": "archived", "length": {len(content)}}}))
""")

    def search_archival(self, query: str, limit: int = 5) -> Dict:
        """Search archival memory."""
        escaped = query.replace("'", "\\'").replace('"', '\\"')
        return self._run_letta(f"""
import json
from letta import create_client
client = create_client()
agents = client.list_agents()
if not agents:
    print(json.dumps({{"results": [], "count": 0}}))
else:
    agent = agents[0]
    results = client.search_archival_memory(agent.id, query='{escaped}', limit={limit})
    out = []
    for r in results:
        out.append({{"text": str(getattr(r, "text", ""))[:300]}})
    print(json.dumps({{"results": out, "count": len(out)}}))
""")

    def get_status(self) -> Dict:
        """Get Letta memory status."""
        if not self._available:
            return {"available": False}
        return self._run_letta("""
import json
from letta import create_client
client = create_client()
agents = client.list_agents()
print(json.dumps({
    "available": True,
    "agents": len(agents),
    "agent_names": [a.name for a in agents[:5]],
    "version": "0.16.7",
}))
""")


# Singleton
letta_mem = LettaMemory()
