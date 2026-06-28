"""validate_council_toml.py — sanity check for sovereign-council.toml.

Catches structural problems before the council fires:
- King present + has 'mandate' field
- 12 queens present (not 11, not 13)
- All agents have all required fields
- Veto queens (queen-care, queen-watch) are present
- Task count matches agent count + 1 (King's synthesis task)
- BFT math: f=floor((13-1)/3)=4, quorum=2f+1=9
"""
import sys
import tomllib
from pathlib import Path

REQUIRED_AGENT_FIELDS = {"name", "type", "task", "arcana", "domain", "color",
                         "mandate", "first_words", "personality"}
EXPECTED_QUEENS = {
    "queen-strategy", "queen-care", "queen-compliance", "queen-finance",
    "queen-domain", "queen-arcana", "queen-brain", "queen-proactive",
    "queen-bridge", "queen-distribution", "queen-council", "queen-watch",
}
VETO_QUEENS = {"queen-care", "queen-watch"}


def report(errors, warnings, tpl, p, n=None, f=None, quorum=None,
           len_agents=None, leader=None, tasks=None):
    """Print validation report. Returns 0 if no errors, 1 otherwise."""
    print(f"\n=== Sovereign Council Toml Validation ===")
    print(f"File: {p}")
    if tpl.get("template"):
        print(f"Template: {tpl['template'].get('name', '?')} "
              f"({(tpl['template'].get('description') or '?')[:80]})")
    if leader:
        print(f"Leader: {leader.get('name', '?')} ({leader.get('arcana', '?')})")
    if n is not None and len_agents is not None:
        print(f"Queens: {len_agents} of {len(EXPECTED_QUEENS)} expected")
    if tasks is not None:
        print(f"Tasks: {len(tasks)} (1 King + {len(tasks)-1} queen tasks)")
    if n is not None and tpl.get("template", {}).get("agents"):
        actual = {a["name"] for a in tpl["template"]["agents"]}
        print(f"Veto queens: {VETO_QUEENS & actual}")
    if n is not None and f is not None:
        print(f"\n  BFT math: n={n} nodes, f={f} (max malicious), quorum={quorum} of {n}")
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"\n✅ All structural checks pass.")
    return 0


def main():
    p = Path(__file__).parent / "sovereign-council.toml"
    if not p.exists():
        print(f"❌ File not found: {p}")
        return 1
    try:
        with p.open("rb") as f:
            tpl = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        return report([f"Toml parse error: {e}"], [], {}, p)

    errors = []
    warnings = []

    if "template" not in tpl:
        return report(["missing [template] section"], warnings, tpl, p)

    template = tpl.get("template", {})
    if template.get("name") != "sovereign-council":
        errors.append(f"template.name should be 'sovereign-council', got {template.get('name')!r}")

    leader = template.get("leader")
    if leader is None:
        errors.append("missing [template.leader] section")
        return report(errors, warnings, tpl, p)
    if leader.get("name") != "queen-king":
        errors.append(f"leader.name should be 'queen-king', got {leader.get('name')!r}")
    if "mandate" not in leader:
        errors.append("leader missing 'mandate' field")

    agents = template.get("agents", [])
    actual = {a["name"] for a in agents}
    if actual != EXPECTED_QUEENS:
        missing = EXPECTED_QUEENS - actual
        extra = actual - EXPECTED_QUEENS
        if missing:
            errors.append(f"Missing queens: {missing}")
        if extra:
            warnings.append(f"Unexpected queens: {extra}")

    if not VETO_QUEENS.issubset(actual):
        errors.append(f"Missing veto queens: {VETO_QUEENS - actual}")

    for a in [leader] + agents:
        missing_fields = REQUIRED_AGENT_FIELDS - set(a.keys())
        if missing_fields:
            errors.append(f"Agent {a.get('name', '?')} missing fields: {missing_fields}")

    tasks = template.get("tasks", [])
    expected_task_count = 1 + len(agents)
    if len(tasks) != expected_task_count:
        errors.append(f"Expected {expected_task_count} tasks, got {len(tasks)}")

    task_owners = {t["owner"] for t in tasks}
    expected_owners = {leader.get("name")} | actual
    if task_owners != expected_owners:
        missing = expected_owners - task_owners
        extra = task_owners - expected_owners
        if missing:
            errors.append(f"Missing task owners: {missing}")
        if extra:
            warnings.append(f"Unexpected task owners: {extra}")

    n = 1 + len(agents)
    f = (n - 1) // 3
    quorum = 2 * f + 1
    if quorum != 9:
        warnings.append(f"BFT quorum is {quorum}, expected 9")

    return report(errors, warnings, tpl, p, n=n, f=f, quorum=quorum,
                  len_agents=len(agents), leader=leader, tasks=tasks)


if __name__ == "__main__":
    sys.exit(main())