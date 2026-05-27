"""
Cold Email Drafter
==================
Reads a deep-research memo (or any target list) and drafts per-target cold
emails using the dual-brain stack:

  LEFT BRAIN  (Step 3.6) → drafts the structural / factual version
  RIGHT BRAIN (Claude or fallback) → drafts the empathetic / creative version
  COUNCIL     → audits both versions for: misleading claims, fabricated
                relationships, GDPR/CAN-SPAM compliance, on-brand voice

Output: per-target .eml files in revenue/outreach/<date>_<topic>/
        + INDEX.md with all drafts + audit notes for human review.

CRITICAL SAFETY: This script NEVER sends. Human review + manual send is
required (Nick has Smartlead / Apollo for actual dispatch).

Usage
-----
    # Draft from latest research memo:
    python cold_email_drafter.py --latest-memo

    # Draft from specific memo:
    python cold_email_drafter.py --memo revenue/research/2026-05-17_*.md

    # Draft from explicit target list (CSV: name,role,domain,context):
    python cold_email_drafter.py --targets revenue/CARE_HOME_COLD_LIST.csv
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

from llm_gateway import call, call_many  # noqa: E402
from external_council_voice import audit_completed_work  # noqa: E402

log = logging.getLogger("cold-email-drafter")

CLAWD = Path("/Users/nicholas/clawd")
RESEARCH_DIR = CLAWD / "revenue" / "research"
OUTREACH_DIR = CLAWD / "revenue" / "outreach"
OUTREACH_DIR.mkdir(parents=True, exist_ok=True)


# ── Target extraction from research memo ────────────────────────────────────

TARGET_EXTRACT_PROMPT = """Extract the target list from this research memo.

Return ONE JSON object with this exact shape (no prose, no markdown fences):
{
  "topic": "<2-5 word topic the memo is about>",
  "targets": [
    {
      "organisation": "<organisation name>",
      "role_title": "<job title to find / contact>",
      "email_domain": "<their email domain if mentioned, else null>",
      "pain_point": "<1 sentence on why they'd care>",
      "evidence_url": "<url citing the pain point if available, else null>"
    }
  ]
}

If the memo has no clear target list, return {"topic": "...", "targets": []}.
Cap at 8 targets. Be strict — only include orgs explicitly named in the memo.

MEMO:
{memo}
"""


def extract_targets_from_memo(memo_text: str) -> dict:
    """Use the left brain to extract structured targets from a free-form memo."""
    prompt = TARGET_EXTRACT_PROMPT.replace("{memo}", memo_text[:10000])
    result = call(
        messages=[{"role": "user", "content": prompt}],
        task="left",
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    if result.get("error"):
        log.error(f"target extraction failed: {result['error']}")
        return {"topic": "unknown", "targets": []}
    text = (result.get("text") or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        log.info(f"extracted {len(parsed.get('targets', []))} targets from memo")
        return parsed
    except json.JSONDecodeError as e:
        log.error(f"target JSON parse failed: {e}")
        return {"topic": "unknown", "targets": []}


# ── Email draft prompts ─────────────────────────────────────────────────────

LEFT_BRAIN_EMAIL_PROMPT = """You are writing a B2B cold email for MEOK AI Labs (https://meok.ai), a UK
Ltd that publishes 39 MIT-licensed compliance MCP servers for AI systems.

PRODUCT FACTS YOU CAN USE:
- 39 MCP servers (eu-ai-act-compliance, dora-compliance, nis2-compliance,
  cra-compliance, bias-detection, ai-bom, care-home-cqc, etc.)
- £29/month Starter (HMAC-signed attestations + email support + 14-day trial)
- £79/month Pro (priority support + 24h SLA + monthly regulatory brief)
- All MCPs are MIT licensed and free to self-host forever
- Run via Claude / Cursor / LangChain agents
- meok.ai/mcp/care-home-cqc is the page most relevant for care-home outreach
- Founded by Nicholas Templeman, UK Ltd CRN 16939677

RULES (CRITICAL — emails will be human-reviewed and any violation kills the campaign):
1. Never claim you have spoken to them, met them, or have prior relationship.
2. Never name-drop other clients ("we work with HC-One" etc.) — we don't yet.
3. Never fabricate quotes, testimonials, or case studies.
4. Always state the relevant compliance deadline / penalty as the wedge.
5. Always include an opt-out line at the bottom ("If this isn't relevant,
   just reply STOP and I'll remove you from the list.") — required for
   UK PECR / GDPR Article 14 compliance on cold B2B.
6. Subject line: max 6 words, lowercase, no emojis, no "RE:" tricks.
7. Body: 4 short paragraphs max, total 90-140 words.
8. CTA: ONE clear ask (call, demo, free trial install).

TARGET YOU'RE WRITING TO:
- Organisation: {organisation}
- Role: {role_title}
- Email domain: {email_domain}
- Pain point: {pain_point}
- Topic: {topic}

Write the LEFT-BRAIN version: structured, factual, deadline-driven.
Return a JSON object with this exact shape (no markdown):

{{"subject": "...", "body": "...", "cta": "..."}}
"""


RIGHT_BRAIN_EMAIL_PROMPT = """You are writing a B2B cold email for MEOK AI Labs (https://meok.ai).

PRODUCT FACTS:
- MEOK AI Labs publishes 39 MIT-licensed compliance MCP servers
- £29/month Starter or £79/month Pro
- All MCPs are MIT licensed and free to self-host forever
- Founded May 2026 by Nicholas Templeman, UK Ltd CRN 16939677

ZERO-TOLERANCE RULES (any violation makes the email unsendable):
1. NEVER write "we've worked with", "we've helped", "similar customers", "other care homes use" — we are NEW, zero customers yet
2. NEVER fabricate quotes, testimonials, or case studies
3. NEVER name-drop other organisations as customers or users
4. NEVER claim prior contact, conversation, or relationship
5. ALWAYS include "If this isn't relevant, just reply STOP and I'll remove you from the list."
6. Subject: max 6 words, lowercase, no emojis, no "RE:" tricks
7. Body: 4 short paragraphs max, 90-140 words total
8. ONE CTA only

Write the RIGHT-BRAIN version: empathetic, story-led, opens with their
specific situation. Lead with their pain point, NOT a product pitch.
Warm + curious tone — but NEVER claim experience we don't have.

TARGET:
- Organisation: {organisation}
- Role: {role_title}
- Email domain: {email_domain}
- Pain point: {pain_point}
- Topic: {topic}

Return ONE JSON object (no markdown fences, no preamble):

{{"subject": "...", "body": "...", "cta": "..."}}
"""


def draft_email_pair(target: dict, topic: str) -> dict:
    """Draft both left + right brain versions of the email."""
    fmt = {
        "organisation": target.get("organisation", "?"),
        "role_title": target.get("role_title", "?"),
        "email_domain": target.get("email_domain") or "?",
        "pain_point": target.get("pain_point") or "?",
        "topic": topic,
    }
    left_prompt = LEFT_BRAIN_EMAIL_PROMPT.format(**fmt)
    right_prompt = RIGHT_BRAIN_EMAIL_PROMPT.format(**fmt)

    left = call(
        messages=[{"role": "user", "content": left_prompt}],
        task="left", max_tokens=800,
        response_format={"type": "json_object"},
    )
    right = call(
        messages=[{"role": "user", "content": right_prompt}],
        task="right", max_tokens=800,
        response_format={"type": "json_object"},
    )

    def parse(r):
        if r.get("error"):
            return {"error": r["error"], "provider": r.get("provider", "?")}
        text = (r.get("text") or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            d = json.loads(text)
            d["provider"] = r.get("provider", "?")
            return d
        except json.JSONDecodeError:
            return {"error": "json parse fail", "raw": text[:400], "provider": r.get("provider", "?")}

    return {"left": parse(left), "right": parse(right)}


# ── Council audit ───────────────────────────────────────────────────────────

EMAIL_AUDIT_DESC_TMPL = """Two cold-email drafts for {organisation} ({role_title}).

LEFT BRAIN draft (provider: {left_provider}):
Subject: {left_subject}
Body:
{left_body}

RIGHT BRAIN draft (provider: {right_provider}):
Subject: {right_subject}
Body:
{right_body}

The council is asked to vote on whether both drafts are safe to send. Vote REJECT if EITHER draft contains any of these (zero-tolerance):
(a) "we've worked with", "we've helped", "similar customers", "other care homes use" — MEOK has zero customers, any such claim is FABRICATION
(b) Fake quotes, testimonials, or case studies
(c) Name-dropping any organisation as a customer/user
(d) Claiming prior contact, conversation, or relationship
(e) Missing the opt-out "reply STOP" line
(f) Overlong (>160 words) or spammy formatting
(g) Wrong target fit (e.g. care-home email to a fintech)
(h) Misleading product claims (e.g. claiming features we don't have)

Vote APPROVE only if BOTH drafts are clean. Vote ABSTAIN if you're unsure.
"""


async def audit_email_pair(target: dict, drafts: dict) -> dict:
    left = drafts.get("left", {})
    right = drafts.get("right", {})
    desc = EMAIL_AUDIT_DESC_TMPL.format(
        organisation=target.get("organisation", "?"),
        role_title=target.get("role_title", "?"),
        left_provider=left.get("provider", "?"),
        left_subject=left.get("subject", "?"),
        left_body=left.get("body", "?")[:1500],
        right_provider=right.get("provider", "?"),
        right_subject=right.get("subject", "?"),
        right_body=right.get("body", "?")[:1500],
    )
    return await audit_completed_work(
        title=f"Cold email drafts: {target.get('organisation', '?')} ({target.get('role_title', '?')})",
        description=desc,
        action_type="cold_email_draft",
        action_params={"organisation": target.get("organisation"), "domain": target.get("email_domain")},
    )


# ── Output writing ──────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def write_eml(out_dir: Path, target: dict, draft: dict, variant: str) -> Path:
    """Write a draft as an RFC 5322-style .eml file (paste-ready)."""
    org_slug = slugify(target.get("organisation", "unknown"))
    path = out_dir / f"{org_slug}__{variant}.eml"
    domain = (target.get("email_domain") or "example.com").lstrip("@").strip()
    subject = draft.get("subject", "(no subject)")
    body = draft.get("body", "(no body)")
    cta = draft.get("cta", "")
    provider = draft.get("provider", "?")

    full_body = body
    if cta and cta not in body:
        full_body = f"{body}\n\n{cta}"

    # Append the legally-required opt-out if missing
    if "STOP" not in full_body and "unsubscribe" not in full_body.lower():
        full_body += "\n\n— Nicholas Templeman, MEOK AI Labs (UK Ltd 16939677)\n  https://meok.ai · If this isn't relevant, reply STOP and I'll remove you."

    eml = f"""From: Nicholas Templeman <nicholas@meok.ai>
To: <REPLACE-WITH-VERIFIED-EMAIL>@{domain}
Subject: {subject}
X-MEOK-Variant: {variant}
X-MEOK-Provider: {provider}
X-MEOK-Target-Role: {target.get('role_title', '?')}

{full_body}
"""
    path.write_text(eml)
    return path


def write_index(out_dir: Path, topic: str, results: list[dict]):
    today = datetime.now().strftime("%Y-%m-%d")
    md = f"""# Cold email batch: {topic}

**Date:** {today}
**Drafts:** {len(results)} targets × 2 variants (left + right brain) = {2*len(results)} emails
**Status:** Awaiting human review

---

## How to use

1. Read each `.eml` file below
2. Pick the variant (left or right) that fits the target best
3. Replace `<REPLACE-WITH-VERIFIED-EMAIL>@<domain>` with an actual address you
   verified on LinkedIn or via the org's website
4. Paste into Smartlead / Apollo / Gmail
5. Send via your usual outreach tool (this script NEVER auto-sends)

## Targets + audit results

| # | Organisation | Role | Council vote | Notes |
|---|---|---|---|---|"""
    for i, r in enumerate(results, 1):
        t = r["target"]
        a = r["audit"]
        notes = a.get("note", "")[:80]
        md += f"\n| {i} | {t.get('organisation', '?')} | {t.get('role_title', '?')} | **{a.get('external_majority', '?')}** | {notes} |"

    md += "\n\n---\n\n## Files in this batch\n"
    for r in results:
        for variant in ("left", "right"):
            org_slug = slugify(r["target"].get("organisation", "?"))
            md += f"- [{org_slug}__{variant}.eml](./{org_slug}__{variant}.eml)\n"

    md += f"\n\n*Generated by `cold_email_drafter.py` at {datetime.now().isoformat()}.*\n"
    md += "*This script does NOT send. Human review + manual send required.*\n"
    (out_dir / "INDEX.md").write_text(md)


# ── Top-level pipeline ──────────────────────────────────────────────────────

async def draft_from_memo(memo_path: Path) -> dict:
    log.info(f"reading memo: {memo_path}")
    memo_text = memo_path.read_text()

    # 1. Extract targets
    extracted = extract_targets_from_memo(memo_text)
    topic = extracted.get("topic", "unknown")
    targets = extracted.get("targets", [])
    if not targets:
        log.warning("no targets extracted from memo")
        return {"error": "no targets", "memo": str(memo_path)}

    # 2. Set up output dir
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = OUTREACH_DIR / f"{today}_{slugify(topic)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"writing to: {out_dir}")

    # 3. Draft + audit each target
    results = []
    for target in targets:
        log.info(f"--- drafting for {target.get('organisation', '?')}")
        drafts = draft_email_pair(target, topic)
        audit = await audit_email_pair(target, drafts)

        # Always write both variants — even if audit rejects, human can see why
        for variant in ("left", "right"):
            draft = drafts.get(variant, {})
            if draft.get("error"):
                log.warning(f"  {variant} brain failed: {draft.get('error')}")
                continue
            write_eml(out_dir, target, draft, variant)
        results.append({"target": target, "drafts": drafts, "audit": audit})

    # 4. Write index
    write_index(out_dir, topic, results)

    return {
        "topic": topic,
        "memo": str(memo_path),
        "out_dir": str(out_dir),
        "targets": len(targets),
        "audits_approved": sum(1 for r in results if r["audit"].get("external_majority") == "approve"),
        "audits_rejected": sum(1 for r in results if r["audit"].get("external_majority") == "reject"),
    }


def latest_memo() -> Path | None:
    memos = sorted(RESEARCH_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return memos[0] if memos else None


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Cold email drafter (research memo → per-target drafts)")
    p.add_argument("--memo", help="Path to a specific research memo")
    p.add_argument("--latest-memo", action="store_true", help="Use the most recent memo in revenue/research/")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    memo_path: Path | None = None
    if args.memo:
        memo_path = Path(args.memo)
    elif args.latest_memo:
        memo_path = latest_memo()

    if not memo_path or not memo_path.exists():
        print("Error: provide --memo <path> or --latest-memo")
        sys.exit(1)

    result = asyncio.run(draft_from_memo(memo_path))
    print(json.dumps(result, indent=2))
