#!/usr/bin/env python3
"""
SOV3 DAILY EAT — cheapest/cleverest daily open-source data ingestion.
=====================================================================
Closes the loop SOV3 already half-has:
    curiosity_agent (finds knowledge GAPS) ─► [THIS] (fetches free data) ─►
    record_memory MCP (stores, hash-deduped) ─► nomic-embed-text (FREE local embed)

Design principles (why this is low-cost + clever):
  • ZERO paid APIs / ZERO keys — arXiv, HuggingFace Hub, GitHub public, RSS are all free.
  • FREE embedding — SOV3 already embeds via local Ollama nomic-embed-text (no per-doc cost).
  • DEDUP — content_hash gate (reuses sov3_deep_ingest pattern); never eat the same doc twice.
  • GAP-DIRECTED — pulls against curiosity_agent's gap report, not a firehose (relevance > volume).
  • BUDGETED — hard daily cap (default 40 docs) so it never runs away.
  • CARE-GATED — every doc routes through record_memory, which applies the Maternal Covenant floor.

Run: python3 sov3_daily_eat.py            (live, hits :3101 + free sources)
     python3 sov3_daily_eat.py --dry-run  (fetch + show, do NOT write to SOV3)
"""

import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
DAILY_CAP = int(os.environ.get("EAT_DAILY_CAP", "40"))
STATE_FILE = os.path.expanduser("~/.sov3_eat_seen.json")
UA = {"User-Agent": "MEOK-SOV3-DailyEat/1.0 (+https://meok.ai)"}

# Free, no-key sources. Queries get filled from SOV3's own gap report at runtime.
DEFAULT_TOPICS = [
    "AI safety alignment", "EU AI Act compliance", "multi-agent systems",
    "aquaculture welfare", "recirculating aquaculture", "humanoid robotics actuator",
]


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def content_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def load_seen() -> set:
    try:
        return set(json.load(open(STATE_FILE)))
    except Exception:
        return set()


def save_seen(seen: set):
    try:
        json.dump(sorted(seen), open(STATE_FILE, "w"))
    except Exception:
        pass


# ---- free source: arXiv (Atom API, no key) ---------------------------------

_ARXIV_LAST = [0.0]   # module-level: enforce arXiv's ~3s politeness window


def fetch_arxiv(query: str, n: int = 5, retries: int = 2) -> list:
    q = urllib.parse.quote(f"all:{query}")
    url = (f"http://export.arxiv.org/api/query?search_query={q}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={n}")
    for attempt in range(retries + 1):
        # arXiv API asks for >=3s between requests; honour it or get 429s
        wait = 3.1 - (time.time() - _ARXIV_LAST[0])
        if wait > 0:
            time.sleep(wait)
        try:
            xml = _get(url, timeout=25)
            _ARXIV_LAST[0] = time.time()
            break
        except Exception as e:
            _ARXIV_LAST[0] = time.time()
            is429 = "429" in str(e)
            if attempt == retries:
                # 429 = transient quota; not a real failure. Skip quietly, HF still feeds the eat.
                tag = "arxiv-throttled (skip; retries tomorrow)" if is429 else f"arxiv: {e}"
                return [{"_error": tag, "_soft": is429}]
            time.sleep((6.0 if is429 else 2.0) * (attempt + 1))  # longer backoff on 429
    else:
        return [{"_error": f"arxiv: exhausted retries"}]
    import re
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        summ = re.search(r"<summary>(.*?)</summary>", entry, re.S)
        link = re.search(r"<id>(.*?)</id>", entry, re.S)
        if title and summ:
            out.append({
                "source": "arxiv",
                "title": " ".join(title.group(1).split()),
                "summary": " ".join(summ.group(1).split())[:1500],
                "url": link.group(1).strip() if link else "",
                "topic": query,
            })
    return out


# ---- free source: HuggingFace Hub datasets (public API, no key) ------------

def fetch_hf_datasets(query: str, n: int = 3) -> list:
    url = (f"https://huggingface.co/api/datasets?search={urllib.parse.quote(query)}"
           f"&limit={n}&full=false")
    try:
        data = json.loads(_get(url))
    except Exception as e:
        return [{"_error": f"hf: {e}"}]
    return [{
        "source": "huggingface",
        "title": d.get("id", "?"),
        "summary": f"HF dataset {d.get('id')} · downloads={d.get('downloads',0)} · likes={d.get('likes',0)}",
        "url": f"https://huggingface.co/datasets/{d.get('id','')}",
        "topic": query,
    } for d in (data if isinstance(data, list) else [])]


# ---- free source: EUR-Lex (EU regulation — feeds the compliance moat) ------
# Uses the public EUR-Lex web search (no key). Best-effort HTML parse; soft-fails
# like arXiv so a EUR-Lex hiccup never breaks the eat. Highest-moat source:
# pulls actual EU legal text the compliance MCPs are built to interpret.

def fetch_eurlex(query: str, n: int = 3) -> list:
    url = ("https://eur-lex.europa.eu/search.html?type=quick&qid=1&"
           + urllib.parse.urlencode({"text": query}))
    try:
        html = _get(url, timeout=20)
    except Exception as e:
        return [{"_error": f"eurlex ({query[:20]}): {e}", "_soft": True}]
    import re as _re
    # extract CELEX result links + titles (best-effort; structure varies)
    items = []
    for m in _re.finditer(r'href="([^"]*legal-content/[^"]*CELEX[^"]*)"[^>]*>\s*([^<]{8,140})<', html):
        href, title = m.group(1), " ".join(m.group(2).split())
        if not title or title.lower().startswith(("more", "show")):
            continue
        full = href if href.startswith("http") else "https://eur-lex.europa.eu" + href.lstrip(".")
        items.append({"source": "eurlex", "title": title[:140],
                      "summary": f"EU legal document matching '{query}'. EUR-Lex: {full}",
                      "url": full, "topic": query})
        if len(items) >= n:
            break
    if not items:
        return [{"_error": f"eurlex ({query[:20]}): no parseable results", "_soft": True}]
    return items


# arXiv + HF are verified-working. EUR-Lex web-scrape is a STUB: EUR-Lex's real
# interface is the Cellar SPARQL/REST API, not the HTML search page — the scrape
# returns nothing reliably. Left registered (soft-fails harmlessly) but flagged
# TODO: replace fetch_eurlex with the Cellar API before relying on it. Not faking
# a working source. arXiv + HF carry the eat today.
SOURCES = {"arxiv": fetch_arxiv, "huggingface": fetch_hf_datasets}  # eurlex stub: see fetch_eurlex TODO


# ---- gap-directed topic selection (uses SOV3's own curiosity output) --------

def get_topics_from_sov3() -> list:
    """Ask SOV3 what it wants to learn; fall back to DEFAULT_TOPICS."""
    try:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "suggest_exploration", "arguments": {}}}
        req = urllib.request.Request(SOV3_URL + "/mcp", method="POST",
            data=json.dumps(payload).encode(),
            headers={**UA, "Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read().decode()
        if "data:" in body:
            body = [l[5:].strip() for l in body.splitlines() if l.startswith("data:")][-1]
        env = json.loads(body)
        txt = env["result"]["content"][0]["text"]
        obj = json.loads(txt)
        # be liberal about shape; harvest any string-ish suggestions
        cand = obj.get("suggestions") or obj.get("topics") or obj.get("domains") or []
        topics = [c if isinstance(c, str) else c.get("topic", "") for c in cand]
        topics = [t for t in topics if t]
        return topics[:6] or DEFAULT_TOPICS
    except Exception:
        return DEFAULT_TOPICS


def record_to_sov3(doc: dict) -> bool:
    body = (f"[{doc['source']}] {doc['title']}\n\n{doc['summary']}\n\nURL: {doc.get('url','')}")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "record_memory", "arguments": {
                   "content": body,
                   "memory_type": "research",
                   "tags": ["daily_eat", doc["source"], "open_source"],
                   "source_agent": "sov3_daily_eat",
               }}}
    try:
        req = urllib.request.Request(SOV3_URL + "/mcp", method="POST",
            data=json.dumps(payload).encode(),
            headers={**UA, "Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    dry = "--dry-run" in sys.argv
    seen = load_seen()
    topics = get_topics_from_sov3()
    print(f"SOV3 DAILY EAT — {'DRY RUN' if dry else 'LIVE'} | cap={DAILY_CAP} | "
          f"topics={len(topics)} (gap-directed)")
    print(f"  topics: {', '.join(topics)}")

    harvested, eaten, skipped = [], 0, 0
    src_ok, src_soft = set(), set()
    for topic in topics:
        for src, fn in SOURCES.items():
            for doc in fn(topic):
                if "_error" in doc:
                    if doc.get("_soft"):
                        src_soft.add(src)              # transient (e.g. arxiv 429) — quiet
                    else:
                        print(f"  ! {doc['_error']}")
                    continue
                src_ok.add(src)
                harvested.append(doc)
    if src_soft:
        print(f"  ~ soft-skipped (transient): {', '.join(sorted(src_soft))} — will retry next run")

    # dedup + cap
    fresh = []
    for doc in harvested:
        h = content_hash(doc["title"] + doc.get("url", ""))
        if h in seen:
            skipped += 1; continue
        fresh.append((h, doc))
    fresh = fresh[:DAILY_CAP]

    for h, doc in fresh:
        if dry:
            print(f"  [dry] {doc['source']:11} {doc['title'][:64]}")
            eaten += 1
        else:
            if record_to_sov3(doc):
                seen.add(h); eaten += 1
                print(f"  ✓ ate {doc['source']:11} {doc['title'][:60]}")
                time.sleep(0.3)  # be gentle on Ollama embed
            else:
                print(f"  ✗ failed {doc['title'][:50]}")

    if not dry:
        save_seen(seen)
    print(f"\nEAT COMPLETE: {eaten} new docs"
          f" | {skipped} already-seen (deduped) | {len(harvested)} fetched"
          f" | cost: £0 (free sources + local embed)")


if __name__ == "__main__":
    main()
