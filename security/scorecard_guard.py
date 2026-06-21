"""
scorecard_guard.py — cold-tier risk scoring for MCP server packages.

Bridges `mcp_scorecard.scorer` into the SOV3 security ensemble:
  * SecurityBrain cold tier reads `_risk_score`, `_cat_security`, `_has_security_md`
    from tool arguments and can HOLD a low-score / low-security package.
  * BFT threat council gets a `scorecard_risk` lens.
  * SOV3 exposes a `security_scorecard` tool that returns the rubric.

Pure stdlib + mcp_scorecard. Import failures are caught and surfaced in the
result rather than crashing the caller.
"""
from __future__ import annotations

import os
import sys
from dataclasses import asdict
from typing import Any, Optional

# Make the upstream scorecard engine importable from this repo layout.
_SCORECARD_PATH = os.path.expanduser("~/clawd/mcp-marketplace/mcp-scorecard-mcp")
if _SCORECARD_PATH not in sys.path:
    sys.path.insert(0, _SCORECARD_PATH)

try:
    from mcp_scorecard.scorer import collect_static, collect_pypi, score
except Exception as _sc_err:  # pragma: no cover
    collect_static = None  # type: ignore
    collect_pypi = None  # type: ignore
    score = None  # type: ignore
    _SCORECARD_IMPORT_ERROR = str(_sc_err)
else:
    _SCORECARD_IMPORT_ERROR = None


# ── thresholds (override via env while we tune false positives) ──────────────
RISK_SCORE_MIN = float(os.environ.get("SCORECARD_RISK_SCORE_MIN", "50"))
RISK_SECURITY_MIN = float(os.environ.get("SCORECARD_RISK_SECURITY_MIN", "5"))


def score_package(dir_path: str, include_pypi: bool = False) -> dict:
    """Run the 100-point MCP scorecard rubric on a local package directory.

    Returns a flat dict with the total, category scores, and security-relevant
    signals. Network-dependent PyPI lookup is opt-in via `include_pypi`.
    """
    if score is None:
        return {
            "error": f"mcp_scorecard not importable: {_SCORECARD_IMPORT_ERROR}",
            "dir_path": dir_path,
        }
    if not os.path.isdir(dir_path):
        return {"error": f"not a directory: {dir_path}"}

    static = collect_static(dir_path)
    pypi = None
    if include_pypi and static.package_name:
        pypi = collect_pypi(static.package_name)

    card = score(static, pypi)
    categories = {c.name: c.points for c in card.categories}

    return {
        "package_name": card.package_name,
        "dir_name": card.dir_name,
        "total": card.total,
        "max_total": card.max_total,
        "distance_to_100": card.distance_to_100,
        "flagship_candidate": card.flagship_candidate,
        "downloads_30d": card.downloads_30d,
        "categories": categories,
        "has_security_md": static.has_security_md,
        "cat_security": categories.get("Security"),
        "server_py_parses": static.server_py_parses,
        "num_tools": static.num_tools,
        "framework": static.framework,
        "static": asdict(static),
        "pypi": asdict(pypi) if pypi else {},
    }


def risk_signal(arguments: Optional[dict]) -> dict:
    """Extract scorecard risk fields that SecurityBrain / BFT council understand.

    Looks for `_risk_score`, `_cat_security`, `_has_security_md`, `_risk_tier`
    at the top level, or inside a nested `scorecard` dict.
    """
    if not arguments:
        return {}

    out: dict[str, Any] = {}
    for key in ("_risk_score", "_cat_security", "_has_security_md", "_risk_tier"):
        if key in arguments:
            out[key] = arguments[key]

    nested = arguments.get("scorecard") or {}
    if isinstance(nested, dict):
        if "total" in nested and "_risk_score" not in out:
            out["_risk_score"] = nested["total"]
        if "cat_security" in nested and "_cat_security" not in out:
            out["_cat_security"] = nested["cat_security"]
        if "has_security_md" in nested and "_has_security_md" not in out:
            out["_has_security_md"] = nested["has_security_md"]

    return out


def evaluate_risk(arguments: Optional[dict]) -> dict:
    """Canonical cold-tier scorecard risk evaluation.

    Returns a dict:
        {
            "risky": bool,
            "risk_score": float|None,
            "cat_security": float|None,
            "has_security_md": bool|None,
            "reasons": [str],
        }
    """
    sig = risk_signal(arguments)
    risk_score = sig.get("_risk_score")
    cat_security = sig.get("_cat_security")
    has_security_md = sig.get("_has_security_md")

    reasons: list[str] = []
    if risk_score is not None and float(risk_score) < RISK_SCORE_MIN:
        reasons.append(f"score={risk_score} < {RISK_SCORE_MIN}")
    if cat_security is not None and float(cat_security) < RISK_SECURITY_MIN:
        reasons.append(f"security_cat={cat_security} < {RISK_SECURITY_MIN}")
    if has_security_md is False:
        reasons.append("SECURITY.md missing")

    return {
        "risky": bool(reasons),
        "risk_score": risk_score,
        "cat_security": cat_security,
        "has_security_md": has_security_md,
        "reasons": reasons,
    }


# ── Self-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fails = 0

    def check(name, cond):
        global fails
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond:
            fails += 1

    print("scorecard_guard self-test")

    # Score a known-good local package (the scorecard engine itself).
    res = score_package(_SCORECARD_PATH)
    check("score_package returns total", isinstance(res.get("total"), (int, float)))
    check("score_package returns Security category", res.get("cat_security") is not None)
    check("has_security_md field present", isinstance(res.get("has_security_md"), bool))

    # Risk evaluation logic.
    low = evaluate_risk({"_risk_score": 30, "_cat_security": 3, "_has_security_md": False})
    check("low score marked risky", low["risky"] is True and len(low["reasons"]) >= 2)

    ok = evaluate_risk({"_risk_score": 85, "_cat_security": 8, "_has_security_md": True})
    check("high score marked safe", ok["risky"] is False)

    none = evaluate_risk({})
    check("no signal means not risky", none["risky"] is False)

    nested = evaluate_risk({"scorecard": {"total": 40, "cat_security": 2, "has_security_md": False}})
    check("nested scorecard signal parsed", nested["risky"] is True)

    print(f"\n{'PASS — scorecard_guard green' if fails == 0 else f'FAIL — {fails} check(s)'}")
    raise SystemExit(1 if fails else 0)
