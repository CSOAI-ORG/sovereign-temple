"""
sovereign_search.py — ONE sovereign search layer for SOV3's agents.

Replaces the scattered DuckDuckGo / Google / Brave calls (quick_search.py,
sov3_tool_bridge.py, browser_automation_bridge.py, voice_pipeline/jarvis_skills.py)
with a single, swappable, privacy-first endpoint. Resilient fallback chain — the
"all three" answer to "Qwant as our sovereign search?":

  1. SearXNG  (SOVEREIGN_SEARCH_URL)  — a metasearch instance WE host. We set its
              engines to qwant + mojeek (+ brave/ddg), so this is Qwant & Mojeek
              behind a layer we fully control. JSON API. The most sovereign option:
              no key, no external dependency, no per-query cost, we own the box.
  2. Brave    (BRAVE_API_KEY)         — independent crawler/index (not Bing-backed),
              proper JSON API, FREE 2,000 queries/mo. The fastest reliable backend.
  3. Mojeek   (MOJEEK_API_KEY)        — UK-based, TRULY independent index (its own
              crawler). The most index-sovereign result source (paid API).
  4. Qwant    (no key)                — EU (French), privacy-first, GDPR. Sovereign
              in privacy & jurisdiction (note: historically Bing-syndicated; its API
              now blocks bots, so this tier is best-effort).
  5. DuckDuckGo HTML                  — last-resort backstop (note: DDG now serves an
              anti-bot page to scrapers, so this too is best-effort, not reliable).

EMPIRICALLY (2026-06): the no-key scrape tiers (Qwant API, DDG HTML, the "lite"
variants) are all blocked from datacenter/residential IPs. So a working sovereign
search needs ONE real backend up: a hosted SearXNG (tier 1) or a key (tier 2/3).
The scrape tiers remain only as a free best-effort tail.

Each tier is tried in order; the first that returns results wins. Every tier
normalises to: [{"title", "url", "snippet", "engine"}]. STDLIB ONLY (urllib) — no
new pip deps, no GPU, identical on the M-series Mac and the VM.

Config (all optional — with nothing set it works today via Qwant -> DuckDuckGo):
  SOVEREIGN_SEARCH_URL     e.g. http://127.0.0.1:8888     (your self-hosted SearXNG)
  MOJEEK_API_KEY           from mojeek.com/services/search
  SOVEREIGN_SEARCH_ORDER   override the chain, e.g. "searxng,mojeek,qwant,ddg"
  SOVEREIGN_SEARCH_TIMEOUT per-request seconds (default 8)

Why a chain and not just Qwant: Qwant has no clean agent API (you scrape, you get
rate-limited) and is Bing-backed, so it is sovereign-in-privacy but not
sovereign-in-index. The robust, genuinely-sovereign way to "use Qwant" is to run
it as one engine inside a SearXNG we own — which this layer is built to prefer.
"""
import os
import re
import json
import html
import urllib.parse
import urllib.request

# A browser-like UA — several privacy engines reject obvious bots.
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _timeout() -> float:
    try:
        return float(os.environ.get("SOVEREIGN_SEARCH_TIMEOUT", "8"))
    except ValueError:
        return 8.0


def _get(url: str, headers=None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=_timeout()) as r:
        return r.read().decode("utf-8", "replace")


def _strip(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


# ---- providers -------------------------------------------------------------
def _searxng(query: str, n: int):
    base = os.environ.get("SOVEREIGN_SEARCH_URL", "").rstrip("/")
    if not base:
        return []
    q = urllib.parse.urlencode({"q": query, "format": "json"})
    data = json.loads(_get(f"{base}/search?{q}"))
    out = []
    for r in data.get("results", [])[:n]:
        out.append({"title": r.get("title", ""), "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "engine": "searxng:" + (r.get("engine") or "?")})
    return out


def _brave(query: str, n: int):
    key = os.environ.get("BRAVE_API_KEY", "").strip()
    if not key:
        return []
    q = urllib.parse.urlencode({"q": query, "count": min(max(n, 1), 20)})
    data = json.loads(_get(f"https://api.search.brave.com/res/v1/web/search?{q}",
                           headers={"Accept": "application/json", "X-Subscription-Token": key}))
    res = ((data.get("web") or {}).get("results")) or []
    return [{"title": _strip(r.get("title", "")), "url": r.get("url", ""),
             "snippet": _strip(r.get("description", "")), "engine": "brave"} for r in res[:n]]


def _mojeek(query: str, n: int):
    key = os.environ.get("MOJEEK_API_KEY", "").strip()
    if not key:
        return []
    q = urllib.parse.urlencode({"q": query, "api_key": key, "fmt": "json", "t": max(1, n)})
    data = json.loads(_get(f"https://www.mojeek.com/search?{q}"))
    res = ((data.get("response") or {}).get("results")) or []
    return [{"title": r.get("title", ""), "url": r.get("url", ""),
             "snippet": r.get("desc", ""), "engine": "mojeek"} for r in res[:n]]


def _qwant(query: str, n: int):
    q = urllib.parse.urlencode({"q": query, "count": min(max(n, 1), 10), "locale": "en_GB",
                                "offset": 0, "safesearch": 1, "device": "desktop", "t": "web"})
    data = json.loads(_get(f"https://api.qwant.com/v3/search/web?{q}",
                           headers={"Accept": "application/json", "Origin": "https://www.qwant.com"}))
    # Qwant nests results deeply and inconsistently — walk for any {url,title} node.
    out, seen = [], set()

    def walk(node):
        if isinstance(node, dict):
            u, t = node.get("url"), node.get("title")
            if u and t and u not in seen:
                seen.add(u)
                out.append({"title": _strip(t), "url": u,
                            "snippet": _strip(node.get("desc", "")), "engine": "qwant"})
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data.get("data"))
    return out[:n]


def _ddg(query: str, n: int):
    q = urllib.parse.urlencode({"q": query})
    txt = _get(f"https://html.duckduckgo.com/html/?{q}")
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)".*?>(.*?)</a>', txt, re.S):
        url = urllib.parse.unquote(m.group(1))
        # DDG wraps targets in a redirect — pull the real uddg= param when present.
        mm = re.search(r"[?&]uddg=([^&]+)", url)
        if mm:
            url = urllib.parse.unquote(mm.group(1))
        out.append({"title": _strip(m.group(2)), "url": url, "snippet": "", "engine": "ddg"})
        if len(out) >= n:
            break
    return out


_PROVIDERS = {"searxng": _searxng, "brave": _brave, "mojeek": _mojeek,
              "qwant": _qwant, "ddg": _ddg}
_DEFAULT_ORDER = "searxng,brave,mojeek,qwant,ddg"


def sovereign_search(query: str, n: int = 5, order: str = None) -> dict:
    """Try each sovereign provider in order; the first non-empty result set wins.
    Never raises — returns {ok, engine, query, results:[{title,url,snippet,engine}], tried}."""
    chain = (order or os.environ.get("SOVEREIGN_SEARCH_ORDER", _DEFAULT_ORDER)).split(",")
    tried = []
    for name in [c.strip() for c in chain if c.strip() in _PROVIDERS]:
        try:
            res = _PROVIDERS[name](query, n)
            tried.append(f"{name}:{len(res)}")
            if res:
                return {"ok": True, "engine": name, "query": query, "results": res, "tried": tried}
        except Exception as e:
            tried.append(f"{name}:err({type(e).__name__})")
    return {"ok": False, "engine": None, "query": query, "results": [], "tried": tried}


# Back-compat alias for the scattered callers we are unifying.
def web_search(query: str, num_results: int = 5) -> dict:
    return sovereign_search(query, num_results)


if __name__ == "__main__":
    import sys
    qy = " ".join(sys.argv[1:]) or "EU AI Act Article 50 transparency"
    r = sovereign_search(qy, 5)
    print(f"engine={r['engine']}  ok={r['ok']}  tried={r['tried']}")
    for i, it in enumerate(r["results"], 1):
        print(f"  {i}. [{it['engine']}] {it['title']}\n     {it['url']}")
