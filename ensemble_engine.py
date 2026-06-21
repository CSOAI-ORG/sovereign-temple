#!/usr/bin/env python3
"""
SOV3 Ensemble Learning Engine — Connects SOV3 + Hindsight + Hermes.

This is the brain coordinator that:
  1. Feeds business files into Hindsight for fact extraction + entity resolution
  2. Syncs extracted facts/entities back to SOV3 memory
  3. Identifies knowledge gaps and triggers research
  4. Connects Hermes for outreach/scraping tasks
  5. Runs continuous learning loops

Usage:
    python3 ensemble_engine.py ingest       # Ingest all business files into Hindsight
    python3 ensemble_engine.py entities     # Show extracted entities
    python3 ensemble_engine.py recall       # Test recall on a query
    python3 ensemble_engine.py sync         # Sync Hindsight knowledge → SOV3
    python3 ensemble_engine.py gaps         # Identify knowledge gaps
    python3 ensemble_engine.py loop         # Run continuous learning loop
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
HINDSIGHT_URL = os.environ.get("HINDSIGHT_URL", "http://localhost:8765")
HERMES_URL = os.environ.get("HERMES_URL", "http://localhost:3000")
BANK_ID = "meok-empire"
CLAWD = Path(os.path.expanduser("~/clawd"))

# Priority files to ingest (ordered by business value)
PRIORITY_FILES = [
    # Revenue & strategy
    ("revenue/PRICING_SOURCE_OF_TRUTH.md", "pricing"),
    ("revenue/MASTER_ACTION_LIST_2026-05-05.md", "actions"),
    ("revenue/ALIGNMENT_2026-04-29.md", "strategy"),
    ("revenue/CARE_HOME_COLD_LIST_2026-04-29.md", "outreach"),
    ("revenue/CARE_HOME_EMAILS_READY_TO_SEND_2026-05-09.md", "outreach"),
    ("revenue/COLD_EMAILS_V2.md", "outreach"),
    ("revenue/LINKEDIN_DMS_READY_TO_SEND.md", "outreach"),
    ("revenue/LIVE_PAYMENT_LINKS_2026-05-09.md", "payments"),
    ("revenue/COMPETITIVE_SCORECARD_100_ROADMAP.md", "competitive"),
    ("revenue/BLUEPRINT_PIVOT_PLAN.md", "strategy"),
    ("revenue/DEEP_RESEARCH_LIVING_TOPOLOGY_2026-05-09.md", "architecture"),
    ("revenue/OUTREACH_MACHINE_2026-05-09.md", "outreach"),
    ("revenue/MULTI_PHASE_ACTION_PLAN_2026-05-09.md", "strategy"),
    ("revenue/BLOCKERS_2026-04-27.md", "blockers"),
    ("revenue/EOD_AUDIT_2026-04-27.md", "audit"),
    ("revenue/NLNET_GRANT_DRAFT_2026-04-26.md", "grants"),
    ("revenue/MCP_MASTER_REFERENCE.md", "mcp"),
    # Topology
    ("_TOPOLOGY/MASTER_INDEX.md", "topology"),
    ("_TOPOLOGY/DOMAINS.md", "domains"),
    ("_TOPOLOGY/REVENUE_OPPORTUNITIES.md", "opportunities"),
    ("_TOPOLOGY/A2A_GAPS.md", "gaps"),
    # Grants
    ("grants/nlnet/READY-TO-SUBMIT.md", "grants"),
    ("grants/innovate-uk/READY-TO-SUBMIT.md", "grants"),
    # Legal
    ("legal/TERMS_OF_SERVICE.md", "legal"),
    ("legal/PRIVACY_POLICY.md", "legal"),
    # Stripe
    ("stripe-activation-guide.md", "stripe"),
    ("unified-portfolio-catalog/stripe-products.json", "stripe"),
    # Audits
    ("audits/stripe-audit-2026-04-13.md", "audit"),
]


def hindsight_retain(content: str, metadata: dict = None, context: str = None) -> dict:
    """Send content to Hindsight for fact extraction and memory retention."""
    try:
        item = {"content": content[:8000]}
        if context:
            item["context"] = context
        if metadata:
            item["metadata"] = {k: str(v) for k, v in metadata.items()}

        resp = requests.post(
            f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/memories",
            json={"items": [item]},
            timeout=120,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def hindsight_recall(query: str, limit: int = 5) -> dict:
    """Query Hindsight for relevant facts."""
    try:
        resp = requests.post(
            f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/memories/recall",
            json={"query": query, "limit": limit},
            timeout=30,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def hindsight_entities() -> dict:
    """Get all extracted entities."""
    try:
        resp = requests.get(
            f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/entities",
            timeout=15,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def hindsight_graph() -> dict:
    """Get entity co-occurrence graph."""
    try:
        resp = requests.get(
            f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/entities/graph",
            timeout=15,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def hindsight_stats() -> dict:
    """Get bank statistics."""
    try:
        resp = requests.get(
            f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/stats",
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def sov3_record(content: str, tags: list, care_weight: float = 0.8):
    """Record to SOV3 memory."""
    try:
        requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": f"ensemble-{int(time.time())}",
            "params": {
                "name": "record_memory",
                "arguments": {
                    "content": content[:4000],
                    "source_agent": "ensemble-engine",
                    "memory_type": "insight",
                    "care_weight": care_weight,
                    "tags": tags,
                }
            }
        }, timeout=15)
    except Exception as e:
        print(f"  SOV3 error: {e}")


def cmd_ingest():
    """Ingest priority business files into Hindsight."""
    print(f"Ensemble Ingest — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Hindsight: {HINDSIGHT_URL}")
    print(f"  Bank: {BANK_ID}")
    print(f"  Files: {len(PRIORITY_FILES)}")

    success = 0
    failed = 0

    for filepath, category in PRIORITY_FILES:
        full_path = CLAWD / filepath
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(errors="ignore")
            if len(content) < 50:
                continue

            # Truncate very large files
            if len(content) > 8000:
                content = content[:8000] + "\n... [truncated]"

            # Prefix with file context
            enriched = f"[FILE: {filepath}] [CATEGORY: {category}]\n\n{content}"

            print(f"  [{success + failed + 1}/{len(PRIORITY_FILES)}] {filepath} ({len(content)} chars)...", end=" ")

            result = hindsight_retain(enriched, {"source": filepath, "category": category})

            if "error" in result:
                print(f"FAIL: {result['error'][:60]}")
                failed += 1
            else:
                print("OK")
                success += 1

            time.sleep(0.5)  # Don't overwhelm Ollama

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print(f"\n  Done: {success} ingested, {failed} failed")

    # Show stats
    stats = hindsight_stats()
    if "error" not in stats:
        print(f"  Bank stats: {json.dumps(stats, indent=2)[:500]}")


def cmd_entities():
    """Show extracted entities."""
    print("Hindsight Entities:")
    entities = hindsight_entities()
    if "error" in entities:
        print(f"  Error: {entities['error']}")
        return

    # Hindsight returns a list directly or nested under a key
    items = entities if isinstance(entities, list) else entities.get("entities", entities.get("items", []))
    if not items:
        print("  No entities extracted yet. Run 'ingest' first.")
        return

    # Sort by mention count descending
    sorted_items = sorted(items, key=lambda e: e.get("mention_count", 0), reverse=True)

    print(f"  Total: {len(sorted_items)}")
    print(f"  {'Entity':50s} | Mentions")
    print(f"  {'-'*65}")
    for ent in sorted_items[:40]:
        name = ent.get("canonical_name", ent.get("name", "?"))
        count = ent.get("mention_count", 0)
        print(f"    {name:50s} | {count}")


def cmd_recall():
    """Test recall with sample queries."""
    queries = [
        "What are the current pricing tiers for MEOK?",
        "What care homes have been contacted?",
        "What MCP packages have the most downloads?",
        "What is the EU AI Act Omnibus delay timeline?",
        "What grant applications are pending?",
        "What are the outstanding revenue blockers?",
    ]

    for q in queries:
        print(f"\n  Q: {q}")
        result = hindsight_recall(q, limit=3)
        if "error" in result:
            print(f"    Error: {result['error']}")
            continue

        memories = result.get("results", result.get("memories", []))
        if memories:
            for i, m in enumerate(memories[:2]):
                text = m.get("text", m.get("content", ""))[:200]
                context = m.get("context", "")
                rank = i + 1
                print(f"    #{rank} {text}")
                if context:
                    print(f"       ctx: {context}")
        else:
            print("    No results")


def cmd_sync():
    """Sync Hindsight knowledge back to SOV3."""
    print("Syncing Hindsight → SOV3...")

    entities = hindsight_entities()
    items = entities if isinstance(entities, list) else entities.get("entities", entities.get("items", []))

    if not items:
        print("  No entities to sync")
        return

    # Record entities as SOV3 knowledge
    entity_summary = []
    for ent in items:
        name = ent.get("canonical_name", ent.get("name", "?"))
        count = ent.get("mention_count", 0)
        entity_summary.append(f"{name} (x{count})")

    content = f"HINDSIGHT ENTITIES ({datetime.now().isoformat()}): {len(items)} entities extracted. " + ", ".join(entity_summary[:50])
    sov3_record(content, ["hindsight", "entities", "knowledge-sync"], 0.85)
    print(f"  Synced {len(items)} entities to SOV3")


def cmd_gaps():
    """Identify knowledge gaps by comparing SOV3 and Hindsight."""
    print("Knowledge Gap Analysis:")

    # Check what SOV3 knows
    try:
        resp = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "method": "tools/call", "id": "gaps",
            "params": {"name": "get_memory_stats", "arguments": {}}
        }, timeout=10)
        sov3_stats = json.loads(
            resp.json().get("result", {}).get("content", [{}])[0].get("text", "{}")
        )
        print(f"  SOV3: {sov3_stats.get('total_episodes', 0)} episodes")
    except:
        print("  SOV3: unavailable")

    # Check Hindsight
    stats = hindsight_stats()
    if "error" not in stats:
        print(f"  Hindsight: {json.dumps(stats)[:200]}")

    # Key business questions that should have answers
    test_queries = [
        ("pricing", "What are MEOK product prices?"),
        ("domains", "Which domains are live vs parked?"),
        ("stripe", "What Stripe products exist?"),
        ("mcps", "Which MCP packages have the most installs?"),
        ("grants", "What grant deadlines are approaching?"),
        ("outreach", "Who has been contacted for sales?"),
        ("legal", "What legal documents exist?"),
    ]

    gaps = []
    for area, query in test_queries:
        result = hindsight_recall(query, limit=1)
        memories = result.get("results", result.get("memories", []))
        if not memories:
            gaps.append(area)
            print(f"  GAP: {area} — no Hindsight results for '{query}'")
        else:
            text = memories[0].get("text", memories[0].get("content", ""))[:80]
            print(f"  OK:  {area} — '{text}'")

    if gaps:
        print(f"\n  {len(gaps)} gaps found. Run 'ingest' to fill them.")
    else:
        print(f"\n  No critical gaps found!")


def hermes_status() -> dict:
    """Check Hermes health and get cron status."""
    try:
        resp = requests.get(f"{HERMES_URL}/health", timeout=5)
        return {"status": "connected", "data": resp.json() if resp.status_code == 200 else {}}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


def hindsight_consolidate() -> dict:
    """Trigger Hindsight consolidation to process pending items."""
    try:
        resp = requests.post(
            f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/consolidate",
            timeout=30,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def cmd_loop():
    """Run continuous ensemble learning loop."""
    print(f"Ensemble Learning Loop starting...")
    print(f"  SOV3: {SOV3_URL}")
    print(f"  Hindsight: {HINDSIGHT_URL}")
    print(f"  Hermes: {HERMES_URL}")
    print(f"  Interval: 30 min")

    iteration = 0
    while True:
        iteration += 1
        print(f"\n{'='*50}")
        print(f"  Iteration {iteration} — {datetime.now().strftime('%H:%M:%S')}")

        # 1. Check for new/modified files across all business directories
        recent_files = []
        watch_dirs = [
            "revenue", "_TOPOLOGY", "audits", "grants", "legal",
            "meok", "sovereign-temple", "unified-portfolio-catalog",
        ]
        watch_extensions = {".md", ".py", ".json", ".tsx", ".csv"}
        cutoff = time.time() - 1800  # Last 30 min

        for d in watch_dirs:
            path = CLAWD / d
            if path.exists():
                for f in path.rglob("*"):
                    if (f.is_file()
                        and f.suffix in watch_extensions
                        and f.stat().st_mtime > cutoff
                        and f.stat().st_size > 50
                        and "node_modules" not in str(f)
                        and ".next" not in str(f)):
                        recent_files.append(f)

        if recent_files:
            print(f"  New/modified files: {len(recent_files)}")
            for f in recent_files[:20]:  # Cap at 20 per cycle
                try:
                    content = f.read_text(errors="ignore")[:6000]
                    rel = str(f.relative_to(CLAWD))
                    hindsight_retain(
                        f"[FILE UPDATE: {rel}]\n{content}",
                        {"source": rel, "updated": datetime.now().isoformat()}
                    )
                    print(f"    Ingested: {f.name}")
                    time.sleep(0.3)
                except Exception as e:
                    print(f"    Skip {f.name}: {e}")
        else:
            print(f"  No new files in last 30 min")

        # 2. Trigger Hindsight consolidation
        stats = hindsight_stats()
        pending = stats.get("pending_consolidation", 0) if "error" not in stats else 0
        if pending > 0:
            print(f"  Hindsight: {pending} pending consolidations, triggering...")
            hindsight_consolidate()

        # 3. Sync entities to SOV3
        cmd_sync()

        # 4. Check gaps
        cmd_gaps()

        # 5. Check Hermes status
        h = hermes_status()
        print(f"  Hermes: {h['status']}")

        # 6. Record loop iteration
        sov3_record(
            f"Ensemble loop iteration {iteration} at {datetime.now().isoformat()}. "
            f"New files: {len(recent_files)}. "
            f"Hindsight: {stats.get('total_nodes', '?')} nodes, {stats.get('total_links', '?')} links. "
            f"Hermes: {h['status']}. Bank: {BANK_ID}.",
            ["ensemble", "loop", "learning"],
            0.4
        )

        print(f"\n  Sleeping 30 minutes...")
        time.sleep(1800)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ingest"

    if cmd == "ingest":
        cmd_ingest()
    elif cmd == "entities":
        cmd_entities()
    elif cmd == "recall":
        cmd_recall()
    elif cmd == "sync":
        cmd_sync()
    elif cmd == "gaps":
        cmd_gaps()
    elif cmd == "loop":
        cmd_loop()
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: ingest, entities, recall, sync, gaps, loop")
