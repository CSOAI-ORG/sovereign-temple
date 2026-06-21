#!/usr/bin/env python3
"""
SOV3 Universal MCP Bridge
==========================
Discovers and calls any of the 207 MCP marketplace servers,
logs every call for neural net training, and tracks success/failure rates.

Usage:
    from mcp_bridge import MCPBridge, NeuralFeedback

    bridge = MCPBridge()
    result = bridge.call("eu-ai-act-compliance-mcp", "classify_ai_risk", {...})
    stats = bridge.get_stats()

    feedback = NeuralFeedback()
    feedback.learn_from_recent(limit=50)
    insights = feedback.get_insights()
"""

import ast
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sqlite3
import sys
import time
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("mcp_bridge")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MARKETPLACE_DIR = os.path.expanduser("~/clawd/mcp-marketplace")
BRIDGE_DB_PATH = os.path.expanduser("~/.meok/data/bridge_calls.db")
NEURAL_DB_PATH = os.path.expanduser("~/.meok/data/bridge_neural.db")

# Compliance neural import
_NEURAL_PATH = os.path.expanduser("~/clawd/meok-labs-engine/shared")


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Server discovery helpers
# ---------------------------------------------------------------------------

def _extract_tools_from_source(server_path: str) -> List[Dict[str, str]]:
    """
    Parse a server.py to extract @mcp.tool() decorated function names
    and their docstrings without importing the module.
    Uses AST so we never execute untrusted code at discovery time.
    """
    tools = []  # type: List[Dict[str, str]]
    try:
        with open(server_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=server_path)
    except Exception:
        return tools

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        # Check for @mcp.tool() decorator
        for dec in node.decorator_list:
            is_mcp_tool = False
            # @mcp.tool()
            if isinstance(dec, ast.Call):
                func = dec.func if hasattr(dec, "func") else None
                if isinstance(func, ast.Attribute) and func.attr == "tool":
                    is_mcp_tool = True
            # @mcp.tool  (no parens)
            elif isinstance(dec, ast.Attribute) and dec.attr == "tool":
                is_mcp_tool = True
            if is_mcp_tool:
                docstring = ast.get_docstring(node) or ""
                # Get parameter names (skip 'self')
                params = []  # type: List[str]
                for arg in node.args.args:
                    name = arg.arg
                    if name != "self":
                        params.append(name)
                tools.append({
                    "name": node.name,
                    "description": docstring.split("\n")[0] if docstring else "",
                    "parameters": params,
                })
                break
    return tools


# ---------------------------------------------------------------------------
# MCPBridge
# ---------------------------------------------------------------------------

class MCPBridge:
    """
    Discovers all MCP marketplace servers and provides a unified call interface.
    Every call is logged to SQLite for neural net training.
    """

    def __init__(self, marketplace_dir: str = MARKETPLACE_DIR,
                 db_path: str = BRIDGE_DB_PATH):
        self.marketplace_dir = marketplace_dir
        self.db_path = db_path
        _ensure_dir(self.db_path)
        self._init_db()

        # Cache: server_name -> {"path": str, "tools": [...], "module": module|None}
        self._servers = {}  # type: Dict[str, Dict[str, Any]]
        self._loaded_modules = {}  # type: Dict[str, Any]
        self._discover_servers()

    # ---- DB setup ----

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS call_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT,
                result TEXT,
                success INTEGER NOT NULL DEFAULT 1,
                error_msg TEXT,
                duration_ms REAL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_call_server ON call_log(server_name);
            CREATE INDEX IF NOT EXISTS idx_call_timestamp ON call_log(timestamp);

            CREATE TABLE IF NOT EXISTS server_stats (
                server_name TEXT PRIMARY KEY,
                total_calls INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0,
                failures INTEGER DEFAULT 0,
                avg_duration_ms REAL DEFAULT 0,
                last_called REAL,
                last_error TEXT
            );
        """)
        conn.commit()
        conn.close()

    # ---- Discovery ----

    def _discover_servers(self) -> None:
        """Scan marketplace directory for all servers with server.py."""
        if not os.path.isdir(self.marketplace_dir):
            logger.warning("Marketplace dir not found: %s", self.marketplace_dir)
            return

        for entry in sorted(os.listdir(self.marketplace_dir)):
            server_dir = os.path.join(self.marketplace_dir, entry)
            server_py = os.path.join(server_dir, "server.py")
            if os.path.isdir(server_dir) and os.path.isfile(server_py):
                tools = _extract_tools_from_source(server_py)
                self._servers[entry] = {
                    "path": server_py,
                    "tools": tools,
                    "tool_names": [t["name"] for t in tools],
                }

        logger.info("Discovered %d MCP servers with %d total tools",
                     len(self._servers),
                     sum(len(s["tools"]) for s in self._servers.values()))

    def discover(self) -> List[Dict[str, Any]]:
        """Return list of all discovered servers and their tools."""
        result = []  # type: List[Dict[str, Any]]
        for name, info in sorted(self._servers.items()):
            result.append({
                "server": name,
                "tools": info["tools"],
                "tool_count": len(info["tools"]),
                "path": info["path"],
            })
        return result

    def list_servers(self) -> List[str]:
        """Return sorted list of server names."""
        return sorted(self._servers.keys())

    def get_server_tools(self, server_name: str) -> List[Dict[str, str]]:
        """Return tools for a specific server."""
        info = self._servers.get(server_name)
        if not info:
            return []
        return info["tools"]

    # ---- Dynamic import ----

    def _load_server_module(self, server_name: str) -> Any:
        """Dynamically import a server.py module. Returns the module or None."""
        if server_name in self._loaded_modules:
            return self._loaded_modules[server_name]

        info = self._servers.get(server_name)
        if not info:
            return None

        server_path = info["path"]
        server_dir = os.path.dirname(server_path)
        module_name = "mcp_server_{}".format(server_name.replace("-", "_"))

        # Add server dir to path so its local imports resolve
        if server_dir not in sys.path:
            sys.path.insert(0, server_dir)
        # Also add shared auth path
        shared_path = os.path.expanduser("~/clawd/meok-labs-engine/shared")
        if shared_path not in sys.path:
            sys.path.insert(0, shared_path)

        try:
            spec = importlib.util.spec_from_file_location(module_name, server_path)
            if spec is None or spec.loader is None:
                logger.error("Cannot create spec for %s", server_path)
                self._loaded_modules[server_name] = None
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            self._loaded_modules[server_name] = mod
            return mod
        except Exception as e:
            logger.warning("Failed to import %s: %s", server_name, e)
            self._loaded_modules[server_name] = None
            return None

    def _find_tool_function(self, module: Any, tool_name: str) -> Optional[Any]:
        """Find a callable function in a loaded module by name."""
        fn = getattr(module, tool_name, None)
        if fn is not None and callable(fn):
            return fn
        # Some servers nest tools — search through all callables
        for attr_name in dir(module):
            if attr_name == tool_name:
                obj = getattr(module, attr_name, None)
                if callable(obj):
                    return obj
        return None

    # ---- Call ----

    def call(self, server_name: str, tool_name: str,
             arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call a tool on any MCP server by name.

        Args:
            server_name: e.g. "eu-ai-act-compliance-mcp"
            tool_name: e.g. "classify_ai_risk"
            arguments: dict of keyword arguments to pass to the tool

        Returns:
            dict with "result" on success or "error" on failure
        """
        if arguments is None:
            arguments = {}

        start_time = time.time()
        success = True
        error_msg = None  # type: Optional[str]
        result = {}  # type: Dict[str, Any]

        try:
            # Validate server exists
            if server_name not in self._servers:
                raise ValueError(
                    "Unknown server '{}'. Use discover() to see available servers.".format(server_name)
                )

            # Validate tool exists (based on AST discovery)
            info = self._servers[server_name]
            if tool_name not in info["tool_names"]:
                raise ValueError(
                    "Tool '{}' not found in server '{}'. Available: {}".format(
                        tool_name, server_name, ", ".join(info["tool_names"])
                    )
                )

            # Load the module
            module = self._load_server_module(server_name)
            if module is None:
                raise RuntimeError(
                    "Failed to import server '{}'. Check logs for details.".format(server_name)
                )

            # Find the function
            fn = self._find_tool_function(module, tool_name)
            if fn is None:
                raise RuntimeError(
                    "Tool function '{}' not found in loaded module '{}'".format(
                        tool_name, server_name
                    )
                )

            # Call the function with provided arguments
            call_result = fn(**arguments)
            if isinstance(call_result, dict):
                result = call_result
            else:
                result = {"value": call_result}

        except Exception as e:
            success = False
            error_msg = str(e)
            result = {
                "error": error_msg,
                "traceback": traceback.format_exc(),
            }

        duration_ms = (time.time() - start_time) * 1000.0

        # Log to SQLite
        self._log_call(server_name, tool_name, arguments, result,
                       success, error_msg, duration_ms)

        return result

    # ---- Logging ----

    def _log_call(self, server_name: str, tool_name: str,
                  arguments: Dict[str, Any], result: Dict[str, Any],
                  success: bool, error_msg: Optional[str],
                  duration_ms: float) -> None:
        """Log a call to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO call_log
                   (server_name, tool_name, arguments, result, success,
                    error_msg, duration_ms, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    server_name, tool_name,
                    json.dumps(arguments, default=str),
                    json.dumps(result, default=str)[:10000],  # cap result size
                    1 if success else 0,
                    error_msg,
                    duration_ms,
                    time.time(),
                )
            )

            # Update server stats
            conn.execute("""
                INSERT INTO server_stats (server_name, total_calls, successes, failures,
                                          avg_duration_ms, last_called, last_error)
                VALUES (?, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(server_name) DO UPDATE SET
                    total_calls = total_calls + 1,
                    successes = successes + ?,
                    failures = failures + ?,
                    avg_duration_ms = (avg_duration_ms * total_calls + ?) / (total_calls + 1),
                    last_called = ?,
                    last_error = CASE WHEN ? IS NOT NULL THEN ? ELSE last_error END
            """, (
                server_name,
                1 if success else 0, 0 if success else 1,
                duration_ms, time.time(), error_msg,
                1 if success else 0, 0 if success else 1,
                duration_ms, time.time(),
                error_msg, error_msg,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to log call: %s", e)

    # ---- Stats ----

    def get_stats(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get call statistics, optionally filtered by server.

        Returns:
            dict with overall stats and per-server breakdown
        """
        conn = sqlite3.connect(self.db_path)

        # Overall stats
        row = conn.execute(
            "SELECT COUNT(*), SUM(success), SUM(CASE WHEN success=0 THEN 1 ELSE 0 END), "
            "AVG(duration_ms) FROM call_log"
        ).fetchone()
        overall = {
            "total_calls": row[0] or 0,
            "successes": row[1] or 0,
            "failures": row[2] or 0,
            "avg_duration_ms": round(row[3] or 0, 2),
            "success_rate": round((row[1] or 0) / max(row[0] or 1, 1) * 100, 1),
        }

        # Per-server stats
        if server_name:
            rows = conn.execute(
                "SELECT * FROM server_stats WHERE server_name = ?",
                (server_name,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM server_stats ORDER BY total_calls DESC LIMIT 50"
            ).fetchall()

        servers = []  # type: List[Dict[str, Any]]
        for r in rows:
            servers.append({
                "server": r[0],
                "total_calls": r[1],
                "successes": r[2],
                "failures": r[3],
                "avg_duration_ms": round(r[4] or 0, 2),
                "last_called": r[5],
                "last_error": r[6],
                "success_rate": round(r[2] / max(r[1], 1) * 100, 1),
            })

        # Top tools
        tool_rows = conn.execute(
            "SELECT server_name, tool_name, COUNT(*), SUM(success) "
            "FROM call_log GROUP BY server_name, tool_name "
            "ORDER BY COUNT(*) DESC LIMIT 20"
        ).fetchall()
        top_tools = []  # type: List[Dict[str, Any]]
        for tr in tool_rows:
            top_tools.append({
                "server": tr[0],
                "tool": tr[1],
                "calls": tr[2],
                "successes": tr[3],
            })

        conn.close()

        return {
            "overall": overall,
            "servers": servers,
            "top_tools": top_tools,
            "total_servers_discovered": len(self._servers),
            "total_tools_discovered": sum(
                len(s["tools"]) for s in self._servers.values()
            ),
        }

    def get_recent_calls(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent call log entries for neural feedback."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT server_name, tool_name, arguments, result, success, "
            "error_msg, duration_ms, timestamp "
            "FROM call_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()

        calls = []  # type: List[Dict[str, Any]]
        for r in rows:
            calls.append({
                "server_name": r[0],
                "tool_name": r[1],
                "arguments": r[2],
                "result": r[3],
                "success": bool(r[4]),
                "error_msg": r[5],
                "duration_ms": r[6],
                "timestamp": r[7],
            })
        return calls


# ---------------------------------------------------------------------------
# NeuralFeedback
# ---------------------------------------------------------------------------

class NeuralFeedback:
    """
    Takes MCP bridge call data and feeds it to the compliance neural net
    for pattern learning. Tracks which servers are used most, failure
    patterns, and generates feature vectors for the neural network.
    """

    def __init__(self, bridge: Optional[MCPBridge] = None,
                 db_path: str = NEURAL_DB_PATH):
        self.bridge = bridge
        self.db_path = db_path
        _ensure_dir(self.db_path)
        self._init_db()
        self._neural_net = None  # type: Optional[Any]
        self._load_neural()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_size INTEGER,
                avg_loss REAL,
                patterns_found INTEGER,
                timestamp REAL
            );
            CREATE TABLE IF NOT EXISTS server_patterns (
                server_name TEXT PRIMARY KEY,
                call_frequency REAL DEFAULT 0,
                failure_rate REAL DEFAULT 0,
                avg_latency REAL DEFAULT 0,
                feature_vector TEXT,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS aggregated_insights (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL
            );
        """)
        conn.commit()
        conn.close()

    def _load_neural(self) -> None:
        """Load the compliance neural net module."""
        try:
            if _NEURAL_PATH not in sys.path:
                sys.path.insert(0, _NEURAL_PATH)
            from compliance_neural import ComplianceNeuralNet
            self._neural_net = ComplianceNeuralNet("mcp_bridge")
        except Exception as e:
            logger.warning("Could not load ComplianceNeuralNet: %s", e)
            self._neural_net = None

    def _call_to_features(self, call_data: Dict[str, Any]) -> List[float]:
        """
        Convert a call log entry into a 12-dimensional feature vector
        compatible with ComplianceNeuralNet.

        Mapping:
            0: system_complexity     — based on argument count
            1: data_sensitivity      — heuristic from tool name
            2: autonomy_level        — 0.5 default (bridge-mediated)
            3: affected_population   — 0.3 default
            4: sector_risk           — from server name heuristic
            5: existing_controls     — 0.7 (bridge provides control layer)
            6: documentation_quality — based on tool description availability
            7: prior_violations      — from failure rate
            8: cross_border          — from server name heuristic
            9: model_transparency    — 0.6 (tools are inspectable)
            10: update_frequency     — from call frequency
            11: vulnerability_exposure — from error rate
        """
        server = call_data.get("server_name", "")
        tool = call_data.get("tool_name", "")
        success = call_data.get("success", True)
        duration = call_data.get("duration_ms", 0) or 0
        args_str = call_data.get("arguments", "{}")

        # Parse argument complexity
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
            arg_count = len(args) if isinstance(args, dict) else 0
        except Exception:
            arg_count = 0

        # Sector risk heuristic based on server name keywords
        high_risk_keywords = ["compliance", "security", "audit", "healthcare", "finance",
                              "identity", "trust", "governance", "law"]
        medium_risk_keywords = ["ai", "data", "analytics", "monitor", "blockchain"]
        sector_risk = 0.3
        for kw in high_risk_keywords:
            if kw in server.lower():
                sector_risk = 0.8
                break
        else:
            for kw in medium_risk_keywords:
                if kw in server.lower():
                    sector_risk = 0.6
                    break

        # Data sensitivity heuristic
        sensitive_keywords = ["pii", "biometric", "health", "financial", "identity",
                              "credential", "auth", "personal"]
        data_sensitivity = 0.3
        for kw in sensitive_keywords:
            if kw in server.lower() or kw in tool.lower():
                data_sensitivity = 0.8
                break

        # Cross-border heuristic
        cross_border = 0.7 if any(kw in server.lower()
                                  for kw in ["eu", "gdpr", "jurisdiction", "cross", "multi"]) else 0.3

        features = [
            min(1.0, arg_count / 10.0),           # 0: system_complexity
            data_sensitivity,                       # 1: data_sensitivity
            0.5,                                    # 2: autonomy_level
            0.3,                                    # 3: affected_population
            sector_risk,                            # 4: sector_risk
            0.7,                                    # 5: existing_controls
            0.6,                                    # 6: documentation_quality
            0.0 if success else 0.5,               # 7: prior_violations
            cross_border,                           # 8: cross_border
            0.6,                                    # 9: model_transparency
            min(1.0, duration / 5000.0),           # 10: update_frequency (latency proxy)
            0.0 if success else 0.7,               # 11: vulnerability_exposure
        ]
        return features

    def _call_to_outcome(self, call_data: Dict[str, Any]) -> List[float]:
        """
        Convert a call result into a 4-dimensional outcome vector.

        Output mapping:
            0: overall_risk_score     — from success + duration
            1: violation_probability  — from failure
            2: remediation_urgency    — from error severity
            3: audit_priority         — from sector risk
        """
        success = call_data.get("success", True)
        duration = call_data.get("duration_ms", 0) or 0
        server = call_data.get("server_name", "")

        risk = 0.2 if success else 0.8
        violation = 0.1 if success else 0.9
        urgency = 0.1 if success else 0.7
        # Higher audit priority for compliance/security servers
        audit = 0.3
        for kw in ["compliance", "audit", "security", "governance"]:
            if kw in server.lower():
                audit = 0.7
                break

        # Slow calls increase risk slightly
        if duration > 3000:
            risk = min(1.0, risk + 0.2)

        return [risk, violation, urgency, audit]

    def learn_from_recent(self, limit: int = 50) -> Dict[str, Any]:
        """
        Fetch recent bridge calls and train the neural net on them.

        Returns:
            dict with learning results and pattern summary
        """
        if self.bridge is None:
            return {"error": "No MCPBridge instance connected"}

        calls = self.bridge.get_recent_calls(limit=limit)
        if not calls:
            return {"message": "No recent calls to learn from", "learned": 0}

        results = []  # type: List[Dict[str, Any]]
        total_loss = 0.0
        patterns = defaultdict(int)  # type: Dict[str, int]

        for call in calls:
            features = self._call_to_features(call)
            outcome = self._call_to_outcome(call)

            # Feed to neural net if available
            if self._neural_net is not None:
                try:
                    learn_result = self._neural_net.learn_from_check(features, outcome)
                    total_loss += learn_result.get("loss", 0)
                    results.append(learn_result)
                except Exception as e:
                    logger.warning("Neural learning failed: %s", e)

            # Track patterns
            server = call.get("server_name", "unknown")
            patterns[server] += 1

            # Update server patterns in DB
            self._update_server_pattern(call)

        avg_loss = total_loss / max(len(results), 1)

        # Log learning session
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO learning_log (batch_size, avg_loss, patterns_found, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (len(calls), avg_loss, len(patterns), time.time())
        )
        conn.commit()
        conn.close()

        # Update aggregated insights
        self._update_aggregated_insights(calls, patterns)

        return {
            "learned_from": len(calls),
            "neural_updates": len(results),
            "avg_loss": round(avg_loss, 6),
            "patterns_found": len(patterns),
            "top_servers": sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10],
            "neural_available": self._neural_net is not None,
        }

    def _update_server_pattern(self, call: Dict[str, Any]) -> None:
        """Update per-server pattern data."""
        server = call.get("server_name", "")
        features = self._call_to_features(call)
        success = call.get("success", True)
        duration = call.get("duration_ms", 0) or 0

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO server_patterns
                    (server_name, call_frequency, failure_rate, avg_latency,
                     feature_vector, updated_at)
                VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(server_name) DO UPDATE SET
                    call_frequency = call_frequency + 1,
                    failure_rate = (failure_rate * call_frequency + ?) / (call_frequency + 1),
                    avg_latency = (avg_latency * call_frequency + ?) / (call_frequency + 1),
                    feature_vector = ?,
                    updated_at = ?
            """, (
                server,
                0.0 if success else 1.0,
                duration,
                json.dumps(features),
                time.time(),
                0.0 if success else 1.0,
                duration,
                json.dumps(features),
                time.time(),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to update server pattern: %s", e)

    def _update_aggregated_insights(self, calls: List[Dict[str, Any]],
                                     patterns: Dict[str, int]) -> None:
        """Compute and persist aggregate insights."""
        total = len(calls)
        successes = sum(1 for c in calls if c.get("success", True))
        failures = total - successes
        avg_duration = sum(c.get("duration_ms", 0) or 0 for c in calls) / max(total, 1)

        # Server diversity — how many unique servers used
        unique_servers = len(patterns)

        # Tool diversity
        unique_tools = len(set(
            "{}:{}".format(c.get("server_name", ""), c.get("tool_name", ""))
            for c in calls
        ))

        insights = {
            "total_calls_analyzed": total,
            "success_rate": round(successes / max(total, 1) * 100, 1),
            "failure_rate": round(failures / max(total, 1) * 100, 1),
            "avg_duration_ms": round(avg_duration, 2),
            "server_diversity": unique_servers,
            "tool_diversity": unique_tools,
            "top_servers": sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10],
            "neural_model_status": "active" if self._neural_net is not None else "unavailable",
            "analyzed_at": time.time(),
        }

        # Get neural insights if available
        if self._neural_net is not None:
            try:
                neural_insights = self._neural_net.get_insights()
                insights["neural_insights"] = neural_insights
            except Exception:
                pass

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR REPLACE INTO aggregated_insights (key, value, updated_at) "
                "VALUES ('latest', ?, ?)",
                (json.dumps(insights, default=str), time.time())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to update aggregated insights: %s", e)

    def get_insights(self) -> Dict[str, Any]:
        """Get the latest aggregated insights."""
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT value FROM aggregated_insights WHERE key='latest'"
            ).fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception:
            pass

        return {
            "message": "No insights yet. Run learn_from_recent() first.",
            "neural_available": self._neural_net is not None,
        }

    def get_server_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get per-server pattern data."""
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT server_name, call_frequency, failure_rate, avg_latency, "
                "feature_vector, updated_at "
                "FROM server_patterns ORDER BY call_frequency DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()

            result = []  # type: List[Dict[str, Any]]
            for r in rows:
                result.append({
                    "server": r[0],
                    "call_frequency": r[1],
                    "failure_rate": round(r[2], 3),
                    "avg_latency_ms": round(r[3], 2),
                    "feature_vector": json.loads(r[4]) if r[4] else [],
                    "updated_at": r[5],
                })
            return result
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Singleton instances (lazy)
# ---------------------------------------------------------------------------
_bridge_instance = None  # type: Optional[MCPBridge]
_feedback_instance = None  # type: Optional[NeuralFeedback]


def get_bridge() -> MCPBridge:
    """Get or create the singleton MCPBridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MCPBridge()
    return _bridge_instance


def get_feedback() -> NeuralFeedback:
    """Get or create the singleton NeuralFeedback instance."""
    global _feedback_instance
    if _feedback_instance is None:
        _feedback_instance = NeuralFeedback(bridge=get_bridge())
    return _feedback_instance


# ---------------------------------------------------------------------------
# SOV3 MCP Tool handlers
# ---------------------------------------------------------------------------

def handle_mcp_bridge_call(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for the mcp_bridge_call tool."""
    server_name = arguments.get("server_name", "")
    tool_name = arguments.get("tool_name", "")
    tool_arguments = arguments.get("arguments", {})

    if not server_name or not tool_name:
        return {"error": "Both server_name and tool_name are required"}

    if isinstance(tool_arguments, str):
        try:
            tool_arguments = json.loads(tool_arguments)
        except Exception:
            return {"error": "arguments must be a valid JSON object"}

    bridge = get_bridge()
    return bridge.call(server_name, tool_name, tool_arguments)


def handle_mcp_bridge_discover(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for the mcp_bridge_discover tool."""
    bridge = get_bridge()
    server_filter = arguments.get("filter", "")
    servers = bridge.discover()

    if server_filter:
        servers = [s for s in servers
                   if server_filter.lower() in s["server"].lower()
                   or any(server_filter.lower() in t.get("name", "").lower()
                          for t in s["tools"])]

    return {
        "total_servers": len(bridge.list_servers()),
        "filtered": len(servers),
        "servers": servers,
    }


def handle_mcp_bridge_stats(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for the mcp_bridge_stats tool."""
    bridge = get_bridge()
    server_name = arguments.get("server_name")
    stats = bridge.get_stats(server_name=server_name)

    # Add neural insights
    feedback = get_feedback()
    stats["neural_insights"] = feedback.get_insights()
    stats["server_patterns"] = feedback.get_server_patterns(limit=10)

    return stats


def handle_mcp_bridge_learn(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for the mcp_bridge_learn tool."""
    limit = arguments.get("limit", 50)
    if not isinstance(limit, int) or limit < 1:
        limit = 50

    feedback = get_feedback()
    return feedback.learn_from_recent(limit=limit)


# ---------------------------------------------------------------------------
# Tool definitions for SOV3 MCP registration
# ---------------------------------------------------------------------------

BRIDGE_TOOL_DEFINITIONS = [
    {
        "name": "mcp_bridge_call",
        "description": "Call any MCP marketplace server tool through the universal bridge. "
                       "Supports 207+ servers with auto-discovery, auth routing, and neural logging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "MCP server name (e.g. 'eu-ai-act-compliance-mcp')"
                },
                "tool_name": {
                    "type": "string",
                    "description": "Tool function name on that server (e.g. 'classify_ai_risk')"
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the tool function",
                    "default": {}
                },
            },
            "required": ["server_name", "tool_name"],
        },
    },
    {
        "name": "mcp_bridge_discover",
        "description": "Discover all available MCP marketplace servers and their tools. "
                       "Returns server names, tool lists, and parameter info for 207+ servers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional filter to search servers/tools by keyword",
                    "default": ""
                },
            },
        },
    },
    {
        "name": "mcp_bridge_stats",
        "description": "Get call statistics and neural insights from the MCP bridge. "
                       "Shows success rates, top tools, latency, and learned patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "Optional: filter stats to a specific server",
                },
            },
        },
    },
    {
        "name": "mcp_bridge_learn",
        "description": "Trigger neural net learning from recent MCP bridge calls. "
                       "Feeds call patterns to the compliance neural network for risk prediction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent calls to learn from (default 50)",
                    "default": 50
                },
            },
        },
    },
]


if __name__ == "__main__":
    # Quick self-test
    bridge = MCPBridge()
    servers = bridge.list_servers()
    print("Discovered {} MCP servers".format(len(servers)))
    for s in servers[:5]:
        tools = bridge.get_server_tools(s)
        print("  {} — {} tools".format(s, len(tools)))
        for t in tools[:3]:
            print("    - {}".format(t["name"]))
    print("\nBridge ready.")
