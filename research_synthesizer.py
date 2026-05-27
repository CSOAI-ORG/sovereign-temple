"""
Deep Research Synthesizer
=========================
Fires a research question at every available LLM voice in parallel,
aggregates the answers via the LEFT BRAIN (Step 3.6) into a single
synthesis memo, then submits the memo to the BFT council for audit.

If the council approves → memo gets written to revenue/research/<slug>.md
and committed (which fires the council audit hook AGAIN — recursive
quality check).

Pipeline:
  1. Read a research question from the queue
  2. Multi-voice research:
       all_active_voices in parallel via llm_gateway.call_many
       → list of perspectives
  3. Left-brain synthesis:
       Step 3.6 takes all perspectives + writes a unified memo
  4. Council audit:
       Submit memo as proposal, external voices vote
  5. If approved → write memo + git commit
     If rejected → log to rejects + flag for human review

Usage
-----
    python research_synthesizer.py --question "What is the cheapest way to..."
    python research_synthesizer.py --queue revenue/RESEARCH_QUEUE.md --pick-next
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

from llm_gateway import call, call_many, list_active, PROVIDERS  # noqa: E402
from external_council_voice import audit_completed_work  # noqa: E402

log = logging.getLogger("deep-research")

CLAWD = Path("/Users/nicholas/clawd")
RESEARCH_DIR = CLAWD / "revenue" / "research"
QUEUE_FILE = CLAWD / "revenue" / "RESEARCH_QUEUE.md"
REJECTS_LOG = Path("/tmp/research_rejects.log")
COMPLETED_LOG = Path("/tmp/research_completed.log")

RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


# ── Multi-voice research stage ──────────────────────────────────────────────

PERSPECTIVE_PROMPT = """You are one voice in a council researching a strategic question.

Your job: contribute YOUR best independent answer to the question below.
Do not hedge. Do not say "I don't know". Give your most confident answer
with concrete details. Other voices will give different angles — your value
is in being SPECIFIC and DIFFERENT.

QUESTION: {question}

Reply in this exact format (no preamble, no markdown headers):

ANSWER:
<your 200-400 word answer with concrete facts, numbers, names, urls if known>

KEY CITATIONS:
- <source 1 if you know it>
- <source 2 if you know it>

CONFIDENCE (0-1): <your confidence in the answer>

RISKS / GAPS:
- <what you might be wrong about, or what info is missing>
"""


SYNTHESIS_PROMPT = """You are the LEFT-BRAIN synthesizer. {voice_count} voices just answered the same question.
Your job: produce ONE unified strategic memo that:

1. **Headline finding** (2 sentences) — what's the answer?
2. **Specific actions** (3-5 bullets) — what should the user DO this week?
3. **Numbers / facts that agreed across voices** — high-confidence claims
4. **Contradictions** — where voices disagreed (flag the disagreement clearly)
5. **Open questions** — what couldn't be answered, what to research next

Target length: 400-700 words. Be ruthlessly specific. No filler. No "it depends".

QUESTION: {question}

VOICES (each separated by ===):

{voices_block}

Write the memo now. Markdown formatting is OK.
"""


async def gather_perspectives(question: str, timeout_s: int = 60) -> list[dict]:
    """Fire question at every active voice in parallel. Returns list of perspectives.

    Excludes the slow ollama-gemma4 voice (9GB model takes 60+s) to keep latency tight.
    For research we want fast diverse voices, not deep slow ones.
    """
    prompt = PERSPECTIVE_PROMPT.format(question=question)
    # Skip gemma4 (too slow for parallel research); use gemma3 + Vast + StepFun
    SKIP = {"ollama-gemma4"}
    active_names = [n for n, p in PROVIDERS.items() if p.is_active() and n not in SKIP]
    log.info(f"firing question at {len(active_names)} voices: {active_names}")
    if not active_names:
        return []
    # call_many is now robust to individual voice timeouts
    results = call_many(prompt, providers=active_names, timeout_s=timeout_s, max_tokens=800)
    # Filter out errored voices
    good = [r for r in results if r.get("text") and not r.get("error")]
    log.info(f"got {len(good)} usable perspectives (filtered from {len(results)})")
    return good


def synthesize(question: str, perspectives: list[dict]) -> str:
    """Left brain (Step 3.6) merges all perspectives into one memo."""
    if not perspectives:
        return "## NO VOICES AVAILABLE\n\nNo LLM perspectives could be gathered for this question."
    voices_block = "\n\n===\n\n".join(
        f"VOICE: {p['provider']} (model: {p['model']})\n\n{p['text']}"
        for p in perspectives
    )
    prompt = SYNTHESIS_PROMPT.format(
        voice_count=len(perspectives),
        question=question,
        voices_block=voices_block[:30000],  # cap to fit context
    )
    messages = [{"role": "user", "content": prompt}]
    result = call(messages, task="left", max_tokens=2000)
    if result.get("error"):
        log.warning(f"left-brain synthesis failed: {result['error']}, trying right-brain")
        result = call(messages, task="right", max_tokens=2000)
    return result.get("text", "## SYNTHESIS FAILED\n\nLeft and right brain both errored.")


# ── Queue management ────────────────────────────────────────────────────────

def parse_queue(queue_path: Path) -> list[dict]:
    """Read queue markdown. Format: ## Question text\n\nDetails (optional)\n\n## Next question..."""
    if not queue_path.exists():
        return []
    text = queue_path.read_text()
    # Split on `## ` headings
    blocks = re.split(r"^## ", text, flags=re.MULTILINE)
    items = []
    for block in blocks[1:]:  # skip preamble before first ##
        lines = block.strip().split("\n", 1)
        question = lines[0].strip()
        details = lines[1].strip() if len(lines) > 1 else ""
        # Skip completed items (have ✅ marker)
        if question.startswith("[✅]") or question.startswith("✅"):
            continue
        items.append({"question": question, "details": details})
    return items


def mark_queue_done(queue_path: Path, question: str):
    """Prepend ✅ to the question line so it's skipped next time."""
    if not queue_path.exists():
        return
    text = queue_path.read_text()
    # Find line `## <question>` and replace
    new = text.replace(f"## {question}", f"## ✅ {question}", 1)
    queue_path.write_text(new)


# ── Memo writing + git commit ───────────────────────────────────────────────

def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return s.strip("-")[:60]


def write_memo(question: str, synthesis: str, perspectives: list[dict], audit_result: dict) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(question)
    path = RESEARCH_DIR / f"{today}_{slug}.md"

    voices_summary = "\n".join(
        f"- **{p['provider']}** ({p['model']}, {p['ms']}ms, ${p['cost_usd']:.5f}): {p['text'][:200].strip()}..."
        for p in perspectives
    )

    council_summary = (
        f"- Voices polled: {audit_result.get('voices_polled', 0)}\n"
        f"- Approve: {audit_result.get('approve_count', 0)} | "
        f"Reject: {audit_result.get('reject_count', 0)} | "
        f"Abstain: {audit_result.get('abstain_count', 0)}\n"
        f"- External majority: **{audit_result.get('external_majority', '?')}**\n"
        f"- Proposal ID: `{audit_result.get('proposal_id', '?')}`"
    )

    memo = f"""# {question}

**Date:** {today}
**Generated by:** Deep Research Agent (multi-voice LLM synthesis + BFT council audit)
**Status:** Council {audit_result.get('external_majority', '?').upper()}

---

## Synthesis (left-brain merge of all voices)

{synthesis}

---

## Source voices (raw)

{voices_summary}

---

## Council audit

{council_summary}

---

*Generated automatically by `research_synthesizer.py` at {datetime.now().isoformat()}.*
*If this memo is wrong, append corrections at the bottom + commit (which re-audits).*
"""
    path.write_text(memo)
    return path


def git_commit_memo(memo_path: Path, question: str) -> bool:
    """Stage and commit the memo file. Returns True on success."""
    try:
        # Run all git ops from the clawd workspace
        subprocess.run(["git", "add", str(memo_path.relative_to(CLAWD))],
                       cwd=str(CLAWD), check=True, capture_output=True, timeout=10)
        msg = f"research: {question[:60]}\n\nAuto-generated by deep-research shift.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
        subprocess.run(["git", "commit", "-m", msg],
                       cwd=str(CLAWD), check=True, capture_output=True, timeout=15)
        log.info(f"committed memo: {memo_path}")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"git commit failed: {e.stderr.decode() if e.stderr else e}")
        return False
    except Exception as e:
        log.error(f"git commit error: {e}")
        return False


# ── Top-level pipeline ──────────────────────────────────────────────────────

async def run_research(question: str, details: str = "") -> dict:
    """End-to-end: research → synthesize → audit → memo → commit."""
    start = time.time()
    full_question = f"{question}\n\nContext: {details}" if details else question

    log.info(f"=== research: {question}")
    perspectives = await gather_perspectives(full_question)
    log.info(f"gathered {len(perspectives)} perspectives")

    synthesis = synthesize(full_question, perspectives)
    log.info(f"synthesized memo ({len(synthesis)} chars)")

    # Council audits the synthesis quality
    audit_result = await audit_completed_work(
        title=f"Deep research memo: {question[:80]}",
        description=f"Generated synthesis from {len(perspectives)} voices.\n\nMemo preview:\n{synthesis[:1500]}",
        action_type="deep_research_memo",
        action_params={"voices": len(perspectives), "question": question},
    )
    log.info(f"council vote: {audit_result.get('external_majority', '?')}")

    # Always write the memo (even if rejected — humans can review)
    memo_path = write_memo(question, synthesis, perspectives, audit_result)

    duration = int(time.time() - start)
    log_entry = {
        "ts": datetime.now().isoformat(),
        "question": question,
        "voices": len(perspectives),
        "memo": str(memo_path),
        "council": audit_result.get("external_majority", "?"),
        "duration_s": duration,
    }
    with COMPLETED_LOG.open("a") as fp:
        fp.write(json.dumps(log_entry) + "\n")

    # Commit ONLY if council approved (avoid spamming git with rejected memos)
    committed = False
    if audit_result.get("external_majority") == "approve":
        committed = git_commit_memo(memo_path, question)
    else:
        with REJECTS_LOG.open("a") as fp:
            fp.write(f"[{datetime.now().isoformat()}] REJECTED: {question}\n  memo: {memo_path}\n  reason: {audit_result}\n\n")

    return {
        "question": question,
        "memo_path": str(memo_path),
        "voices": len(perspectives),
        "council_majority": audit_result.get("external_majority"),
        "committed": committed,
        "duration_s": duration,
    }


def pick_next_question(queue_path: Path) -> dict | None:
    items = parse_queue(queue_path)
    return items[0] if items else None


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Deep research synthesizer")
    p.add_argument("--question", help="Direct question to research")
    p.add_argument("--queue", default=str(QUEUE_FILE), help="Path to research queue markdown")
    p.add_argument("--pick-next", action="store_true", help="Pick next unanswered question from queue")
    p.add_argument("--show-queue", action="store_true", help="Print queue contents + exit")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if args.show_queue:
        items = parse_queue(Path(args.queue))
        print(f"Queue has {len(items)} unanswered questions:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item['question']}")
        sys.exit(0)

    if args.pick_next:
        item = pick_next_question(Path(args.queue))
        if not item:
            print("Queue is empty. Add questions to revenue/RESEARCH_QUEUE.md")
            sys.exit(0)
        result = asyncio.run(run_research(item["question"], item.get("details", "")))
        if result["council_majority"] == "approve":
            mark_queue_done(Path(args.queue), item["question"])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.question:
        result = asyncio.run(run_research(args.question))
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print("Usage: --question '...' OR --pick-next OR --show-queue")
    sys.exit(1)
