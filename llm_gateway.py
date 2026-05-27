"""
LLM Gateway — the left brain / right brain router for MEOK AI Labs

ONE entry-point that fronts every LLM provider you have access to.
Routes each call to the cheapest/best provider for the task TYPE.

TASK ROUTING TABLE
==================

| task_hint           | routes to                              | why                          |
|---------------------|----------------------------------------|------------------------------|
| "fast" / "cheap"    | Ollama gemma3:1b (local, free)         | <1s, no cost                 |
| "audit" / "vote"    | gemma3:1b + Step 3.5 + Haiku (parallel)| BFT diversity, cheap         |
| "tool" / "code"     | Step 3.5 Flash → Claude Sonnet fallback| fast tool-use, premium fallback |
| "deep" / "review"   | Claude Opus 4.7                        | best long-context reasoning  |
| "research"          | Claude Opus + Step 3.5 in parallel     | aggregate                    |
| "bulk"              | Step 3.5 Flash → DeepSeek → Gemini Flash | cheapest per-token         |
| "chinese"           | Step 3.5 Flash + Qwen                  | native CN                    |
| "draft"             | Ollama gemma4:e4b (local)              | private, free, decent quality|

PROVIDERS (graceful-degrade if key unset)
===========================================
- ollama: localhost:11434 — gemma3:1b (free, fast), gemma4:e4b (free, deep)
- stepfun: api.stepfun.com — step-3.5-flash (cheap, fast, tool-use)
- anthropic: api.anthropic.com — haiku (cheap), sonnet (balanced), opus (premium)
- openai: api.openai.com — (only if key set)
- deepseek: api.deepseek.com — DeepSeek V3 (cheapest premium)
- mistral: api.mistral.ai — Large 2 (EU-resident vote)
- google: generativelanguage.googleapis.com — Gemini 2.5 Flash (cheapest)
- xai: api.x.ai — Grok 4 fast

USAGE
=====
    from llm_gateway import call, call_many

    # Single call
    text = call(messages=[{"role":"user","content":"..."}], task="cheap")

    # Parallel multi-provider call (for BFT council voting)
    votes = call_many(prompt="...", providers=["ollama-gemma3", "stepfun-flash", "claude-haiku"])

Token accounting per provider per day → /tmp/llm_gateway_cost.json
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib import request as urllib_request

log = logging.getLogger("llm-gateway")

# ── Configuration ────────────────────────────────────────────────────────────

COST_LOG = Path("/tmp/llm_gateway_cost.json")
DEFAULT_TIMEOUT = 60

# ── Provider catalogue ──────────────────────────────────────────────────────

@dataclass
class Provider:
    name: str                       # routing key e.g. "stepfun-flash"
    model: str                      # exact API model string
    endpoint: str                   # full URL
    transport: str                  # "openai" | "ollama" | "anthropic"
    auth_header: dict = field(default_factory=dict)
    cost_in_per_1m: float = 0.0     # USD per 1M input tokens
    cost_out_per_1m: float = 0.0    # USD per 1M output tokens
    context_window: int = 8192
    enabled: bool = True
    rps_limit: float = 10.0          # soft rate limit

    def is_active(self) -> bool:
        return self.enabled and (
            "Authorization" in self.auth_header
            or "x-api-key" in self.auth_header
            or self.transport == "ollama"  # local, no auth needed
        )


def _h_anthropic() -> dict:
    k = os.environ.get("ANTHROPIC_API_KEY", "")
    return {"x-api-key": k, "anthropic-version": "2023-06-01"} if k else {}

def _h_bearer(env_name: str) -> dict:
    k = os.environ.get(env_name, "")
    return {"Authorization": f"Bearer {k}"} if k else {}

def _h_google() -> dict:
    return {}  # Google uses ?key= query param, handled in transport

PROVIDERS: dict[str, Provider] = {
    # Local — always free, no key
    "ollama-gemma3": Provider(
        name="ollama-gemma3", model="gemma3:1b",
        endpoint="http://localhost:11434/api/chat",
        transport="ollama", cost_in_per_1m=0.0, cost_out_per_1m=0.0,
        context_window=8192,
    ),
    "ollama-gemma4": Provider(
        name="ollama-gemma4", model="gemma4:e4b",
        endpoint="http://localhost:11434/api/chat",
        transport="ollama", cost_in_per_1m=0.0, cost_out_per_1m=0.0,
        context_window=8192,
    ),
    # Vast.ai GPU (RTX 4070S 12GB) via persistent SSH tunnel on :11436 — zero-cost cloud voices
    "vast-llama3-8b": Provider(
        name="vast-llama3-8b", model="llama3.1:8b",
        endpoint="http://localhost:11436/api/chat",
        transport="ollama", cost_in_per_1m=0.0, cost_out_per_1m=0.0,
        context_window=128000,
    ),
    "vast-llama3-3b": Provider(
        name="vast-llama3-3b", model="llama3.2:3b",
        endpoint="http://localhost:11436/api/chat",
        transport="ollama", cost_in_per_1m=0.0, cost_out_per_1m=0.0,
        context_window=128000,
    ),
    # Anthropic — Claude family
    "claude-haiku": Provider(
        name="claude-haiku", model="claude-haiku-4-5",
        endpoint="https://api.anthropic.com/v1/messages",
        transport="anthropic", auth_header=_h_anthropic(),
        cost_in_per_1m=1.0, cost_out_per_1m=5.0, context_window=200000,
    ),
    "claude-sonnet": Provider(
        name="claude-sonnet", model="claude-sonnet-4-7",
        endpoint="https://api.anthropic.com/v1/messages",
        transport="anthropic", auth_header=_h_anthropic(),
        cost_in_per_1m=3.0, cost_out_per_1m=15.0, context_window=1000000,
    ),
    "claude-opus": Provider(
        name="claude-opus", model="claude-opus-4-7",
        endpoint="https://api.anthropic.com/v1/messages",
        transport="anthropic", auth_header=_h_anthropic(),
        cost_in_per_1m=15.0, cost_out_per_1m=75.0, context_window=1000000,
    ),
    # StepFun — Chinese MoE, very fast tool-use. NOTE: correct domain is .ai not .com
    # step-3.5-flash is a REASONING model (chain-of-thought in `reasoning` field) — needs high max_tokens
    "stepfun-flash": Provider(
        name="stepfun-flash", model="step-3.5-flash",
        endpoint="https://api.stepfun.ai/v1/chat/completions",
        transport="openai", auth_header=_h_bearer("STEPFUN_API_KEY"),
        cost_in_per_1m=0.10, cost_out_per_1m=0.40,
        context_window=262144,
    ),
    # StepFun 3.6 — newer, non-reasoning, default-friendly. LEFT BRAIN primary per Nick.
    "stepfun-3.6": Provider(
        name="stepfun-3.6", model="step-3.6",
        endpoint="https://api.stepfun.ai/v1/chat/completions",
        transport="openai", auth_header=_h_bearer("STEPFUN_API_KEY"),
        cost_in_per_1m=0.10, cost_out_per_1m=0.40,
        context_window=262144,
    ),
    # MiniMax — backup left-brain per Nick's architecture
    "minimax-m2": Provider(
        name="minimax-m2", model="MiniMax-M2",
        endpoint="https://api.minimax.io/v1/text/chatcompletion_v2",
        transport="openai", auth_header=_h_bearer("MINIMAX_API_KEY"),
        cost_in_per_1m=0.40, cost_out_per_1m=2.20,
        context_window=1_000_000,
    ),
    # DeepSeek — cheap deep reasoning
    "deepseek-v3": Provider(
        name="deepseek-v3", model="deepseek-chat",
        endpoint="https://api.deepseek.com/v1/chat/completions",
        transport="openai", auth_header=_h_bearer("DEEPSEEK_API_KEY"),
        cost_in_per_1m=0.27, cost_out_per_1m=1.10,
        context_window=64000,
    ),
    # Mistral — EU-resident vote
    "mistral-large": Provider(
        name="mistral-large", model="mistral-large-latest",
        endpoint="https://api.mistral.ai/v1/chat/completions",
        transport="openai", auth_header=_h_bearer("MISTRAL_API_KEY"),
        cost_in_per_1m=2.0, cost_out_per_1m=6.0,
        context_window=128000,
    ),
    # Google Gemini — cheapest at scale
    "gemini-flash": Provider(
        name="gemini-flash", model="gemini-2.5-flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        transport="google", auth_header={},  # uses ?key= query
        cost_in_per_1m=0.075, cost_out_per_1m=0.30,
        context_window=1000000,
        enabled=bool(os.environ.get("GOOGLE_API_KEY")),
    ),
    # xAI Grok — diverse perspective
    "grok-fast": Provider(
        name="grok-fast", model="grok-4-fast",
        endpoint="https://api.x.ai/v1/chat/completions",
        transport="openai", auth_header=_h_bearer("XAI_API_KEY"),
        cost_in_per_1m=0.30, cost_out_per_1m=1.50,
        context_window=128000,
    ),
}

# ── Task → provider routing table ────────────────────────────────────────────

# Each task hint maps to an ordered preference list (first = primary, rest = fallback)
TASK_ROUTES: dict[str, list[str]] = {
    # ─── Nick's dual-brain architecture ─────────────────────────────────────
    # LEFT BRAIN  (analytical, fast, structured): Step 3.6 → Step 3.5 Flash → MiniMax M2 backup
    # RIGHT BRAIN (creative, intuitive, complex): Claude Opus → Claude Sonnet → DeepSeek V3 backup
    "left":     ["stepfun-3.6", "stepfun-flash", "minimax-m2", "vast-llama3-8b"],
    "right":    ["claude-opus", "claude-sonnet", "deepseek-v3", "vast-llama3-8b", "stepfun-3.6", "ollama-gemma4"],
    "brain":    ["stepfun-3.6", "claude-opus"],  # dispatch both hemispheres in parallel via call_many
    # ─── Task-specific routes ───────────────────────────────────────────────
    "cheap":    ["ollama-gemma3", "vast-llama3-3b", "stepfun-3.6", "gemini-flash"],
    "fast":     ["stepfun-3.6", "ollama-gemma3", "vast-llama3-3b", "gemini-flash"],
    "tool":     ["stepfun-3.6", "stepfun-flash", "vast-llama3-8b", "claude-sonnet"],
    "code":     ["claude-sonnet", "deepseek-v3", "stepfun-3.6", "vast-llama3-8b"],
    "deep":     ["claude-opus", "stepfun-flash", "deepseek-v3", "ollama-gemma4"],  # stepfun-flash IS deep (reasoning)
    "audit":    ["ollama-gemma3", "vast-llama3-8b", "stepfun-3.6", "claude-haiku"],
    "vote":     ["ollama-gemma3", "vast-llama3-8b", "stepfun-3.6", "claude-haiku"],
    "draft":    ["stepfun-3.6", "ollama-gemma4", "vast-llama3-8b", "deepseek-v3"],
    "bulk":     ["stepfun-3.6", "vast-llama3-8b", "gemini-flash", "deepseek-v3"],
    "research": ["claude-opus", "stepfun-flash", "deepseek-v3"],
    "chinese":  ["stepfun-3.6", "stepfun-flash", "minimax-m2", "deepseek-v3"],
    # ─── Default ────────────────────────────────────────────────────────────
    "default":  ["stepfun-3.6", "ollama-gemma3", "claude-haiku", "vast-llama3-8b"],
}


def pick_provider(task: str = "default", explicit: Optional[str] = None) -> Optional[Provider]:
    """Return the first ACTIVE provider for the given task hint."""
    if explicit and explicit in PROVIDERS and PROVIDERS[explicit].is_active():
        return PROVIDERS[explicit]
    route = TASK_ROUTES.get(task, TASK_ROUTES["default"])
    for name in route:
        p = PROVIDERS.get(name)
        if p and p.is_active():
            return p
    return None


# ── Transport adapters ──────────────────────────────────────────────────────

def _build_request(provider: Provider, messages: list[dict], **kwargs) -> tuple[bytes, str, dict]:
    """Returns (body, url, headers) for the actual HTTP call."""
    headers = {"Content-Type": "application/json", **provider.auth_header}
    url = provider.endpoint
    max_tokens = kwargs.get("max_tokens", 1024)
    temperature = kwargs.get("temperature", 0.4)

    if provider.transport == "ollama":
        payload = {
            "model": provider.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        # Translate OpenAI-style response_format → Ollama's `format` field
        rf = kwargs.get("response_format")
        if isinstance(rf, dict) and rf.get("type") == "json_object":
            payload["format"] = "json"
        elif kwargs.get("response_format_ollama"):
            payload["format"] = kwargs["response_format_ollama"]
        body = json.dumps(payload).encode("utf-8")
    elif provider.transport == "openai":
        payload = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if kwargs.get("response_format"):
            payload["response_format"] = kwargs["response_format"]
        body = json.dumps(payload).encode("utf-8")
    elif provider.transport == "anthropic":
        body = json.dumps({
            "model": provider.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")
    elif provider.transport == "google":
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        url = f"{provider.endpoint}?key={api_key}"
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": m["content"]} for m in messages if m["role"] == "user"]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }).encode("utf-8")
    else:
        raise ValueError(f"unknown transport: {provider.transport}")

    return body, url, headers


def _extract_text(provider: Provider, response: dict) -> str:
    """Extract assistant text from each provider's response shape.
    For reasoning models (DeepSeek R1, StepFun 3.5-flash, OpenAI o1/o3),
    content may be empty when reasoning was truncated — fall back to reasoning field."""
    if provider.transport == "ollama":
        return response.get("message", {}).get("content", "")
    if provider.transport == "openai":
        msg = response["choices"][0]["message"]
        # Prefer content; fall back to reasoning if content is empty (truncated CoT)
        return msg.get("content") or msg.get("reasoning") or ""
    if provider.transport == "anthropic":
        return response["content"][0]["text"]
    if provider.transport == "google":
        return response["candidates"][0]["content"]["parts"][0]["text"]
    return ""


def _extract_usage(provider: Provider, response: dict) -> tuple[int, int]:
    """Return (input_tokens, output_tokens). Best-effort."""
    if provider.transport == "ollama":
        return (response.get("prompt_eval_count", 0), response.get("eval_count", 0))
    if provider.transport == "openai":
        u = response.get("usage", {})
        return (u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
    if provider.transport == "anthropic":
        u = response.get("usage", {})
        return (u.get("input_tokens", 0), u.get("output_tokens", 0))
    if provider.transport == "google":
        u = response.get("usageMetadata", {})
        return (u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))
    return (0, 0)


# ── Cost tracking ────────────────────────────────────────────────────────────

def _log_cost(provider: Provider, in_tok: int, out_tok: int, ms: int):
    cost_usd = (in_tok / 1_000_000) * provider.cost_in_per_1m + (out_tok / 1_000_000) * provider.cost_out_per_1m
    today = time.strftime("%Y-%m-%d")
    entry = {"day": today, "provider": provider.name, "model": provider.model,
             "in": in_tok, "out": out_tok, "cost_usd": round(cost_usd, 6), "ms": ms,
             "ts": int(time.time())}
    try:
        with COST_LOG.open("a") as fp:
            fp.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"cost log write failed: {e}")
    return cost_usd


# ── Public API ───────────────────────────────────────────────────────────────

def call(
    messages: list[dict],
    task: str = "default",
    explicit_provider: Optional[str] = None,
    **kwargs,
) -> dict:
    """
    Route a single LLM call to the appropriate provider.

    Returns:
        {"text": str, "provider": str, "model": str, "cost_usd": float, "ms": int,
         "input_tokens": int, "output_tokens": int}
    """
    p = pick_provider(task, explicit_provider)
    if not p:
        return {"error": f"no active provider for task={task} explicit={explicit_provider}",
                "available": [n for n, pp in PROVIDERS.items() if pp.is_active()]}

    body, url, headers = _build_request(p, messages, **kwargs)
    start = time.time()
    try:
        req = urllib_request.Request(url, data=body, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=kwargs.get("timeout_s", DEFAULT_TIMEOUT)) as r:
            response = json.loads(r.read())
        ms = int((time.time() - start) * 1000)
        text = _extract_text(p, response)
        in_tok, out_tok = _extract_usage(p, response)
        cost = _log_cost(p, in_tok, out_tok, ms)
        return {"text": text, "provider": p.name, "model": p.model, "cost_usd": cost,
                "ms": ms, "input_tokens": in_tok, "output_tokens": out_tok}
    except Exception as e:
        ms = int((time.time() - start) * 1000)
        log.error(f"{p.name} error after {ms}ms: {e}")
        # Try next in route as fallback
        route = TASK_ROUTES.get(task, TASK_ROUTES["default"])
        for fallback_name in route:
            if fallback_name == p.name:
                continue
            fp = PROVIDERS.get(fallback_name)
            if fp and fp.is_active():
                log.info(f"falling back to {fp.name}")
                return call(messages, task=task, explicit_provider=fallback_name, **kwargs)
        return {"error": str(e), "provider": p.name, "ms": ms}


def call_many(
    prompt: str,
    providers: Optional[list[str]] = None,
    task: str = "vote",
    **kwargs,
) -> list[dict]:
    """
    Fire the same prompt at multiple providers in parallel.
    Used by the BFT council voting layer.

    Robust to individual voice timeouts: any voice that doesn't reply
    inside its own per-provider timeout is skipped from the results.
    A global deadline 30s past the per-voice timeout caps total wall time.
    """
    if not providers:
        # Use task-route active providers
        route = TASK_ROUTES.get(task, TASK_ROUTES["default"])
        providers = [n for n in route if PROVIDERS.get(n) and PROVIDERS[n].is_active()][:5]

    messages = [{"role": "user", "content": prompt}]
    results = []
    per_voice_timeout = kwargs.get("timeout_s", DEFAULT_TIMEOUT)
    global_deadline = per_voice_timeout + 30

    with ThreadPoolExecutor(max_workers=min(8, len(providers))) as pool:
        futures = {pool.submit(call, messages, task, name, **kwargs): name for name in providers}
        try:
            for fut in as_completed(futures, timeout=global_deadline):
                try:
                    results.append(fut.result(timeout=5))
                except Exception as e:
                    name = futures.get(fut, "unknown")
                    log.warning(f"voice {name} failed: {e}")
                    results.append({"error": str(e), "provider": name})
        except TimeoutError:
            # Global deadline hit — collect whatever finished + cancel the rest
            finished_names = set()
            for fut, name in futures.items():
                if fut.done():
                    finished_names.add(name)
                    try:
                        results.append(fut.result(timeout=1))
                    except Exception as e:
                        results.append({"error": str(e), "provider": name})
                else:
                    log.warning(f"voice {name} cancelled (global deadline)")
                    fut.cancel()
                    results.append({"error": "global_deadline_exceeded", "provider": name})

    return results


def list_active() -> dict:
    """Return diagnostics of currently-active providers."""
    return {
        "active": [{"name": n, "model": p.model, "cost_in_per_1m": p.cost_in_per_1m,
                    "cost_out_per_1m": p.cost_out_per_1m, "context": p.context_window}
                   for n, p in PROVIDERS.items() if p.is_active()],
        "inactive": [{"name": n, "reason": "missing API key"}
                     for n, p in PROVIDERS.items() if not p.is_active()],
        "tasks": list(TASK_ROUTES.keys()),
    }


def today_costs() -> dict:
    """Aggregate today's cost across all providers."""
    today = time.strftime("%Y-%m-%d")
    totals = {}
    try:
        with COST_LOG.open("r") as fp:
            for line in fp:
                try:
                    e = json.loads(line)
                    if e.get("day") != today:
                        continue
                    p = e["provider"]
                    if p not in totals:
                        totals[p] = {"calls": 0, "in_tokens": 0, "out_tokens": 0, "cost_usd": 0.0}
                    totals[p]["calls"] += 1
                    totals[p]["in_tokens"] += e["in"]
                    totals[p]["out_tokens"] += e["out"]
                    totals[p]["cost_usd"] += e["cost_usd"]
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    grand_total = sum(t["cost_usd"] for t in totals.values())
    return {"day": today, "per_provider": totals, "total_usd": round(grand_total, 4)}


# ── CLI for ad-hoc routing ──────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="LLM Gateway router")
    p.add_argument("--prompt", help="single prompt to route")
    p.add_argument("--task", default="default", choices=list(TASK_ROUTES.keys()))
    p.add_argument("--provider", help="force specific provider")
    p.add_argument("--many", action="store_true", help="fire at all task providers in parallel")
    p.add_argument("--status", action="store_true", help="show active providers")
    p.add_argument("--costs", action="store_true", help="show today's cost summary")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if args.status:
        print(json.dumps(list_active(), indent=2))
    elif args.costs:
        print(json.dumps(today_costs(), indent=2))
    elif args.prompt:
        if args.many:
            results = call_many(args.prompt, task=args.task)
            for r in results:
                print(json.dumps(r, indent=2))
                print("---")
        else:
            messages = [{"role": "user", "content": args.prompt}]
            result = call(messages, task=args.task, explicit_provider=args.provider)
            print(json.dumps(result, indent=2))
    else:
        print("Usage: --prompt '...' [--task cheap|fast|tool|deep|...] [--many] OR --status OR --costs")
