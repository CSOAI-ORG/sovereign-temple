"""
Promotion Engine — repurposes one approved piece into 5 platform-native drafts.

Input: a research memo OR an approved revenue/content/*.md blog post.
Output: 5 ready-to-paste drafts in revenue/promotion/<date>_<slug>/:

  - dev_to.md          (DEV.to: front-matter + tags)
  - hashnode.md        (Hashnode: front-matter + cover image hint)
  - medium.md          (Medium: standard markdown, no front-matter)
  - substack.md        (Substack: open-friendly + subject line + preview)
  - linkedin.txt       (LinkedIn post: 3 short paragraphs + hook + CTA)
  - twitter_thread.txt (X/Twitter: 7-9 tweet thread, each ≤280 chars)
  - reddit_<sub>.md    (Reddit posts for r/SaaS, r/MachineLearning, r/EuropeanUnion)

Each draft passes through the council audit BEFORE writing.

Usage:
    python promotion_engine.py --memo revenue/research/<date>_*.md
    python promotion_engine.py --content revenue/content/<date>_*.md
    python promotion_engine.py --latest    # pick newest of either
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_gateway import call  # noqa: E402
from external_council_voice import audit_completed_work  # noqa: E402

log = logging.getLogger("promotion-engine")

CLAWD = Path("/Users/nicholas/clawd")
RESEARCH_DIR = CLAWD / "revenue" / "research"
CONTENT_DIR = CLAWD / "revenue" / "content"
PROMOTION_DIR = CLAWD / "revenue" / "promotion"
PROMOTION_DIR.mkdir(parents=True, exist_ok=True)


# ── Prompts (one per platform) ──────────────────────────────────────────────

DEV_TO_PROMPT = """You are writing a DEV.to article from this source memo.

SOURCE:
{source}

RULES:
- DEV.to front-matter at the top (---title/published/description/tags/cover_image/canonical_url---)
- 6-7 tags max, all lowercase, dash-separated (e.g. opensource, mcp, eu-ai-act, compliance, ai)
- 1200-1800 words
- One H1 (matches title), then H2/H3 hierarchy
- Code blocks where relevant (e.g. `uvx <pkg>` install commands)
- Concrete dates, numbers, names — no fluff
- Include relevant /mcp/<slug> links inline as natural references
- End with: ONE clear "what to do" CTA (install, try, star repo)
- Canonical URL should point to meok.ai blog version when promoted

Return the COMPLETE article in markdown (front-matter included, no JSON wrap).
"""


HASHNODE_PROMPT = """Same source as the DEV.to version. Adapt for Hashnode:

SOURCE:
{source}

DIFFERENCES from DEV.to:
- Hashnode front-matter: ---title/subtitle/tags/cover/canonical_url/slug---
- 800-1200 words (shorter than DEV.to)
- More personal voice (Hashnode favors developer storytelling)
- Same canonical_url pointing to meok.ai

Return the complete article (front-matter included, no JSON wrap).
"""


MEDIUM_PROMPT = """Adapt for Medium publication.

SOURCE:
{source}

RULES:
- NO front-matter (Medium has UI for metadata)
- Start with the H1 title as the first line
- 1000-1400 words
- More journalistic / story-led than DEV.to
- Open with a SPECIFIC observation, not a thesis statement
- Subheadings are H2 (##)
- Include one pull-quote highlighted with > blockquote syntax

Return the complete article body in markdown (no preamble).
"""


SUBSTACK_PROMPT = """Adapt for Substack newsletter.

SOURCE:
{source}

RULES:
- Top of file: SUBJECT LINE (under 50 chars) on first line
- Second line: PREVIEW TEXT (under 100 chars, what shows in inbox)
- Then a blank line, then the H1
- 700-1100 words (shorter — readers are in their inbox)
- Conversational, friendly tone
- ONE link to a meok.ai resource near the top
- ONE CTA at the bottom (subscribe, try free, reply)

Return everything in markdown.
"""


LINKEDIN_PROMPT = """Adapt for a LinkedIn post (not article).

SOURCE:
{source}

RULES:
- ZERO formatting (LinkedIn strips markdown)
- 200-280 words total
- Opens with a HOOK in line 1 (a specific number, deadline, or counter-intuitive claim)
- 3-4 short paragraphs, each 2-3 sentences max
- Blank lines between paragraphs for scannability
- ONE clear CTA at the bottom (e.g. "DM me if you want the install command")
- No hashtag spam — 3-5 relevant hashtags ONLY at the very end

Return plain text (no markdown).
"""


TWITTER_PROMPT = """Adapt for an X/Twitter thread.

SOURCE:
{source}

RULES:
- 7-9 tweets total
- Each tweet ≤ 280 chars (HARD limit)
- Tweet 1: HOOK — specific number, name, or counter-intuitive claim that makes people stop scrolling
- Tweets 2-7: one specific fact + concrete detail per tweet
- Tweets 8-9: CTA + link (only 1 link, in last tweet)
- Number tweets like "1/", "2/", etc.
- No hashtag spam — 0-2 hashtags total at end of thread

Return as plain text, ONE TWEET PER LINE, separated by blank lines.
"""


REDDIT_PROMPT = """Adapt for r/{subreddit}.

SOURCE:
{source}

RULES for r/{subreddit}:
{rules}

Return:
TITLE: <reddit post title, ≤ 300 chars>
---
<body in markdown, follow r/{subreddit} norms>
"""

REDDIT_SUB_CONFIGS = {
    "SaaS": (
        "- Personal voice, founder-style, no marketing speak\n"
        "- 300-500 words\n"
        "- Open with the specific problem you hit\n"
        "- Be honest about not yet having revenue (don't fake traction)\n"
        "- Include the install command + 1 link, max 2 links total\n"
        "- Title under 80 chars"
    ),
    "MachineLearning": (
        "- Use [P] prefix in title (e.g. '[P] I built 39 MCP servers...')\n"
        "- 400-700 words\n"
        "- Technical, code-led — show one architectural decision\n"
        "- Cite specific regulations (EU AI Act Article 50, DORA Art 17) not vague claims\n"
        "- Open weights / open source angle\n"
        "- 1 GitHub link, 1 paper-style description, no marketing"
    ),
    "EuropeanUnion": (
        "- Frame as ABOUT the regulation, not selling the tool\n"
        "- 300-500 words\n"
        "- Title is informative (e.g. 'EU AI Act Article 50 takes effect 2 Nov 2026 — what changes')\n"
        "- ONLY mention the tool once, near the bottom, as a free open-source aid\n"
        "- No salesy tone — Reddit will sniff it out"
    ),
}


# ── Drafting pipeline ───────────────────────────────────────────────────────

PLATFORMS = [
    ("dev_to.md", DEV_TO_PROMPT, "right"),
    ("hashnode.md", HASHNODE_PROMPT, "right"),
    ("medium.md", MEDIUM_PROMPT, "right"),
    ("substack.md", SUBSTACK_PROMPT, "left"),
    ("linkedin.txt", LINKEDIN_PROMPT, "left"),
    ("twitter_thread.txt", TWITTER_PROMPT, "left"),
]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def draft_platform(source: str, name: str, prompt_tmpl: str, task: str) -> dict:
    log.info(f"  drafting {name} via {task} brain...")
    prompt = prompt_tmpl.format(source=source[:8000])
    result = call(
        messages=[{"role": "user", "content": prompt}],
        task=task, max_tokens=3500,
    )
    if result.get("error"):
        return {"error": result["error"], "name": name}
    return {
        "name": name,
        "text": result.get("text", "").strip(),
        "provider": result.get("provider"),
        "cost": result.get("cost_usd", 0),
    }


def draft_reddit(source: str, subreddit: str) -> dict:
    log.info(f"  drafting reddit r/{subreddit}...")
    prompt = REDDIT_PROMPT.format(
        subreddit=subreddit,
        rules=REDDIT_SUB_CONFIGS[subreddit],
        source=source[:8000],
    )
    result = call(
        messages=[{"role": "user", "content": prompt}],
        task="right", max_tokens=2500,
    )
    if result.get("error"):
        return {"error": result["error"], "name": f"reddit_{subreddit.lower()}.md"}
    return {
        "name": f"reddit_{subreddit.lower()}.md",
        "text": result.get("text", "").strip(),
        "provider": result.get("provider"),
        "cost": result.get("cost_usd", 0),
    }


async def run_promotion(source_path: Path) -> dict:
    source_text = source_path.read_text()
    title_match = re.search(r"^#\s+(.+)$", source_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source_path.stem
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = PROMOTION_DIR / f"{today}_{slugify(title)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"=== promoting: {title}")
    log.info(f"=== output: {out_dir}")

    drafts = []
    for name, prompt_tmpl, task in PLATFORMS:
        d = draft_platform(source_text, name, prompt_tmpl, task)
        drafts.append(d)

    for sub in ("SaaS", "MachineLearning", "EuropeanUnion"):
        d = draft_reddit(source_text, sub)
        drafts.append(d)

    # Audit the full bundle as ONE proposal (council reviews together)
    summary = "\n\n---\n\n".join(
        f"PLATFORM: {d['name']}\n\n{(d.get('text') or d.get('error', ''))[:2000]}"
        for d in drafts
    )
    audit = await audit_completed_work(
        title=f"Promotion bundle: {title[:80]}",
        description=f"Source: {source_path.name}\n\nGenerated {len(drafts)} platform-native drafts.\n\nBundle preview:\n{summary[:5000]}",
        action_type="promotion_bundle",
        action_params={"source": source_path.name, "platforms": [d["name"] for d in drafts]},
    )

    # Write each draft (even rejected ones — human reviews)
    written = []
    for d in drafts:
        if d.get("error"):
            log.warning(f"  {d['name']} skipped: {d['error']}")
            continue
        path = out_dir / d["name"]
        path.write_text(d["text"])
        written.append(d["name"])

    # Write INDEX.md with summary
    total_cost = sum(d.get("cost", 0) for d in drafts)
    index = f"""# Promotion bundle: {title}

**Date:** {today}
**Source:** `{source_path.relative_to(CLAWD)}`
**Drafts:** {len(written)} / {len(drafts)}
**Council vote:** {audit.get('external_majority', '?').upper()}
**Generation cost:** ${total_cost:.5f}

---

## How to use

Each file below is a platform-native draft. Pick which platforms to actually post on
based on where your target audience hangs out:

- `dev_to.md` — paste into dev.to/new (technical devs)
- `hashnode.md` — hashnode.com/create (technical devs, shorter)
- `medium.md` — medium.com/new-story (broader tech + biz)
- `substack.md` — your Substack post editor (newsletter list)
- `linkedin.txt` — LinkedIn post composer (B2B + founders) [needs your account]
- `twitter_thread.txt` — X.com (split tweets, one per blank-line block)
- `reddit_saas.md` — reddit.com/r/SaaS/submit (founder community)
- `reddit_machinelearning.md` — reddit.com/r/MachineLearning [P] (ML researchers, Saturday only)
- `reddit_europeanunion.md` — reddit.com/r/europeanunion (EU regulation focus, no salesy tone)

## Files

"""
    for name in sorted(written):
        index += f"- [{name}](./{name})\n"
    index += f"\n\n## Audit details\n\n- Proposal ID: `{audit.get('proposal_id', '?')}`\n- Voices polled: {audit.get('voices_polled', 0)}\n- Approve / Reject / Abstain: {audit.get('approve_count', 0)} / {audit.get('reject_count', 0)} / {audit.get('abstain_count', 0)}\n\n*This script does NOT auto-post anywhere. Human review + manual post required.*\n"
    (out_dir / "INDEX.md").write_text(index)

    return {
        "title": title,
        "source": str(source_path),
        "out_dir": str(out_dir),
        "drafts_written": len(written),
        "council_majority": audit.get("external_majority"),
        "cost_usd": round(total_cost, 5),
    }


def latest_source() -> Path | None:
    candidates = []
    for d in (RESEARCH_DIR, CONTENT_DIR):
        if d.exists():
            candidates += list(d.glob("*.md"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Promotion engine: 1 source → 9 platform-native drafts")
    p.add_argument("--memo", help="path to research memo")
    p.add_argument("--content", help="path to content piece")
    p.add_argument("--latest", action="store_true", help="newest of either")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    src: Path | None = None
    if args.memo:
        src = Path(args.memo)
    elif args.content:
        src = Path(args.content)
    elif args.latest:
        src = latest_source()

    if not src or not src.exists():
        print("Error: --memo <path> | --content <path> | --latest")
        sys.exit(1)

    result = asyncio.run(run_promotion(src))
    print(json.dumps(result, indent=2))
