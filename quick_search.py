#!/usr/bin/env python3
"""
Quick Web Search - Fast, Simple Web Search for Jarvis
Uses multiple sources for better results
"""

import requests
import json
import time
from typing import Dict, List, Optional
from collections import OrderedDict


class QuickSearch:
    """Fast web search with caching and multiple backends"""

    def __init__(self):
        self.cache = OrderedDict()
        self.cache_size = 100
        self.cache_ttl = 300  # 5 minutes

    def _get_cache(self, query: str) -> Optional[List[Dict]]:
        """Get cached results"""
        key = query.lower().strip()
        if key in self.cache:
            timestamp, results = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return results
        return None

    def _set_cache(self, query: str, results: List[Dict]):
        """Cache results"""
        key = query.lower().strip()
        self.cache[key] = (time.time(), results)
        if len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)

    def search(self, query: str, num_results: int = 5) -> Dict:
        """Fast web search"""
        # Check cache first
        cached = self._get_cache(query)
        if cached:
            return {"results": cached, "query": query, "cached": True}

        results = []

        # Try DuckDuckGo (fastest, no API key needed)
        results = self._duckduckgo(query, num_results)

        if not results:
            # Fallback to textise dot iitty
            results = self._textise(query, num_results)

        if results:
            self._set_cache(query, results)
            return {"results": results, "query": query, "cached": False}

        return {"error": "Search failed", "query": query}

    def _duckduckgo(self, query: str, num_results: int) -> List[Dict]:
        """DuckDuckGo search"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
                timeout=8,
            )

            if response.status_code != 200:
                return []

            import re

            results = []

            # Better pattern matching
            pattern = r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
            snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]*)'

            matches = re.findall(pattern, response.text)
            snippets = re.findall(snippet_pattern, response.text)

            for i, (url, title) in enumerate(matches[:num_results]):
                snippet = snippets[i] if i < len(snippets) else ""
                results.append(
                    {
                        "title": title.strip()[:200],
                        "url": url.strip()[:300],
                        "snippet": snippet.strip()[:300],
                    }
                )

            return results
        except Exception as e:
            return []

    def _textise(self, query: str, num_results: int) -> List[Dict]:
        """Fallback to textise dot iitty"""
        try:
            url = (
                f"https://lite.textise dot iitty.com/search?q={query.replace(' ', '+')}"
            )
            response = requests.get(url, timeout=5)
            # Simplified fallback
            return []
        except:
            return []

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.cache_size,
            "ttl": self.cache_ttl,
        }


# Global instance
_quick_search = None


def get_quick_search() -> QuickSearch:
    global _quick_search
    if _quick_search is None:
        _quick_search = QuickSearch()
    return _quick_search


# Quick function for direct use
def quick_search(query: str, num_results: int = 5) -> str:
    """Quick search that returns formatted string"""
    search = get_quick_search()
    result = search.search(query, num_results)

    if "error" in result:
        return f"I couldn't find information about {query}, Sir."

    results = result.get("results", [])
    if not results:
        return f"I couldn't find anything about {query}, Sir."

    # Format for voice
    lines = [f"Found {len(results)} results for '{query}':"]
    for i, r in enumerate(results[:3], 1):
        lines.append(f"{i}. {r['title']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:100]}...")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    search = QuickSearch()
    result = search.search("latest AI developments 2026", 5)
    print(json.dumps(result, indent=2))
