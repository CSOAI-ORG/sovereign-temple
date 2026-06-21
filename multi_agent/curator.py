"""
curator.py — Hermes "Curator" pattern integrated into SOV3.

We scrapped the Julian-Goldie "Hermes Agent OS" funnel (a resold Next.js dashboard) and
lifted the genuine upstream NousResearch/hermes-agent pattern that actually matters: the
CURATOR — an autonomous pass that grades the skill library by real usage, prunes dead
skills, flags fragile ones, and consolidates duplicates, so a 46-agent system doesn't rot.

Built on SOV3's real surfaces (no new deps, stdlib only):
  - SkillLibrary (data/skill_library.db): usage_count, care_score, validated, updated_at
  - SkillRegistry (in-memory): execution_count, success_rate
  - tool_dispatcher: calls_total / errors_total  (which tools are dead / fragile)

Report-first (like worm_guard): curate() only *recommends*; it never deletes. Pruning a
live skill/tool is destructive, so enforcement is a separate, explicit step.

Companion follow-ons noted but NOT built here (heavier / owner-gated): GEPA self-evolution
(DSPy eval loop to auto-repair fragile skills) and the messaging-gateway (Telegram/Discord).

Self-test: `python3 curator.py`
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

# classifications, worst-first (a skill gets the first that applies)
DEAD = "dead"            # never used -> prune candidate
FRAGILE = "fragile"      # executed but low success -> repair (GEPA) candidate
STALE = "stale"          # not touched in a long time -> review/demote
UNVALIDATED = "unvalidated"  # present but never validated -> validate
ACTIVE = "active"


def _age_days(updated_at: Any, now: datetime) -> Optional[float]:
    if not updated_at:
        return None
    try:
        s = str(updated_at).replace("Z", "")
        then = datetime.fromisoformat(s)
        return max(0.0, (now - then).total_seconds() / 86400.0)
    except Exception:
        return None


def _text(skill: dict) -> str:
    return (str(skill.get("title", "")) + " " + str(skill.get("description", ""))).lower().strip()


class SkillCurator:
    def __init__(self, stale_days: int = 45, fragile_success: float = 0.5,
                 dup_threshold: float = 0.82):
        self.stale_days = stale_days
        self.fragile_success = fragile_success
        self.dup_threshold = dup_threshold

    # ---- grade one skill -----------------------------------------------------
    def grade(self, skill: dict, now: datetime) -> dict:
        usage = int(skill.get("usage_count") or 0)
        execs = skill.get("execution_count")
        execs = int(execs) if execs is not None else None
        success = skill.get("success_rate")
        success = float(success) if success is not None else None
        validated = bool(skill.get("validated", True))  # sqlite stores 0/1; registry skills assume validated
        care = float(skill.get("care_score") or 0.0)
        age = _age_days(skill.get("updated_at") or skill.get("created_at"), now)

        reasons = []
        # worst-first classification
        never_used = usage <= 0 and (execs is None or execs <= 0)
        if never_used:
            cls = DEAD
            reasons.append("never used (usage_count=0, no executions)")
        elif success is not None and execs and execs > 0 and success < self.fragile_success:
            cls = FRAGILE
            reasons.append(f"low success_rate {success:.2f} over {execs} runs")
        elif age is not None and age > self.stale_days and usage < 3:
            cls = STALE
            reasons.append(f"not updated in {age:.0f}d, low usage ({usage})")
        elif not validated:
            cls = UNVALIDATED
            reasons.append("present but never validated")
        else:
            cls = ACTIVE

        # composite health score (for PROMOTE detection)
        u = min(usage / 50.0, 1.0)
        s = success if success is not None else 0.7
        r = 1.0 - min((age or 0) / 180.0, 1.0)
        score = round(0.4 * u + 0.3 * s + 0.15 * r + 0.15 * care, 3)

        return {
            "id": skill.get("skill_hash") or skill.get("name") or skill.get("id"),
            "title": skill.get("title") or skill.get("name"),
            "classification": cls, "score": score, "usage": usage,
            "validated": validated, "reasons": reasons,
        }

    # ---- duplicate detection (bounded: Jaccard pre-filter -> difflib refine) --
    def find_duplicates(self, skills: list) -> list:
        """Cluster near-duplicate skills. A cheap token-set Jaccard pre-filter (O(tokens)/pair)
        gates the expensive difflib refine so this stays fast at 1000s of skills; for very
        large libraries it only compares within task_type buckets to bound the n²."""
        n = len(skills)
        ids = [s.get("skill_hash") or s.get("name") or i for i, s in enumerate(skills)]
        texts = [_text(s) for s in skills]
        toks = [set(re.findall(r"[a-z0-9]+", t)) for t in texts]
        parent = {i: i for i in range(n)}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        # bound compute: only compare within task_type buckets once the library is large
        if n > 3000:
            buckets: dict = {}
            for i, s in enumerate(skills):
                buckets.setdefault(s.get("task_type", "_"), []).append(i)
            groups = list(buckets.values())
        else:
            groups = [list(range(n))]

        for grp in groups:
            for a in range(len(grp)):
                i = grp[a]
                if not toks[i]:
                    continue
                for b in range(a + 1, len(grp)):
                    j = grp[b]
                    if not toks[j]:
                        continue
                    inter = len(toks[i] & toks[j])
                    if not inter:
                        continue
                    if inter / len(toks[i] | toks[j]) < 0.30:   # cheap pre-filter
                        continue
                    if difflib.SequenceMatcher(None, texts[i], texts[j]).ratio() >= self.dup_threshold:
                        parent[find(i)] = find(j)

        clusters: dict = {}
        for i in range(n):
            clusters.setdefault(find(i), []).append(ids[i])
        return [members for members in clusters.values() if len(members) >= 2]

    # ---- grade tools from dispatcher stats -----------------------------------
    def grade_tools(self, tool_stats: Optional[dict]) -> dict:
        if not tool_stats:
            return {"dead": [], "fragile": []}
        calls = tool_stats.get("calls_total", {}) or {}
        errors = tool_stats.get("errors_total", {}) or {}
        all_names = tool_stats.get("all_tool_names") or list(calls.keys())
        dead = sorted([t for t in all_names if int(calls.get(t, 0)) == 0])
        fragile = sorted([t for t, c in calls.items()
                          if int(c) > 0 and int(errors.get(t, 0)) / int(c) > 0.3])
        return {"dead": dead, "fragile": fragile}

    # ---- the curation pass ---------------------------------------------------
    def curate(self, skills: list, tool_stats: Optional[dict] = None,
               now: Optional[datetime] = None) -> dict:
        now = now or datetime.utcnow()
        graded = [self.grade(s, now) for s in skills]

        def of(cls):
            return [g for g in graded if g["classification"] == cls]

        dups = self.find_duplicates(skills)
        promote = sorted([g for g in graded if g["classification"] == ACTIVE and g["score"] >= 0.75],
                         key=lambda g: g["score"], reverse=True)[:10]
        tools = self.grade_tools(tool_stats)

        recs = []
        if of(DEAD):
            recs.append({"action": "PRUNE", "what": "skills", "ids": [g["id"] for g in of(DEAD)],
                         "why": "never used — archive to reduce surface"})
        if dups:
            recs.append({"action": "CONSOLIDATE", "what": "duplicate skill clusters", "clusters": dups,
                         "why": "near-identical — merge to one canonical skill"})
        if of(FRAGILE):
            recs.append({"action": "REPAIR", "what": "fragile skills (GEPA candidates)",
                         "ids": [g["id"] for g in of(FRAGILE)], "why": "low success rate — re-tune prompt/tests"})
        if of(UNVALIDATED):
            recs.append({"action": "VALIDATE", "what": "unvalidated skills",
                         "ids": [g["id"] for g in of(UNVALIDATED)], "why": "never validated — run validation tests"})
        if of(STALE):
            recs.append({"action": "REVIEW", "what": "stale skills", "ids": [g["id"] for g in of(STALE)],
                         "why": "untouched + low usage — demote or refresh"})
        if tools["dead"]:
            recs.append({"action": "PRUNE", "what": "dead tools (0 calls)", "tools": tools["dead"],
                         "why": "registered but never called"})
        if tools["fragile"]:
            recs.append({"action": "REPAIR", "what": "fragile tools (>30% errors)", "tools": tools["fragile"],
                         "why": "high failure rate"})
        if promote:
            recs.append({"action": "PROMOTE", "what": "high-value skills",
                         "ids": [g["id"] for g in promote], "why": "high usage+success — surface first"})

        return {
            "summary": {
                "total_skills": len(skills),
                "active": len(of(ACTIVE)), "dead": len(of(DEAD)), "fragile": len(of(FRAGILE)),
                "stale": len(of(STALE)), "unvalidated": len(of(UNVALIDATED)),
                "duplicate_clusters": len(dups),
                "dead_tools": len(tools["dead"]), "fragile_tools": len(tools["fragile"]),
                "promote": len(promote),
            },
            "recommendations": recs,
            "graded": graded,
            "tools": tools,
            "mode": "report-only (no skill/tool was pruned; recommendations only)",
        }


# ---- self-test ------------------------------------------------------------------
if __name__ == "__main__":
    fails = 0

    def check(name, cond):
        global fails
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond:
            fails += 1

    now = datetime(2026, 6, 6)
    recent = "2026-06-01T10:00:00"
    old = "2025-09-01T10:00:00"

    skills = [
        {"skill_hash": "s1", "title": "Summarise a document", "description": "produce a concise summary of a text",
         "usage_count": 50, "care_score": 0.9, "validated": 1, "updated_at": recent,
         "success_rate": 0.95, "execution_count": 40},
        {"skill_hash": "s2", "title": "Old unused export", "description": "export legacy format nobody uses",
         "usage_count": 0, "care_score": 0.3, "validated": 0, "updated_at": old, "execution_count": 0},
        {"skill_hash": "s3", "title": "Flaky web scrape", "description": "scrape a site that often fails",
         "usage_count": 12, "care_score": 0.5, "validated": 1, "updated_at": recent,
         "success_rate": 0.2, "execution_count": 12},
        {"skill_hash": "s4", "title": "Quarterly report builder", "description": "build a quarterly report",
         "usage_count": 2, "care_score": 0.6, "validated": 1, "updated_at": old,
         "success_rate": 0.9, "execution_count": 2},
        {"skill_hash": "s5", "title": "Summarize documents", "description": "produce a concise summary of text",
         "usage_count": 30, "care_score": 0.85, "validated": 1, "updated_at": recent,
         "success_rate": 0.9, "execution_count": 25},
    ]
    tool_stats = {"all_tool_names": ["alpha", "beta", "gamma"],
                  "calls_total": {"alpha": 100, "beta": 5}, "errors_total": {"beta": 4}}

    cur = SkillCurator()
    rep = cur.curate(skills, tool_stats, now=now)
    g = {x["id"]: x["classification"] for x in rep["graded"]}

    check("active skill graded active", g["s1"] == ACTIVE)
    check("never-used skill graded dead", g["s2"] == DEAD)
    check("low-success skill graded fragile", g["s3"] == FRAGILE)
    check("old low-usage skill graded stale", g["s4"] == STALE)
    check("duplicate cluster found (s1≈s5)", any({"s1", "s5"} <= set(c) for c in cur.find_duplicates(skills)))
    check("dead tool detected (gamma, 0 calls)", "gamma" in rep["tools"]["dead"])
    check("fragile tool detected (beta, 80% err)", "beta" in rep["tools"]["fragile"])
    actions = {r["action"] for r in rep["recommendations"]}
    check("recommends PRUNE", "PRUNE" in actions)
    check("recommends CONSOLIDATE", "CONSOLIDATE" in actions)
    check("recommends REPAIR", "REPAIR" in actions)
    check("recommends PROMOTE", "PROMOTE" in actions)
    check("report-only (non-destructive)", rep["mode"].startswith("report-only"))

    print(f"\n{'PASS — curator green' if fails == 0 else f'FAIL — {fails} check(s)'}")
    raise SystemExit(1 if fails else 0)
