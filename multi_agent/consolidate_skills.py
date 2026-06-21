"""
consolidate_skills.py — reversible de-duplication of the SOV3 skill library.

Acts on the Curator finding (256 near-duplicate clusters in data/skill_library.db). For each
cluster it keeps ONE canonical skill (highest care_score, then usage, then earliest) and moves
the rest to a `skills_archived` table (NOT deleted from disk — restorable). The FTS5 triggers
keep the search index in sync on delete.

Reversible two ways: (1) the .bak DB copy, (2) the skills_archived table (re-INSERT to restore).

Usage:  python3 consolidate_skills.py            # dry-run (counts only)
        python3 consolidate_skills.py --execute  # apply
"""
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curator import SkillCurator

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "skill_library.db")


def main(execute: bool = False):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute(
        "SELECT id, skill_hash, task_type, title, description, care_score, usage_count, "
        "validated, created_at, updated_at FROM skills"
    ).fetchall()]
    by_hash = {r["skill_hash"]: r for r in rows}

    clusters = SkillCurator().find_duplicates(rows)
    to_archive = []
    for cl in clusters:
        members = [by_hash[h] for h in cl if h in by_hash]
        if len(members) < 2:
            continue
        canonical = sorted(
            members,
            key=lambda m: (-(m.get("care_score") or 0.0), -(m.get("usage_count") or 0),
                           m.get("created_at") or ""),
        )[0]
        for m in members:
            if m["skill_hash"] != canonical["skill_hash"]:
                to_archive.append((m["skill_hash"], canonical["skill_hash"]))

    print(f"  skills={len(rows)}  dup_clusters={len(clusters)}  "
          f"to_archive={len(to_archive)}  keep={len(rows) - len(to_archive)}")

    if not execute:
        print("  DRY-RUN — no changes. Re-run with --execute to apply.")
        c.close()
        return

    c.execute("""
        CREATE TABLE IF NOT EXISTS skills_archived (
            id INTEGER, skill_hash TEXT, task_type TEXT, title TEXT, description TEXT,
            yaml_body TEXT, care_score REAL, usage_count INTEGER, validated INTEGER,
            created_at TEXT, updated_at TEXT, archived_reason TEXT, canonical_hash TEXT, archived_at TEXT)
    """)
    now = datetime.utcnow().isoformat()
    n = 0
    for dup_hash, canon in to_archive:
        full = c.execute("SELECT * FROM skills WHERE skill_hash=?", (dup_hash,)).fetchone()
        if not full:
            continue
        c.execute(
            "INSERT INTO skills_archived (id,skill_hash,task_type,title,description,yaml_body,"
            "care_score,usage_count,validated,created_at,updated_at,archived_reason,canonical_hash,archived_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (full["id"], full["skill_hash"], full["task_type"], full["title"], full["description"],
             full["yaml_body"], full["care_score"], full["usage_count"], full["validated"],
             full["created_at"], full["updated_at"], "duplicate", canon, now),
        )
        c.execute("DELETE FROM skills WHERE skill_hash=?", (dup_hash,))
        n += 1
    c.commit()
    remain = c.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    arch = c.execute("SELECT COUNT(*) FROM skills_archived").fetchone()[0]
    c.close()
    print(f"  EXECUTED: archived {n}  |  skills remaining {remain}  |  skills_archived total {arch}")
    print("  Restore any skill: INSERT back from skills_archived, or restore the .bak DB.")


if __name__ == "__main__":
    main("--execute" in sys.argv)
