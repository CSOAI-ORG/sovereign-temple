"""
tool_ops.py — make SOV3 operate its 110 MCP tools better. Stdlib-only, additive.

Two universal improvements, both wired at the natural chokepoints:

  1. validate_and_repair(tool, args, schema)
     Schema-validate + auto-coerce/default tool-call arguments BEFORE execution.
     The #1 failure mode for a local LLM (Gemma via Ollama) operating tools is malformed
     args — a string "5" where an int is wanted, a missing default, a CSV where a list is
     wanted. This coerces them to the declared JSON-Schema type and fills defaults, so the
     call succeeds instead of crashing the handler. Wired at the tools/call chokepoint.

  2. keyword_rank(query, tools, top_k)
     A fast token-overlap tool ranker used as the ToolDispatcher FALLBACK when the
     sentence-transformers embedder isn't available — otherwise the dispatcher returns ALL
     tools (token bloat + worse selection). Keeps the "send 5-10 relevant tools" behaviour
     even with no embeddings installed.

Self-test: `python3 tool_ops.py`
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

_TOKEN = re.compile(r"[a-z0-9]+")


def _coerce(value: Any, typ: Optional[str]) -> Any:
    """Best-effort coerce a value to a JSON-Schema type. Returns the original on failure
    (never raises) — repair must not break a call that was already fine."""
    if typ is None or value is None:
        return value
    try:
        if typ == "integer":
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return value
            return int(float(str(value).strip()))
        if typ == "number":
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return value
            return float(str(value).strip())
        if typ == "boolean":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("true", "1", "yes", "y", "on")
        if typ == "array":
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                s = value.strip()
                if s.startswith("["):
                    try:
                        return json.loads(s)
                    except Exception:
                        pass
                return [x.strip() for x in s.split(",") if x.strip()]
            return [value]
        if typ == "object":
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value
        if typ == "string":
            return value if isinstance(value, str) else str(value)
    except Exception:
        return value
    return value


def validate_and_repair(tool_name: str, args: dict, schema: Optional[dict]) -> tuple:
    """Validate + repair tool-call args against an MCP inputSchema.
    Returns (repaired_args, report). report = {coerced, defaulted, missing_required, unknown}.
    Non-destructive: coerces known fields to their declared type and fills defaults; never
    drops args (unknowns are reported, not removed)."""
    args = dict(args or {})
    props = (schema or {}).get("properties", {}) or {}
    required = (schema or {}).get("required", []) or []
    coerced, defaulted, missing, unknown = [], [], [], []

    for k, spec in props.items():
        typ = spec.get("type") if isinstance(spec, dict) else None
        if k in args:
            new = _coerce(args[k], typ)
            if new != args[k]:
                args[k] = new
                coerced.append(k)
        elif isinstance(spec, dict) and "default" in spec:
            args[k] = spec["default"]
            defaulted.append(k)

    if props:
        unknown = [k for k in list(args.keys()) if k not in props]
    for k in required:
        v = args.get(k)
        if k not in args or v is None or v == "":
            missing.append(k)

    return args, {"coerced": coerced, "defaulted": defaulted,
                  "missing_required": missing, "unknown": unknown}


def keyword_rank(query: str, tools: list, top_k: int = 8) -> list:
    """Rank tools by token overlap with the query (name match boosted). Fallback selector
    when embeddings are unavailable — beats returning all tools."""
    q = set(_TOKEN.findall((query or "").lower()))
    if not q:
        return tools[:top_k]
    scored = []
    for t in tools:
        name = (t.get("name") or "").lower()
        toks = set(_TOKEN.findall(name + " " + (t.get("description") or "").lower()))
        overlap = len(q & toks)
        score = overlap / (len(q) ** 0.5) if toks else 0.0
        if any(qt in name for qt in q):   # boost when a query term is in the tool name
            score += 0.5
        scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for s, t in scored[:top_k]]


# ---- self-test -----------------------------------------------------------------
if __name__ == "__main__":
    fails = 0

    def ck(n, c):
        global fails
        print(("  ok  " if c else " FAIL ") + n)
        if not c:
            fails += 1

    sch = {"type": "object", "properties": {
        "priority": {"type": "integer"}, "care_weight": {"type": "number"},
        "flag": {"type": "boolean"}, "tags": {"type": "array"},
        "topology": {"type": "string", "default": "hierarchical"},
        "mission": {"type": "string"},
    }, "required": ["mission"]}

    a, r = validate_and_repair("x", {"priority": "5", "care_weight": "0.5",
                                     "flag": "true", "tags": "a,b", "mission": "go"}, sch)
    ck("coerce int '5'->5", a["priority"] == 5 and isinstance(a["priority"], int))
    ck("coerce number '0.5'->0.5", a["care_weight"] == 0.5)
    ck("coerce bool 'true'->True", a["flag"] is True)
    ck("coerce array 'a,b'->list", a["tags"] == ["a", "b"])
    ck("default filled (topology)", a["topology"] == "hierarchical" and "topology" in r["defaulted"])
    ck("reports coerced fields", {"priority", "care_weight", "flag", "tags"} <= set(r["coerced"]))

    _, r2 = validate_and_repair("x", {}, sch)
    ck("missing required detected", r2["missing_required"] == ["mission"])

    _, r3 = validate_and_repair("x", {"mission": "go", "weird": 1}, sch)
    ck("unknown arg reported (not dropped)", r3["unknown"] == ["weird"])

    valid, r4 = validate_and_repair("x", {"mission": "go"}, sch)
    ck("good call passes clean", not r4["missing_required"] and valid["mission"] == "go")

    tools = [{"name": "get_weather", "description": "current weather for a city"},
             {"name": "send_email", "description": "send an email message"},
             {"name": "query_memory", "description": "search stored memories"}]
    ck("keyword_rank picks weather", keyword_rank("what is the weather today", tools, 2)[0]["name"] == "get_weather")
    ck("keyword_rank picks memory", keyword_rank("search my stored memory", tools, 1)[0]["name"] == "query_memory")

    print(f"\n{'PASS — tool_ops green' if fails == 0 else f'FAIL — {fails} check(s)'}")
    raise SystemExit(1 if fails else 0)
