#!/usr/bin/env python3
"""GitHub Scanner Agent — Monitors new repos, stars, releases

Usage:
    python github_scanner.py --query "llm router" --days 1
    python github_scanner.py --repo "BerriAI/litellm" --watch-releases
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class GitHubScanner:
    """Scans GitHub for relevant repositories and activity."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or ""
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MEOKCLAW-ResearchSwarm/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _api_request(self, url: str) -> Dict[str, Any]:
        """Make authenticated GitHub API request."""
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def search_repos(self, query: str, sort: str = "updated", per_page: int = 30) -> List[Dict]:
        """Search GitHub repositories."""
        url = (
            f"https://api.github.com/search/repositories"
            f"?q={query.replace(' ', '+')}"
            f"&sort={sort}&order=desc&per_page={per_page}"
        )
        data = self._api_request(url)
        return data.get("items", [])

    def get_repo_activity(self, owner: str, repo: str, days: int = 7) -> Dict[str, Any]:
        """Get recent activity for a repository."""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        # Get recent commits
        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since}&per_page=10"
        commits = self._api_request(commits_url)

        # Get recent releases
        releases_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=5"
        releases = self._api_request(releases_url)

        return {
            "repo": f"{owner}/{repo}",
            "commits": len(commits),
            "releases": [r.get("tag_name", "unknown") for r in releases[:3]],
            "latest_commit": commits[0].get("commit", {}).get("message", "")[:100] if commits else "None",
        }

    def scan_competitors(self) -> List[Dict[str, Any]]:
        """Scan known competitor repositories."""
        competitors = [
            ("BerriAI", "litellm"),
            ("Portkey-AI", "gateway"),
            ("helicone", "helicone"),
            ("langfuse", "langfuse"),
            ("openrouter", "openapi"),
        ]

        results = []
        for owner, repo in competitors:
            try:
                activity = self.get_repo_activity(owner, repo, days=1)
                if activity["commits"] > 0 or activity["releases"]:
                    results.append(activity)
            except Exception as e:
                print(f"   Error scanning {owner}/{repo}: {e}")

        return results

    def find_new_tools(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Find new tools by keyword."""
        keywords = keywords or [
            "llm router",
            "ai gateway",
            "prompt injection defense",
            "model ensemble",
            "ai orchestration",
        ]

        results = []
        for keyword in keywords:
            try:
                repos = self.search_repos(keyword, per_page=5)
                for repo in repos:
                    # Only include repos updated in last 7 days
                    updated = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
                    if datetime.now(updated.tzinfo) - updated < timedelta(days=7):
                        results.append({
                            "name": repo["full_name"],
                            "stars": repo["stargazers_count"],
                            "language": repo.get("language", "Unknown"),
                            "description": repo.get("description", "")[:200],
                            "url": repo["html_url"],
                            "updated": repo["updated_at"],
                        })
            except Exception as e:
                print(f"   Error searching '{keyword}': {e}")

        return results


def main():
    parser = argparse.ArgumentParser(description="GitHub Scanner for MEOKCLAW")
    parser.add_argument("--token", help="GitHub API token")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--repo", help="Owner/repo to monitor")
    parser.add_argument("--competitors", action="store_true", help="Scan competitors")
    parser.add_argument("--new-tools", action="store_true", help="Find new tools")
    args = parser.parse_args()

    scanner = GitHubScanner(token=args.token)

    if args.query:
        repos = scanner.search_repos(args.query)
        print(f"Found {len(repos)} repositories for '{args.query}':")
        for repo in repos[:10]:
            print(f"  - {repo['full_name']} ({repo['stargazers_count']} stars)")
            print(f"    {repo.get('description', '')[:100]}")

    elif args.repo:
        owner, repo = args.repo.split("/")
        activity = scanner.get_repo_activity(owner, repo)
        print(json.dumps(activity, indent=2))

    elif args.competitors:
        results = scanner.scan_competitors()
        print("Competitor Activity (last 24h):")
        for r in results:
            print(f"  {r['repo']}: {r['commits']} commits, releases: {r['releases']}")

    elif args.new_tools:
        tools = scanner.find_new_tools()
        print(f"Found {len(tools)} recently updated tools:")
        for tool in tools:
            print(f"  - {tool['name']} ({tool['stars']} stars, {tool['language']})")
            print(f"    {tool['description']}")

    else:
        # Default: scan everything
        print("=== Competitor Scan ===")
        competitors = scanner.scan_competitors()
        for c in competitors:
            print(f"  {c['repo']}: {c['commits']} commits")

        print("\n=== New Tools ===")
        tools = scanner.find_new_tools()
        for t in tools[:10]:
            print(f"  - {t['name']} ({t['stars']} stars)")


if __name__ == "__main__":
    main()
