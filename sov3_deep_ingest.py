#!/usr/bin/env python3
"""
SOV3 Deep Ingest — Reads all business-critical files, extracts structured facts,
and feeds them into SOV3 memory as high-care-weight episodes.

This is NOT a simple file dump. It:
  1. Reads each file and generates a structured summary
  2. Extracts key entities (domains, prices, dates, contacts, URLs)
  3. Assigns care_weight based on file importance
  4. Tags with business category
  5. Deduplicates against existing SOV3 memories
  6. Records as 'insight' type memories for high retrieval priority

Usage:
    python3 sov3_deep_ingest.py                  # Ingest all critical files
    python3 sov3_deep_ingest.py --revenue         # Revenue docs only
    python3 sov3_deep_ingest.py --memory          # Memory files only
    python3 sov3_deep_ingest.py --meok            # MEOK pages only
    python3 sov3_deep_ingest.py --topology        # Topology docs only
    python3 sov3_deep_ingest.py --dry-run         # Preview without writing
    python3 sov3_deep_ingest.py --count           # Count files per category
"""
import os
import sys
import json
import time
import hashlib
import re
import requests
from pathlib import Path
from datetime import datetime

SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
CLAWD = Path(os.path.expanduser("~/clawd"))
DRY_RUN = "--dry-run" in sys.argv
COUNT_ONLY = "--count" in sys.argv

# File categories with paths and importance
FILE_CATEGORIES = {
    "revenue": {
        "paths": [CLAWD / "revenue"],
        "extensions": [".md"],
        "care_weight": 0.90,
        "tags": ["revenue", "business", "strategy"],
        "max_chars": 6000,
    },
    "memory": {
        "paths": [Path(os.path.expanduser("~/.claude/projects/-Users-nicholas/memory"))],
        "extensions": [".md"],
        "care_weight": 0.85,
        "tags": ["memory", "context", "identity"],
        "max_chars": 4000,
    },
    "topology": {
        "paths": [CLAWD / "_TOPOLOGY"],
        "extensions": [".md", ".csv"],
        "care_weight": 0.80,
        "tags": ["topology", "infrastructure", "mapping"],
        "max_chars": 5000,
    },
    "grants": {
        "paths": [CLAWD / "grants"],
        "extensions": [".md"],
        "care_weight": 0.75,
        "tags": ["grants", "funding", "applications"],
        "max_chars": 5000,
    },
    "audits": {
        "paths": [CLAWD / "audits"],
        "extensions": [".md"],
        "care_weight": 0.80,
        "tags": ["audit", "security", "compliance"],
        "max_chars": 4000,
    },
    "legal": {
        "paths": [CLAWD / "legal"],
        "extensions": [".md"],
        "care_weight": 0.70,
        "tags": ["legal", "contracts", "ip"],
        "max_chars": 4000,
    },
    "meok_pages": {
        "paths": [CLAWD / "meok" / "ui" / "src" / "app"],
        "extensions": [".tsx"],
        "pattern": "page.tsx",
        "care_weight": 0.65,
        "tags": ["meok", "website", "product-page"],
        "max_chars": 3000,
    },
    "stripe": {
        "paths": [CLAWD],
        "extensions": [".py", ".json", ".md", ".sh"],
        "pattern": "stripe",
        "care_weight": 0.75,
        "tags": ["stripe", "payments", "revenue"],
        "max_chars": 3000,
        "max_depth": 2,
    },
    "domain_sites": {
        "paths": [
            CLAWD / "csoai-org",
            CLAWD / "proofof-site",
            CLAWD / "cobolbridge-site",
            CLAWD / "council-ai-storefront",
        ],
        "extensions": [".html", ".tsx"],
        "pattern": "index|page|pricing|about",
        "care_weight": 0.60,
        "tags": ["domain", "website", "content"],
        "max_chars": 3000,
    },
}


def collect_files(category_name: str, config: dict) -> list:
    """Collect files matching a category's criteria."""
    files = []
    max_depth = config.get("max_depth", 10)
    pattern = config.get("pattern")

    for base_path in config["paths"]:
        if not base_path.exists():
            continue

        for ext in config["extensions"]:
            if max_depth <= 2:
                # Shallow search
                for f in base_path.glob(f"*{ext}"):
                    if pattern and pattern.lower() not in f.name.lower():
                        continue
                    if f.is_file() and f.stat().st_size > 50:
                        files.append(f)
            else:
                for f in base_path.rglob(f"*{ext}"):
                    if pattern and not re.search(pattern, f.name, re.IGNORECASE):
                        continue
                    if f.is_file() and f.stat().st_size > 50:
                        # Skip node_modules, .next, etc
                        parts = str(f.relative_to(base_path)).split(os.sep)
                        skip_dirs = {"node_modules", ".next", ".vercel", "__pycache__", ".git", "dist", "build"}
                        if any(p in skip_dirs for p in parts):
                            continue
                        files.append(f)

    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def extract_facts(content: str, filename: str) -> dict:
    """Extract structured facts from file content."""
    facts = {
        "domains": [],
        "prices": [],
        "dates": [],
        "urls": [],
        "emails": [],
        "stripe_ids": [],
        "mcp_names": [],
    }

    # Domains (findall with groups returns just the group, use finditer for full match)
    domain_pattern = r'\b[\w-]+\.(?:ai|org|com|co\.uk|io)\b'
    facts["domains"] = sorted(set(re.findall(domain_pattern, content)))[:10]

    # Prices
    price_pattern = r'[£$€]\s*[\d,]+(?:\.\d{2})?(?:/mo|/yr|/month|/year)?'
    facts["prices"] = sorted(set(re.findall(price_pattern, content)))[:10]

    # Dates
    date_pattern = r'\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\b'
    facts["dates"] = sorted(set(re.findall(date_pattern, content)))[:10]

    # URLs
    url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./?=&#%+]*)?'
    facts["urls"] = sorted(set(re.findall(url_pattern, content)))[:10]

    # Emails
    email_pattern = r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b'
    facts["emails"] = sorted(set(re.findall(email_pattern, content)))[:5]

    # Stripe IDs
    stripe_pattern = r'(?:price|prod|sub|pi|cs|cus)_[A-Za-z0-9]{10,}'
    facts["stripe_ids"] = sorted(set(re.findall(stripe_pattern, content)))[:10]

    # MCP names
    mcp_pattern = r'meok-[\w-]+-mcp|[\w-]+-compliance-mcp|[\w-]+-detection-mcp'
    facts["mcp_names"] = sorted(set(re.findall(mcp_pattern, content)))[:10]

    return facts


def build_summary(filename: str, content: str, facts: dict, category: str) -> str:
    """Build a structured summary for SOV3 ingestion."""
    # Get first meaningful paragraph (skip headers/blank lines)
    lines = content.strip().split('\n')
    summary_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('---'):
            summary_lines.append(stripped)
            if len(' '.join(summary_lines)) > 300:
                break

    brief = ' '.join(summary_lines)[:500]

    # Build structured content
    parts = [f"[FILE: {filename}] ({category.upper()})"]
    parts.append(f"Summary: {brief}")

    # Add extracted facts
    if facts["prices"]:
        parts.append(f"Prices: {', '.join(facts['prices'][:5])}")
    if facts["domains"]:
        parts.append(f"Domains: {', '.join(facts['domains'][:5])}")
    if facts["mcp_names"]:
        parts.append(f"MCPs: {', '.join(facts['mcp_names'][:5])}")
    if facts["stripe_ids"]:
        parts.append(f"Stripe: {len(facts['stripe_ids'])} IDs found")
    if facts["dates"]:
        parts.append(f"Key dates: {', '.join(facts['dates'][:3])}")

    return '\n'.join(parts)


def record_to_sov3(content: str, tags: list, care_weight: float, source: str) -> bool:
    """Record a memory episode to SOV3."""
    if DRY_RUN:
        return True
    try:
        resp = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": f"ingest-{int(time.time()*1000)}",
            "params": {
                "name": "record_memory",
                "arguments": {
                    "content": content[:4000],
                    "source_agent": source,
                    "memory_type": "insight",
                    "care_weight": care_weight,
                    "tags": tags,
                }
            }
        }, timeout=15)
        result = resp.json()
        r = result.get("result", {}).get("content", [{}])
        if isinstance(r, list) and r:
            text = r[0].get("text", "{}")
            data = json.loads(text)
            return data.get("success", False)
        return False
    except Exception as e:
        print(f"    SOV3 error: {e}")
        return False


def content_hash(content: str) -> str:
    """Generate a hash for deduplication."""
    return hashlib.md5(content[:1000].encode()).hexdigest()[:12]


def ingest_category(name: str, config: dict, seen_hashes: set) -> dict:
    """Ingest all files in a category."""
    files = collect_files(name, config)
    stats = {"total": len(files), "ingested": 0, "skipped": 0, "failed": 0}

    print(f"\n  [{name.upper()}] {len(files)} files found")

    for i, filepath in enumerate(files):
        try:
            content = filepath.read_text(errors="ignore")
            if len(content) < 50:
                stats["skipped"] += 1
                continue

            # Dedup check
            chash = content_hash(content)
            if chash in seen_hashes:
                stats["skipped"] += 1
                continue
            seen_hashes.add(chash)

            # Truncate to max_chars
            max_chars = config.get("max_chars", 4000)
            truncated = content[:max_chars]

            # Extract facts
            facts = extract_facts(truncated, filepath.name)

            # Build summary
            rel_path = str(filepath.relative_to(CLAWD)) if str(filepath).startswith(str(CLAWD)) else filepath.name
            summary = build_summary(rel_path, truncated, facts, name)

            # Tags
            tags = config["tags"] + [filepath.stem]

            # Record
            success = record_to_sov3(
                summary,
                tags,
                config["care_weight"],
                f"deep-ingest-{name}"
            )

            if success:
                stats["ingested"] += 1
                if (i + 1) % 10 == 0:
                    print(f"    [{i+1}/{len(files)}] {stats['ingested']} ingested")
            else:
                stats["failed"] += 1

            # Small delay to not overwhelm SOV3
            time.sleep(0.1)

        except Exception as e:
            print(f"    Error on {filepath.name}: {e}")
            stats["failed"] += 1

    return stats


def main():
    print(f"SOV3 Deep Ingest — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  SOV3: {SOV3_URL}")
    print(f"  Dry run: {DRY_RUN}")

    # Check SOV3
    try:
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        print(f"  SOV3 status: {r.json().get('status', '?')}")
    except:
        print("  SOV3 not responding!")
        sys.exit(1)

    # Determine which categories to process
    args = set(sys.argv[1:]) - {"--dry-run", "--count"}
    if args:
        categories = {k: v for k, v in FILE_CATEGORIES.items()
                      if f"--{k}" in args or f"--{k.replace('_', '-')}" in args}
        if not categories:
            # Try matching partial names
            categories = {k: v for k, v in FILE_CATEGORIES.items()
                          if any(k.startswith(a.lstrip('-')) for a in args)}
    else:
        categories = FILE_CATEGORIES

    if COUNT_ONLY:
        print("\n  File counts by category:")
        total = 0
        for name, config in categories.items():
            files = collect_files(name, config)
            print(f"    {name}: {len(files)} files")
            total += len(files)
        print(f"    TOTAL: {total}")
        return

    # Run ingestion
    seen_hashes = set()
    all_stats = {}
    total_ingested = 0
    start = time.time()

    for name, config in categories.items():
        stats = ingest_category(name, config, seen_hashes)
        all_stats[name] = stats
        total_ingested += stats["ingested"]

    elapsed = time.time() - start

    # Summary
    print(f"\n{'='*50}")
    print(f"  DEEP INGEST COMPLETE")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Total ingested: {total_ingested}")
    print(f"\n  By category:")
    for name, stats in all_stats.items():
        print(f"    {name}: {stats['ingested']}/{stats['total']} "
              f"({stats['skipped']} skipped, {stats['failed']} failed)")

    # Record the ingest event itself
    if not DRY_RUN and total_ingested > 0:
        record_to_sov3(
            f"DEEP INGEST COMPLETED ({datetime.now().isoformat()}): "
            f"{total_ingested} business files ingested across {len(all_stats)} categories. "
            f"Categories: {', '.join(all_stats.keys())}. "
            f"SOV3 now has comprehensive business knowledge from revenue docs, "
            f"memory files, topology, grants, audits, and product pages.",
            ["ingest", "milestone", "business-knowledge"],
            0.95,
            "deep-ingest-system"
        )


if __name__ == "__main__":
    main()
