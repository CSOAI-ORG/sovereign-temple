#!/usr/bin/env python3
"""
SOV3 RESEARCH INGEST — curated, safe, repeatable ingestion of Nick's own research.
==================================================================================
Feeds Nick's high-value research docs into SOV3 memory so the council/agents (and
quantum scoring) can reason over them. NOT a 972-file firehose — curated + filtered.

SAFETY (hard rules, non-negotiable):
  • BANNED-TERM GATE — any file containing csga/james castle/terranova/chris james/
    open claw is SKIPPED and logged. Never poison memory with severed-tie material.
  • EXCLUDE _TOPOLOGY/RESEARCH/ entirely (known to contain severed terms).
  • DEDUP by content hash (persistent seen-set) — never double-ingest.
  • Chunk long docs to ~6k chars/record so local nomic-embed stays clean.

Cost: £0 — local Ollama nomic-embed-text, local postgres, no paid APIs.

Run: python3 sov3_ingest_research.py --dry-run   (scan + report, no writes)
     python3 sov3_ingest_research.py             (ingest)
"""

import hashlib
import json
import os
import re
import sys
import urllib.request

SOV3 = "http://localhost:3101/mcp"
ROOT = os.path.expanduser("~/clawd")
STATE = os.path.expanduser("~/.sov3_research_seen.json")

BANNED = re.compile(r"csga|james castle|terranova|chris james|open claw", re.I)

# Curated include-globs (relative to ROOT). High-value research only.
INCLUDE_DIRS = [
    "csoai-docs",          # white papers, charter, exec summaries
    "facility",            # the 24k sqft blueprint + phases
    "meok-sigil",          # SIGIL spec + thought layer
]
# Hard exclude — severed-term archive + noise
EXCLUDE = re.compile(r"_TOPOLOGY|node_modules|/\.git/|/_archive|/_inbox|package-lock|/dist/|egg-info")
CHUNK = 6000


def load_seen():
    try: return set(json.load(open(STATE)))
    except Exception: return set()


def save_seen(s):
    try: json.dump(sorted(s), open(STATE, "w"))
    except Exception: pass


def chash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]


def record(content, title, tags):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "record_memory", "arguments": {
            "content": content, "memory_type": "research",
            "tags": tags, "source_agent": "research_ingest"}}}
    req = urllib.request.Request(SOV3, method="POST", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception as e:
        return f"ERR {e}"


def collect():
    files = []
    for d in INCLUDE_DIRS:
        base = os.path.join(ROOT, d)
        for root, dirs, fs in os.walk(base):
            if EXCLUDE.search(root):
                continue
            for f in fs:
                if f.endswith((".md", ".txt")):
                    p = os.path.join(root, f)
                    if not EXCLUDE.search(p):
                        files.append(p)
    return sorted(set(files))


def main():
    dry = "--dry-run" in sys.argv
    seen = load_seen()
    files = collect()
    print(f"SOV3 RESEARCH INGEST — {'DRY RUN' if dry else 'LIVE'} | candidates: {len(files)}")

    ingested = banned = skipped = chunks = 0
    for p in files:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if BANNED.search(text):
            banned += 1
            print(f"  🚫 BANNED-TERM skip: {os.path.relpath(p, ROOT)}")
            continue
        rel = os.path.relpath(p, ROOT)
        # chunk
        parts = [text[i:i+CHUNK] for i in range(0, len(text), CHUNK)] or [text]
        for idx, part in enumerate(parts):
            h = chash(rel + str(idx) + part[:200])
            if h in seen:
                skipped += 1
                continue
            title = f"{rel}" + (f" [chunk {idx+1}/{len(parts)}]" if len(parts) > 1 else "")
            body = f"[RESEARCH] {title}\n\n{part}"
            if dry:
                print(f"  [dry] {title}")
                chunks += 1
            else:
                ok = record(body, title, ["research", "ip_corpus", "meok_research", "self_authored"])
                if ok is True:
                    seen.add(h); chunks += 1
                    print(f"  ✓ {title}")
                else:
                    print(f"  ✗ {title}: {ok}")
        ingested += 1

    if not dry:
        save_seen(seen)
    print(f"\nDONE: {ingested} files, {chunks} chunks ingested | "
          f"{banned} banned-skipped | {skipped} already-seen | cost £0")


if __name__ == "__main__":
    main()
