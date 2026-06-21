"""
Content Engine
==============
Generates meok.ai marketing content (blog posts, case studies, landing pages,
competitor-comparison pages, SEO-targeted listicles) using the dual-brain
stack with multi-stage council audit at every step.

Pipeline per content piece:
  1. RESEARCH    — research_synthesizer gathers facts (if topic warrants)
  2. OUTLINE     — LEFT brain (Step 3.6) drafts a structured outline
  3. DRAFT       — RIGHT brain (Claude or fallback) writes the prose
  4. SEO POLISH  — LEFT brain adds meta tags, H1/H2 hierarchy, internal links
  5. AUDIT       — BFT council votes on factual accuracy + brand voice
  6. WRITE       — markdown file in revenue/content/ for human review
                   (Nick promotes to meok/ui/src/app/blog/<slug>/page.tsx)
  7. COMMIT      — auto-commit on approve, log on reject

CRITICAL: Output is always markdown by default, not directly to the live
site. Human review + manual promotion to Next.js required to prevent
mistakes from going public.

Usage
-----
    # Process next item from queue:
    python content_engine.py --pick-next

    # Specific topic:
    python content_engine.py --topic "EU AI Act care home compliance" --type blog --words 800

    # Show queue:
    python content_engine.py --show-queue
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_gateway import call  # noqa: E402
from external_council_voice import audit_completed_work  # noqa: E402

log = logging.getLogger("content-engine")

CLAWD = Path("/Users/nicholas/clawd")
CONTENT_DIR = CLAWD / "revenue" / "content"
QUEUE_FILE = CLAWD / "revenue" / "CONTENT_QUEUE.md"
REJECTS_LOG = Path("/tmp/content_rejects.log")
COMPLETED_LOG = Path("/tmp/content_completed.log")

CONTENT_DIR.mkdir(parents=True, exist_ok=True)


# ── Stage prompts ───────────────────────────────────────────────────────────

OUTLINE_PROMPT = """You are the LEFT BRAIN drafting the structural outline for a {content_type}
about: "{topic}"

Target audience: SMB / startup founders + compliance leads at care homes,
SaaS companies, fintech, and SMEs in the EU who need to comply with EU AI
Act, DORA, NIS2, CRA, or related regulations.

Tone: direct, specific, concrete numbers + deadlines, light irreverence.
Anti-tone: marketing fluff, "leverage synergies", buzzwords.

MEOK products to weave in naturally (don't force):
- 39 MIT-licensed MCP servers (eu-ai-act-compliance, dora-compliance, etc.)
- £29/mo Starter (HMAC-signed attestations) / £79/mo Pro
- Self-host free forever
- meok.ai/mcp/{{slug}} pages for each MCP

Target length: {words} words.

Return a JSON object (no markdown):
{{
  "title": "max 60-char H1",
  "slug": "url-friendly slug",
  "meta_description": "max 155-char SEO description",
  "primary_keyword": "the main keyword this targets",
  "outline": [
    {{"heading": "H2 heading", "key_points": ["point", "point"]}},
    ...
  ],
  "cta": "the single conversion action at the end",
  "internal_links": ["meok.ai/mcp/...", "meok.ai/...", ...]
}}
"""


DRAFT_PROMPT = """You are the RIGHT BRAIN writing the full {content_type} prose from this outline.

OUTLINE (JSON):
{outline_json}

RULES:
- Open with a SPECIFIC observation (not a generic "in today's fast-changing world")
- One H1 (the title) at the top; H2s match the outline headings
- Concrete numbers + dates + names wherever possible
- No fabricated quotes, no fake testimonials, no "we partnered with X"
- Mention MEOK products IN CONTEXT (e.g. "the same way `uvx eu-ai-act-compliance-mcp` will…"),
  not as a sales pitch break
- End with the CTA from the outline as a final paragraph
- Use markdown formatting throughout

Target length: {words} words (±15%).

Return the COMPLETE markdown body (no JSON wrapper, no preamble — just the markdown starting with "# title").
"""


SEO_POLISH_PROMPT = """You are the LEFT BRAIN doing SEO polish on this draft.

DRAFT (markdown):
{draft}

YOUR JOB:
1. Ensure ONE H1 at top + correct H2 hierarchy
2. Ensure primary keyword "{primary_keyword}" appears in: H1, first paragraph,
   one H2, and the last paragraph (4 placements total — natural, not stuffed)
3. Add a "Frequently asked questions" H2 near the bottom with 3 FAQ items
   relevant to the topic (Schema.org FAQ markup ready)
4. Add 3 internal links inline (use markdown link syntax, point to:
   {internal_links})
5. Keep word count within ±15% of original
6. Don't add any new factual claims — only restructure / SEO

Return JUST the polished markdown (no preamble).
"""


# ── Stage runners ───────────────────────────────────────────────────────────

def stage_outline(topic: str, content_type: str, words: int) -> dict:
    log.info(f"[stage 1] outline: {topic}")
    prompt = OUTLINE_PROMPT.format(content_type=content_type, topic=topic, words=words)
    # Outline can be 2-3k tokens of structured JSON — give plenty of headroom to avoid truncation
    result = call(
        messages=[{"role": "user", "content": prompt}],
        task="left", max_tokens=6000,
        response_format={"type": "json_object"},
    )
    if result.get("error"):
        return {"error": result["error"]}
    text = (result.get("text") or "").strip()
    if not text:
        return {"error": f"outline empty content from {result.get('provider')}", "raw_preview": str(result)[:300]}
    if text.startswith("```"):
        text = re.sub(r"^```\w*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        outline = json.loads(text)
        outline["_provider"] = result.get("provider")
        outline["_cost"] = result.get("cost_usd", 0)
        log.info(f"  outline by {outline['_provider']}, {len(outline.get('outline', []))} H2s")
        return outline
    except json.JSONDecodeError as e:
        # Try regex extract the first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                outline = json.loads(m.group(0))
                outline["_provider"] = result.get("provider")
                outline["_cost"] = result.get("cost_usd", 0)
                log.info(f"  outline (regex-rescued) by {outline['_provider']}")
                return outline
            except json.JSONDecodeError:
                pass
        return {"error": f"outline JSON parse: {e}", "raw": text[:400]}


def stage_draft(outline: dict, content_type: str, words: int) -> dict:
    log.info(f"[stage 2] draft")
    prompt = DRAFT_PROMPT.format(
        content_type=content_type,
        outline_json=json.dumps(outline, indent=2),
        words=words,
    )
    result = call(
        messages=[{"role": "user", "content": prompt}],
        task="right", max_tokens=min(4000, words * 6),
    )
    if result.get("error"):
        return {"error": result["error"]}
    log.info(f"  draft by {result.get('provider')} ({len(result.get('text', ''))} chars)")
    return {
        "markdown": result.get("text", ""),
        "_provider": result.get("provider"),
        "_cost": result.get("cost_usd", 0),
    }


def stage_seo(draft_md: str, outline: dict) -> dict:
    log.info("[stage 3] SEO polish")
    prompt = SEO_POLISH_PROMPT.format(
        draft=draft_md[:15000],
        primary_keyword=outline.get("primary_keyword", "compliance"),
        internal_links=", ".join(outline.get("internal_links", [])),
    )
    result = call(
        messages=[{"role": "user", "content": prompt}],
        task="left", max_tokens=4000,
    )
    if result.get("error"):
        return {"error": result["error"]}
    log.info(f"  polished by {result.get('provider')}")
    return {
        "markdown": result.get("text", "").strip(),
        "_provider": result.get("provider"),
        "_cost": result.get("cost_usd", 0),
    }


async def stage_audit(topic: str, polished_md: str, outline: dict) -> dict:
    log.info("[stage 4] council audit")
    desc = f"""Generated {outline.get('_provider', 'auto')} content piece for meok.ai.

Topic: {topic}
Title: {outline.get('title', '?')}
Slug: {outline.get('slug', '?')}
Primary keyword: {outline.get('primary_keyword', '?')}
Word count target: declared in queue
CTA: {outline.get('cta', '?')}

CONTENT (truncated to 2000 chars for vote):

{polished_md[:2000]}

Council vote criteria:
- Factual accuracy (no fabricated quotes, fake stats, made-up clients)
- On-brand voice (direct, specific, no buzzwords)
- Clear CTA + correct internal links
- No legally-risky claims about being an authoritative source on a regulation
- SEO basics present (H1, H2 hierarchy, keyword placement, FAQ section)
"""
    return await audit_completed_work(
        title=f"Content piece: {outline.get('title', topic[:80])}",
        description=desc,
        action_type="content_piece",
        action_params={"topic": topic, "slug": outline.get("slug")},
    )


# ── Queue + output ──────────────────────────────────────────────────────────

def parse_queue(queue_path: Path) -> list[dict]:
    if not queue_path.exists():
        return []
    text = queue_path.read_text()
    blocks = re.split(r"^## ", text, flags=re.MULTILINE)
    items = []
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        topic = lines[0].strip()
        if topic.startswith("✅"):
            continue
        # parse `Type: blog`, `Words: 800`, `Keyword: ...` from the body
        meta = {"type": "blog", "words": 800, "keyword": None}
        for line in lines[1:]:
            line = line.strip()
            if line.lower().startswith("type:"):
                meta["type"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("words:"):
                try:
                    meta["words"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.lower().startswith("keyword:"):
                meta["keyword"] = line.split(":", 1)[1].strip()
        items.append({"topic": topic, **meta})
    return items


def mark_queue_done(queue_path: Path, topic: str):
    if not queue_path.exists():
        return
    text = queue_path.read_text()
    new = text.replace(f"## {topic}", f"## ✅ {topic}", 1)
    queue_path.write_text(new)


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def write_content(topic: str, content_type: str, outline: dict, polished_md: str, audit: dict, cost_breakdown: dict) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    slug = outline.get("slug") or slugify(topic)
    path = CONTENT_DIR / f"{today}_{content_type}_{slug}.md"

    front = f"""---
title: {outline.get('title', topic)}
slug: {slug}
description: {outline.get('meta_description', '')}
primary_keyword: {outline.get('primary_keyword', '')}
content_type: {content_type}
generated_at: {datetime.now().isoformat()}
council_vote: {audit.get('external_majority', '?')}
council_proposal_id: {audit.get('proposal_id', '?')}
generation_cost_usd: {cost_breakdown.get('total', 0):.6f}
status: awaiting_human_promotion
---

{polished_md}

---

_**Promotion checklist** (manual):_
- [ ] Fact-check the dated claims (regulations, fines, named entities)
- [ ] Verify the {len(outline.get('internal_links', []))} internal links resolve
- [ ] Promote to `meok/ui/src/app/blog/{slug}/page.tsx` or relevant route
- [ ] Add Open Graph image
- [ ] Submit URL to GSC after live

_Generation cost: {cost_breakdown}._
"""
    path.write_text(front)
    return path


def git_commit(path: Path, topic: str) -> bool:
    try:
        rel = path.relative_to(CLAWD)
        subprocess.run(["git", "add", str(rel)], cwd=str(CLAWD), check=True, capture_output=True, timeout=10)
        msg = f"content: {topic[:60]}\n\nAuto-generated by content engine.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
        subprocess.run(["git", "commit", "-m", msg], cwd=str(CLAWD), check=True, capture_output=True, timeout=15)
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"git commit failed: {e.stderr.decode() if e.stderr else e}")
        return False


# ── Top-level ───────────────────────────────────────────────────────────────

async def generate_content(topic: str, content_type: str = "blog", words: int = 800) -> dict:
    start = time.time()

    outline = stage_outline(topic, content_type, words)
    if outline.get("error"):
        return {"error": "outline failed", "detail": outline.get("error")}

    draft = stage_draft(outline, content_type, words)
    if draft.get("error"):
        return {"error": "draft failed", "detail": draft.get("error")}

    polished = stage_seo(draft.get("markdown", ""), outline)
    if polished.get("error"):
        # Fall back to unpolished draft if SEO stage failed
        log.warning(f"SEO stage failed: {polished.get('error')} - using unpolished draft")
        final_md = draft.get("markdown", "")
        seo_cost = 0
    else:
        final_md = polished.get("markdown", draft.get("markdown", ""))
        seo_cost = polished.get("_cost", 0)

    audit = await stage_audit(topic, final_md, outline)

    cost_breakdown = {
        "outline": outline.get("_cost", 0),
        "draft": draft.get("_cost", 0),
        "seo": seo_cost,
        "total": outline.get("_cost", 0) + draft.get("_cost", 0) + seo_cost,
    }

    path = write_content(topic, content_type, outline, final_md, audit, cost_breakdown)
    duration = int(time.time() - start)

    committed = False
    if audit.get("external_majority") == "approve":
        committed = git_commit(path, topic)
    else:
        with REJECTS_LOG.open("a") as fp:
            fp.write(f"[{datetime.now().isoformat()}] REJECTED: {topic}\n  path: {path}\n  reason: {audit.get('note', '?')}\n\n")

    log_entry = {
        "ts": datetime.now().isoformat(),
        "topic": topic,
        "type": content_type,
        "path": str(path),
        "council": audit.get("external_majority", "?"),
        "duration_s": duration,
        "cost_usd": cost_breakdown["total"],
    }
    with COMPLETED_LOG.open("a") as fp:
        fp.write(json.dumps(log_entry) + "\n")

    return {
        "topic": topic,
        "path": str(path),
        "council_majority": audit.get("external_majority"),
        "committed": committed,
        "duration_s": duration,
        "cost_breakdown": cost_breakdown,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Content engine: blog / case-study / landing page generator")
    p.add_argument("--topic", help="Single topic to generate")
    p.add_argument("--type", default="blog", help="Content type (blog/case-study/landing/comparison)")
    p.add_argument("--words", type=int, default=800)
    p.add_argument("--queue", default=str(QUEUE_FILE))
    p.add_argument("--pick-next", action="store_true")
    p.add_argument("--show-queue", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if args.show_queue:
        items = parse_queue(Path(args.queue))
        print(f"Queue has {len(items)} unprocessed items:")
        for i, it in enumerate(items, 1):
            print(f"  {i}. [{it['type']}, {it['words']}w] {it['topic']}")
        sys.exit(0)

    if args.pick_next:
        items = parse_queue(Path(args.queue))
        if not items:
            print("Queue empty.")
            sys.exit(0)
        it = items[0]
        result = asyncio.run(generate_content(it["topic"], it["type"], it["words"]))
        if result.get("council_majority") == "approve":
            mark_queue_done(Path(args.queue), it["topic"])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.topic:
        result = asyncio.run(generate_content(args.topic, args.type, args.words))
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print("Usage: --pick-next OR --topic '...' [--type blog] [--words 800] OR --show-queue")
    sys.exit(1)
