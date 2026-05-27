"""
External Council Voice — wires external LLMs (Ollama, StepFun, Anthropic, Haiku)
as voting agents alongside SOV3's native 33-node BFT council.

Each external LLM is registered as an agent via SOV3's register_agent MCP tool,
then casts votes on proposals via vote_on_proposal. The native 33-node council
already runs Byzantine quorum (2f+1) — external voices simply add diversity.

Total council size with all 4 external voices wired: 37 nodes.
BFT quorum needed: 2f+1 = 25 votes (tolerates up to 12 faulty/malicious votes).

Usage
-----
    from external_council_voice import audit_completed_work

    decision = await audit_completed_work(
        title="Shipped care-home-cqc-mcp + Stripe £29 + landing page",
        description="<full diff / actions / verification>",
        action_type="ship_mcp",
        action_params={"slug": "care-home-cqc"},
    )
    # decision = {"approved": True, "votes": [...], "quorum_met": True}
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib import request as urllib_request

log = logging.getLogger("external-council")

SOV3_MCP = os.environ.get("SOV3_MCP_URL", "http://localhost:3101/mcp")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

# Optional external LLM keys — if unset, that voice is skipped (graceful degrade)
STEPFUN_API_KEY = os.environ.get("STEPFUN_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ───────────────────────────────────────────────────────────────────────────
# Voice configuration — each external LLM that can join the council
# ───────────────────────────────────────────────────────────────────────────

@dataclass
class CouncilVoice:
    agent_id: str           # registered ID in SOV3 council
    display_name: str       # what shows in council UI / logs
    model: str              # exact model string for the API
    endpoint: str           # full API URL
    auth_header: dict       # headers including Authorization
    body_template: str      # 'openai' (chat/completions style) | 'ollama' | 'anthropic'
    timeout_s: int = 30
    enabled: bool = True


VOICES: list[CouncilVoice] = [
    # Local free voice — gemma3:1b for fast turn-around (~3-5s); upgrade to gemma4 if needed
    CouncilVoice(
        agent_id="ext-ollama-gemma3",
        display_name="Ollama gemma3:1b (local, free, fast)",
        model="gemma3:1b",
        endpoint=OLLAMA_URL,
        auth_header={},
        body_template="ollama",
        timeout_s=60,
        enabled=True,
    ),
    # Local secondary voice — gemma4:e4b for deeper review (9GB, ~30-60s)
    CouncilVoice(
        agent_id="ext-ollama-gemma4",
        display_name="Ollama gemma4:e4b (local, free, deep)",
        model="gemma4:e4b",
        endpoint=OLLAMA_URL,
        auth_header={},
        body_template="ollama",
        timeout_s=120,
        enabled=False,   # disabled by default — enable for deep audits
    ),
    # StepFun Step 3.6 — non-reasoning fast voice (LEFT BRAIN primary per Nick)
    # NOTE: correct domain is api.stepfun.ai (not .com) — docs are misleading
    CouncilVoice(
        agent_id="ext-stepfun-3.6",
        display_name="Step 3.6 (LEFT BRAIN, fast, structured)",
        model="step-3.6",
        endpoint="https://api.stepfun.ai/v1/chat/completions",
        auth_header={"Authorization": f"Bearer {STEPFUN_API_KEY}"} if STEPFUN_API_KEY else {},
        body_template="openai",
        timeout_s=30,
        enabled=bool(STEPFUN_API_KEY),
    ),
    # StepFun Step 3.5 Flash — reasoning model for deep audit votes
    CouncilVoice(
        agent_id="ext-stepfun-flash",
        display_name="Step 3.5 Flash (reasoning, deep audit)",
        model="step-3.5-flash",
        endpoint="https://api.stepfun.ai/v1/chat/completions",
        auth_header={"Authorization": f"Bearer {STEPFUN_API_KEY}"} if STEPFUN_API_KEY else {},
        body_template="openai",
        timeout_s=60,
        enabled=False,  # disabled by default — reasoning model is slow; enable for deep audits
    ),
    # Anthropic voices — DISABLED until billing credit added at console.anthropic.com
    # Set ANTHROPIC_BILLING_OK=1 env var to re-enable once credits topped up.
    CouncilVoice(
        agent_id="ext-anthropic-haiku",
        display_name="Anthropic Haiku (fast, cheap)",
        model="claude-haiku-4-5",
        endpoint="https://api.anthropic.com/v1/messages",
        auth_header={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        } if ANTHROPIC_API_KEY else {},
        body_template="anthropic",
        enabled=bool(ANTHROPIC_API_KEY) and bool(os.environ.get("ANTHROPIC_BILLING_OK")),
    ),
    CouncilVoice(
        agent_id="ext-anthropic-opus",
        display_name="Anthropic Opus (premium deep)",
        model="claude-opus-4-7",
        endpoint="https://api.anthropic.com/v1/messages",
        auth_header={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        } if ANTHROPIC_API_KEY else {},
        body_template="anthropic",
        enabled=bool(ANTHROPIC_API_KEY) and bool(os.environ.get("ANTHROPIC_BILLING_OK")),
    ),
]


# ───────────────────────────────────────────────────────────────────────────
# SOV3 MCP client — calls submit_council_proposal / vote_on_proposal
# ───────────────────────────────────────────────────────────────────────────

def _mcp_call(tool: str, args: dict) -> dict:
    """Call a SOV3 MCP tool via JSON-RPC 2.0 over HTTP."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
        "id": 1,
    }).encode("utf-8")
    req = urllib_request.Request(
        SOV3_MCP,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        # MCP wraps results: {"result": {"content": [{"type": "text", "text": "<json>"}]}}
        result = data.get("result", {})
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except Exception:
                return {"raw_text": content[0]["text"]}
        return result
    except Exception as e:
        log.error(f"SOV3 MCP {tool} error: {e}")
        return {"error": str(e)}


def register_external_voice(voice: CouncilVoice) -> str:
    """Register an external LLM as a council agent in SOV3."""
    result = _mcp_call("register_agent", {
        "agent_id": voice.agent_id,
        "name": voice.display_name,
        "specialty": "external_llm_voice",
        "model": voice.model,
    })
    log.info(f"registered {voice.agent_id}: {result}")
    return voice.agent_id


def submit_proposal(title: str, description: str, action_type: str, action_params: dict) -> Optional[str]:
    """Submit a proposal to the 33-node BFT council."""
    result = _mcp_call("submit_council_proposal", {
        "title": title,
        "description": description,
        "proposed_by": "claude-opus-1m",
        "action_type": action_type,
        "action_params": action_params,
    })
    proposal_id = result.get("proposal_id")
    log.info(f"submitted proposal {proposal_id}: {title}")
    return proposal_id


def cast_vote_in_council(proposal_id: str, voice: CouncilVoice, vote: str, reasoning: str) -> dict:
    """Cast an external LLM's vote into the SOV3 council."""
    return _mcp_call("vote_on_proposal", {
        "proposal_id": proposal_id,
        "agent_id": voice.agent_id,
        "vote": vote,
        "reasoning": reasoning,
    })


# ───────────────────────────────────────────────────────────────────────────
# LLM voting — ask each external voice to vote on a proposal
# ───────────────────────────────────────────────────────────────────────────

VOTE_PROMPT = """You are a Byzantine fault-tolerant council voter reviewing a proposed action.

PROPOSAL TITLE: {title}

PROPOSAL DESCRIPTION:
{description}

ACTION TYPE: {action_type}

Evaluate against:
1. Is the work correctly described? (no overclaims, fabrication, or hidden assumptions)
2. Is it safe? (no irreversible harm, sensible blast radius)
3. Does it advance the user's stated goal? (revenue, safety, code quality, etc.)
4. Are there obvious issues a reasonable reviewer would flag?

Respond with a JSON object ONLY, no prose:
{{"vote": "approve" | "reject" | "abstain", "reasoning": "<2 sentences>", "confidence": 0.0-1.0}}
"""


def _ask_voice(voice: CouncilVoice, prompt: str) -> dict:
    """Send a prompt to an LLM voice and parse its JSON vote."""
    if voice.body_template == "ollama":
        body = json.dumps({
            "model": voice.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2, "num_predict": 200},
        }).encode("utf-8")
    elif voice.body_template == "openai":
        body = json.dumps({
            "model": voice.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1500,   # high to handle StepFun reasoning + content
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
    elif voice.body_template == "anthropic":
        body = json.dumps({
            "model": voice.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
        }).encode("utf-8")
    else:
        return {"vote": "abstain", "reasoning": "unknown body template", "confidence": 0.0}

    headers = {"Content-Type": "application/json", **voice.auth_header}
    req = urllib_request.Request(voice.endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib_request.urlopen(req, timeout=voice.timeout_s) as r:
            response = json.loads(r.read())
        # Extract the assistant text
        if voice.body_template == "ollama":
            text = response.get("message", {}).get("content", "")
        elif voice.body_template == "openai":
            text = response["choices"][0]["message"]["content"]
        elif voice.body_template == "anthropic":
            text = response["content"][0]["text"]
        else:
            text = ""
        if not text:
            # Reasoning model returned no content (truncated in reasoning) — try reasoning field
            if voice.body_template == "openai":
                msg = response.get("choices", [{}])[0].get("message", {})
                text = msg.get("reasoning") or ""
        if not text:
            log.error(f"{voice.agent_id} empty content + no reasoning fallback")
            return {"vote": "abstain", "reasoning": "voice returned empty", "confidence": 0.0}
        # Some models wrap JSON in markdown fences ```json ... ```
        text = text.strip()
        if text.startswith("```"):
            # strip code fence
            text = text.split("```", 2)[1] if "```" in text[3:] else text
            text = text.lstrip("json").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract first {...} block
            import re
            m = re.search(r"\{[^{}]*\"vote\"[^{}]*\}", text, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
            else:
                raise
        return {
            "vote": parsed.get("vote", "abstain"),
            "reasoning": parsed.get("reasoning", "")[:500],
            "confidence": float(parsed.get("confidence", 0.5)),
        }
    except Exception as e:
        # Log with truncated raw response for debug
        raw_preview = (str(text)[:200] if 'text' in dir() else "<no text>")
        log.error(f"{voice.agent_id} error: {e} | raw_text_preview: {raw_preview!r}")
        return {"vote": "abstain", "reasoning": f"voice error: {e}"[:500], "confidence": 0.0}


# ───────────────────────────────────────────────────────────────────────────
# Top-level audit API
# ───────────────────────────────────────────────────────────────────────────

async def audit_completed_work(
    title: str,
    description: str,
    action_type: str = "generic",
    action_params: Optional[dict] = None,
) -> dict:
    """
    Submit a completed-work claim to the BFT council and gather external votes.

    Returns:
        {
            "proposal_id": str,
            "voices_polled": int,
            "votes": [{voice, vote, reasoning, confidence}, ...],
            "approve_count": int,
            "reject_count": int,
            "abstain_count": int,
            "external_majority": "approve" | "reject" | "abstain",
            "note": str,  # status hint
        }
    """
    action_params = action_params or {}
    proposal_id = submit_proposal(title, description, action_type, action_params)
    if not proposal_id:
        return {"error": "could not submit proposal to SOV3", "approved": False}

    prompt = VOTE_PROMPT.format(title=title, description=description, action_type=action_type)
    active_voices = [v for v in VOICES if v.enabled]

    votes = []
    for voice in active_voices:
        v = _ask_voice(voice, prompt)
        v["voice"] = voice.agent_id
        v["display_name"] = voice.display_name
        votes.append(v)
        # Persist into SOV3 council
        register_external_voice(voice)
        cast_vote_in_council(proposal_id, voice, v["vote"], v["reasoning"])

    approve = sum(1 for v in votes if v["vote"] == "approve")
    reject = sum(1 for v in votes if v["vote"] == "reject")
    abstain = sum(1 for v in votes if v["vote"] == "abstain")

    if approve > reject and approve >= abstain:
        majority = "approve"
    elif reject > approve:
        majority = "reject"
    else:
        majority = "abstain"

    return {
        "proposal_id": proposal_id,
        "voices_polled": len(active_voices),
        "votes": votes,
        "approve_count": approve,
        "reject_count": reject,
        "abstain_count": abstain,
        "external_majority": majority,
        "note": (
            f"{approve}/{len(active_voices)} external voices approved. "
            "Native 33-node BFT council also reviewing — check SOV3 dashboard for quorum status."
        ),
    }


# ───────────────────────────────────────────────────────────────────────────
# CLI for ad-hoc audit calls (used by Claude after completed work)
# ───────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, sys
    p = argparse.ArgumentParser(description="Audit completed work via external council voices")
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--action-type", default="generic")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    result = asyncio.run(audit_completed_work(args.title, args.description, args.action_type))
    print(json.dumps(result, indent=2))
