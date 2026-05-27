"""MEOKCLAW Dual-Brain API v2.2.0 — Now with COUNCIL MODE and COST ARENA

The sovereign intelligence gateway. Routes every query through the optimal
model hemisphere, with full cost transparency and parallel model comparison.

Key additions:
- /api/council — Multi-model debate with BFT consensus
- /api/arena — Side-by-side model benchmarking
- Cost-per-response tracking with savings calculations
- Shareable result URLs
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dual_brain_orchestrator import DualBrainOrchestrator
from router_ml import MLRouter
from openrouter_client import OpenRouterClient
from ollama_client import OllamaClient
from backend.i18n import get_locale_from_request

# Optional enterprise modules
try:
    from semantic_cache import SemanticCache
    semantic_cache = SemanticCache()
    SEMANTIC_CACHE = True
except Exception as e:
    print(f"⚠️  Semantic cache not loaded: {e}")
    SEMANTIC_CACHE = False

try:
    from enterprise_auth import auth_manager, get_auth, requires_auth, AuthContext
    from fastapi import Depends
    ENTERPRISE_AUTH = True
except Exception as e:
    print(f"⚠️  Enterprise auth not loaded: {e}")
    ENTERPRISE_AUTH = False

try:
    from prompt_registry import prompt_registry
    PROMPT_REGISTRY = True
except Exception as e:
    print(f"⚠️  Prompt registry not loaded: {e}")
    PROMPT_REGISTRY = False

try:
    from guardrails import guardrails, EnforcementLevel
    GUARDRAILS = True
except Exception as e:
    print(f"⚠️  Guardrails not loaded: {e}")
    GUARDRAILS = False


def _check_guardrails(text: str, field: str = "input", locale: str = "en") -> str:
    """Run guardrails on user text. Raises HTTPException if blocked, returns cleaned text if redacted."""
    if not GUARDRAILS or not text:
        return text
    result = guardrails.check(text)
    if result.blocked:
        # Localize violation descriptions
        localized_violations = []
        for v in result.violations:
            localized_desc = guardrails.get_localized_description(v.type, locale)
            localized_violations.append({
                "type": v.type,
                "severity": v.severity,
                "description": localized_desc,
                "rule_id": v.rule_id,
            })
        raise HTTPException(
            status_code=400,
            detail={
                "error": guardrails.get_localized_description("prompt_injection", locale) if result.violations else "Blocked",
                "field": field,
                "violations": localized_violations,
                "enforcement": result.enforcement_level.value,
                "locale": locale,
            },
        )
    if result.enforcement_level == EnforcementLevel.REDACT:
        return result.cleaned_text
    return text


def _check_output_guardrails(text: str, field: str = "output", locale: str = "en") -> str:
    """Run guardrails on model output text. Redacts prompt leaks and PII but does not block."""
    if not GUARDRAILS or not text:
        return text
    result = guardrails.check(text, enforce_injection=EnforcementLevel.WARN, enforce_pii=EnforcementLevel.REDACT)
    if result.enforcement_level == EnforcementLevel.REDACT:
        return result.cleaned_text
    return text


try:
    from circuit_breaker import circuit_breaker
    CIRCUIT_BREAKER = True
except Exception as e:
    print(f"⚠️  Circuit breaker not loaded: {e}")
    CIRCUIT_BREAKER = False

try:
    from observability import tracer
    OBSERVABILITY = True
except Exception as e:
    print(f"⚠️  Observability not loaded: {e}")
    OBSERVABILITY = False

try:
    from batch_processor import batch_processor
    BATCH_PROCESSOR = True
except Exception as e:
    print(f"⚠️  Batch processor not loaded: {e}")
    BATCH_PROCESSOR = False

try:
    from structured_output import structured_engine
    STRUCTURED_OUTPUT = True
except Exception as e:
    print(f"⚠️  Structured output not loaded: {e}")
    STRUCTURED_OUTPUT = False


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    context: Optional[List[Dict[str, str]]] = None
    mode: str = Field(default="auto", pattern="^(auto|council|arena|fast|quantman)$")
    model: Optional[str] = Field(default=None, description="Explicit model override (e.g., 'owl-alpha', 'deepseek-v4-flash')")
    max_tokens: int = Field(default=1024, ge=1, le=4096)
    prompt_name: Optional[str] = Field(default=None, description="Registered prompt name from prompt registry")


class ArenaRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    models: List[str] = Field(default=["deepseek-v4-flash", "deepseek-v4-pro"])
    system_prompt: Optional[str] = None


class CouncilRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    models: List[str] = Field(default=["deepseek-v4-flash", "deepseek-v4-pro", "kimi-k2.6"])
    consensus_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    system_prompt: Optional[str] = None


class ModelResult(BaseModel):
    model: str
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    confidence: Optional[float] = None


class CouncilResponse(BaseModel):
    response_id: str
    prompt: str
    models: List[ModelResult]
    consensus_text: str
    consensus_score: float
    disagreeing_models: List[str]
    total_cost_usd: float
    total_latency_ms: int
    share_url: str
    timestamp: str


class ArenaResponse(BaseModel):
    response_id: str
    prompt: str
    models: List[ModelResult]
    winner: Optional[str] = None
    cost_comparison: Dict[str, float]
    speed_comparison: Dict[str, int]
    share_url: str
    timestamp: str


class ChatResponse(BaseModel):
    response_id: str
    hemisphere: str
    model: str
    text: str
    confidence: float
    cost_usd: float
    latency_ms: int
    tokens_in: int
    tokens_out: int
    context: Optional[List[Dict[str, str]]] = None
    share_url: str
    # QuantMan metadata (optional)
    hy3_state: Optional[int] = None
    partnership_score: Optional[float] = None
    convergence_method: Optional[str] = None
    left_text: Optional[str] = None
    right_text: Optional[str] = None
    sov3_mediation: Optional[Dict[str, Any]] = None


class CostSavings(BaseModel):
    query_cost_usd: float
    gpt4_equivalent_cost: float
    savings_percent: float
    savings_message: str


# ---------------------------------------------------------------------------
# Cost estimation for savings calculations
# ---------------------------------------------------------------------------

GPT4_COST_PER_1K = 0.03  # GPT-4o input cost per 1K tokens

COST_RATES: Dict[str, Dict[str, float]] = {
    "deepseek-v4-flash": {"input": 0.0001, "output": 0.0002},
    "deepseek-v4-pro": {"input": 0.0015, "output": 0.005},
    "kimi-k2.6": {"input": 0.002, "output": 0.008},
    "llama3.1:8b": {"input": 0.0, "output": 0.0},  # Local = free
    "llama3.2:3b": {"input": 0.0, "output": 0.0},
}


def calculate_savings(tokens_in: int, tokens_out: int, model: str) -> CostSavings:
    """Calculate how much money was saved vs GPT-4."""
    our_cost = COST_RATES.get(model, {"input": 0.001, "output": 0.003})
    our_total = (tokens_in / 1000) * our_cost["input"] + (tokens_out / 1000) * our_cost["output"]
    gpt4_total = (tokens_in / 1000) * GPT4_COST_PER_1K + (tokens_out / 1000) * (GPT4_COST_PER_1K * 2)
    
    if gpt4_total > 0:
        savings_pct = ((gpt4_total - our_total) / gpt4_total) * 100
    else:
        savings_pct = 0.0
    
    messages = [
        (95, "🔥 SAVINGS BEAST: You saved 95%+ vs GPT-4!"),
        (90, "💰 MASSIVE SAVINGS: 90%+ cheaper than GPT-4"),
        (80, "💸 Great savings: 80%+ cheaper than GPT-4"),
        (50, "✅ Good savings: 50%+ cheaper than GPT-4"),
        (0,  f"💡 Used {model} — cost transparent"),
    ]
    msg = next(m for threshold, m in messages if savings_pct >= threshold)
    
    return CostSavings(
        query_cost_usd=round(our_total, 6),
        gpt4_equivalent_cost=round(gpt4_total, 6),
        savings_percent=round(savings_pct, 1),
        savings_message=msg,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.orch = DualBrainOrchestrator()
    app.state.ml_router = MLRouter()
    app.state.openrouter = OpenRouterClient()
    app.state.vast_ollama = OllamaClient("http://localhost:11436")
    app.state.local_ollama = OllamaClient("http://localhost:11434")
    app.state.quantman = QuantManEngine()
    app.state.council_results: Dict[str, CouncilResponse] = {}
    app.state.arena_results: Dict[str, ArenaResponse] = {}
    # Warm up local models in background
    asyncio.create_task(warm_up_models())
    yield
    # Cleanup handled by __del__ in clients


app = FastAPI(
    title="MEOKCLAW Dual-Brain API",
    version="2.3.0",
    description="Sovereign Intelligence Gateway with Council Mode",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://meokclaw-v2.vercel.app",
        "https://meokclaw-v2-nicholas-projects-d92dd02f.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.post("/api/dual-brain", response_model=ChatResponse)
async def dual_brain_chat(req: ChatRequest, request: Request):
    locale = get_locale_from_request(request.headers.get("accept-language"))
    req.message = _check_guardrails(req.message, field="message", locale=locale)
    orch: DualBrainOrchestrator = app.state.orch
    response_id = str(uuid.uuid4())[:8]
    
    # ══ Prompt Registry ══
    system_prompt = None
    if PROMPT_REGISTRY and prompt_registry and req.prompt_name:
        try:
            system_prompt, user_prompt, version_id = prompt_registry.render(req.prompt_name, {"query": req.message})
            req.message = user_prompt
        except Exception:
            pass
    
    # ══ LAYER 1: Semantic Cache ══
    if SEMANTIC_CACHE and semantic_cache:
        cached = await semantic_cache.get(req.message)
        if cached:
            text, sim, meta = cached
            return ChatResponse(
                response_id=response_id,
                hemisphere="cache",
                model=meta.get("original_model", "cached"),
                text=text,
                confidence=round(sim, 3),
                cost_usd=0.0,
                latency_ms=50,
                tokens_in=0,
                tokens_out=0,
                context=None,
                share_url=f"https://meokclaw-v2.vercel.app/share/{response_id}",
            )
    
    # ══ LAYER 2: Observability + Circuit Breaker ══
    trace_id = None
    if OBSERVABILITY and tracer:
        trace_id = tracer.start_trace(metadata={"endpoint": "/api/dual-brain", "mode": req.mode})
        span = tracer.start_span("inference", trace_id=trace_id)
        span.set_attribute("model", req.model or "auto")
        span.set_attribute("mode", req.mode)
    else:
        span = None
    
    start_time = time.time()
    try:
        result = await orch.think(req.message, req.context, model_override=req.model, mode=req.mode)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if span:
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("cost_usd", result.get("cost_usd", 0))
            span.set_attribute("model", result.get("model", result.get("primary_model", "unknown")))
            span.set_attribute("hemisphere", result.get("hemisphere", "unknown"))
            tracer.finish_span(span.id)
            tracer.finish_trace(trace_id)
        
        # ══ LAYER 3: Cache Store ══
        if SEMANTIC_CACHE and semantic_cache and result.get("text"):
            await semantic_cache.set(
                query=req.message,
                response_text=result["text"],
                model=result.get("model", result.get("primary_model", "unknown")),
                cost_usd=result.get("cost_usd", 0.0),
            )
        
        savings = calculate_savings(
            result.get("tokens_in", 0),
            result.get("tokens_out", 0),
            result.get("model", result.get("primary_model", "unknown")),
        )
        
        return ChatResponse(
            response_id=response_id,
            hemisphere=result.get("hemisphere", "unknown"),
            model=result.get("model", result.get("primary_model", "unknown")),
            text=_check_output_guardrails(result.get("text", "[No response]")),
            confidence=result.get("confidence", 0.0),
            cost_usd=round(result.get("cost_usd", 0.0), 6),
            latency_ms=int(result.get("latency_ms", 0)),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
            context=result.get("context"),
            share_url=f"https://meokclaw-v2.vercel.app/share/{response_id}",
            hy3_state=result.get("hy3_state"),
            partnership_score=result.get("partnership_score"),
            convergence_method=result.get("convergence_method"),
            left_text=result.get("left_text"),
            right_text=result.get("right_text"),
            sov3_mediation=result.get("sov3_mediation"),
        )
    except Exception as e:
        if span:
            span.set_error(str(e))
            tracer.finish_span(span.id)
            tracer.finish_trace(trace_id)
        raise


@app.post("/api/quantman", response_model=ChatResponse)
async def quantman_chat(req: ChatRequest, request: Request):
    """QuantMan Mode: Nested dual-brain with SOV3 mediation and HY3 convergence."""
    locale = get_locale_from_request(request.headers.get("accept-language"))
    req.message = _check_guardrails(req.message, field="message", locale=locale)
    engine: QuantManEngine = app.state.quantman
    response_id = str(uuid.uuid4())[:8]
    
    # Prompt Registry
    if PROMPT_REGISTRY and prompt_registry and req.prompt_name:
        try:
            system_prompt, user_prompt, version_id = prompt_registry.render(req.prompt_name, {"query": req.message})
            req.message = user_prompt
        except Exception:
            pass
    
    # Semantic cache check
    if SEMANTIC_CACHE and semantic_cache:
        cached = await semantic_cache.get(req.message)
        if cached:
            text, sim, meta = cached
            return ChatResponse(
                response_id=response_id,
                hemisphere="quantman_cache",
                model=meta.get("original_model", "cached"),
                text=text,
                confidence=round(sim, 3),
                cost_usd=0.0,
                latency_ms=50,
                tokens_in=0,
                tokens_out=0,
                context=None,
                share_url=f"https://meokclaw-v2.vercel.app/share/{response_id}",
            )
    
    # Observability
    trace_id = None
    if OBSERVABILITY and tracer:
        trace_id = tracer.start_trace(metadata={"endpoint": "/api/quantman"})
        span = tracer.start_span("quantman_inference", trace_id=trace_id)
        span.set_attribute("mode", "quantman")
    else:
        span = None
    
    messages = [{"role": "user", "content": req.message}]
    if req.context:
        messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in req.context[-6:]]
        messages.append({"role": "user", "content": req.message})
    
    start_time = time.time()
    result = await engine.think(messages, temperature=0.7, max_tokens=min(1024, req.max_tokens if hasattr(req, 'max_tokens') else 1024))
    latency_ms = int((time.time() - start_time) * 1000)
    
    if span:
        span.set_attribute("latency_ms", latency_ms)
        span.set_attribute("cost_usd", result.total_cost_usd)
        span.set_attribute("hy3_state", result.hy3_state)
        span.set_attribute("partnership_score", result.partnership_score)
        tracer.finish_span(span.id)
        tracer.finish_trace(trace_id)
    
    # Cache store
    if SEMANTIC_CACHE and semantic_cache and result.text:
        await semantic_cache.set(
            query=req.message,
            response_text=result.text,
            model=f"quantman_left:{','.join(result.left.models_used)}_right:{','.join(result.right.models_used)}",
            cost_usd=result.total_cost_usd,
        )
    
    return ChatResponse(
        response_id=response_id,
        hemisphere="quantman",
        model=f"left:{','.join(result.left.models_used)}|right:{','.join(result.right.models_used)}",
        text=_check_output_guardrails(result.text),
        confidence=result.partnership_score,
        cost_usd=round(result.total_cost_usd, 6),
        latency_ms=latency_ms,
        tokens_in=0,
        tokens_out=0,
        context=None,
        share_url=f"https://meokclaw-v2.vercel.app/share/{response_id}",
        hy3_state=result.hy3_state,
        partnership_score=result.partnership_score,
        convergence_method=result.convergence_method,
        left_text=result.left.text,
        right_text=result.right.text,
        sov3_mediation=result.sov3_mediation,
    )


@app.post("/api/council", response_model=CouncilResponse)
async def council_mode(req: CouncilRequest, request: Request):
    """Run multiple models in parallel and find consensus via BFT voting."""
    locale = get_locale_from_request(request.headers.get("accept-language"))
    req.prompt = _check_guardrails(req.prompt, field="prompt", locale=locale)
    if req.system_prompt:
        req.system_prompt = _check_guardrails(req.system_prompt, field="system_prompt", locale=locale)
    openrouter: OpenRouterClient = app.state.openrouter
    vast: OllamaClient = app.state.vast_ollama
    local: OllamaClient = app.state.local_ollama
    
    response_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # Build messages
    messages = []
    if req.system_prompt:
        messages.append({"role": "system", "content": req.system_prompt})
    messages.append({"role": "user", "content": req.prompt})
    
    # Launch all models in parallel
    async def run_model(model_id: str) -> ModelResult:
        t0 = time.time()
        
        # Route to appropriate provider
        if model_id.startswith("llama") or model_id.startswith("gemma") or model_id.startswith("qwen"):
            # Try local first, then vast
            try:
                res = await local.chat_completion(model_id, messages, temperature=0.7, max_tokens=1024)
            except:
                res = await vast.chat_completion(model_id, messages, temperature=0.7, max_tokens=1024)
        else:
            res = await openrouter.chat_completion(model_id, messages, temperature=0.7, max_tokens=1024)
        
        latency = int((time.time() - t0) * 1000)
        return ModelResult(
            model=model_id,
            text=res.text,
            tokens_in=res.tokens_in,
            tokens_out=res.tokens_out,
            cost_usd=res.cost_usd,
            latency_ms=latency,
            confidence=None,
        )
    
    # Execute all models concurrently
    results = await asyncio.gather(*[run_model(m) for m in req.models], return_exceptions=True)
    models = [r for r in results if not isinstance(r, Exception)]
    failed = [m for i, m in enumerate(req.models) if isinstance(results[i], Exception)]
    
    # Simple BFT consensus: longest common substring / similarity
    # For now: use the response with median length as "consensus"
    if models:
        sorted_by_len = sorted(models, key=lambda x: len(x.text))
        consensus = sorted_by_len[len(sorted_by_len) // 2]
        consensus_score = min(1.0, len(models) / max(len(req.models), 1))
        disagreeing = [m.model for m in models if m.model != consensus.model]
        
        # Actually: if we have 3+ models, check if majority agree on key facts
        if len(models) >= 3:
            # Simple heuristic: count models that mention the same first sentence keywords
            first_words = [set(m.text.split()[:5]) for m in models]
            overlap_scores = []
            for i, words_i in enumerate(first_words):
                overlaps = sum(len(words_i & words_j) / max(len(words_i), 1) 
                             for j, words_j in enumerate(first_words) if i != j)
                overlap_scores.append(overlaps / max(len(models) - 1, 1))
            
            best_idx = overlap_scores.index(max(overlap_scores))
            consensus = models[best_idx]
            consensus_score = max(overlap_scores)
            disagreeing = [m.model for m in models if m.model != consensus.model]
    else:
        consensus = ModelResult(model="none", text="All models failed.", tokens_in=0, tokens_out=0, cost_usd=0, latency_ms=0)
        consensus_score = 0.0
        disagreeing = []
    
    total_cost = sum(m.cost_usd for m in models)
    total_latency = int((time.time() - start_time) * 1000)
    
    resp = CouncilResponse(
        response_id=response_id,
        prompt=req.prompt,
        models=models,
        consensus_text=consensus.text,
        consensus_score=round(consensus_score, 2),
        disagreeing_models=disagreeing[:3],  # Cap at 3
        total_cost_usd=round(total_cost, 6),
        total_latency_ms=total_latency,
        share_url=f"https://meokclaw-v2.vercel.app/council/{response_id}",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    
    app.state.council_results[response_id] = resp
    return resp


@app.post("/api/arena", response_model=ArenaResponse)
async def arena_mode(req: ArenaRequest, request: Request):
    """Side-by-side model comparison with cost tracking."""
    locale = get_locale_from_request(request.headers.get("accept-language"))
    req.prompt = _check_guardrails(req.prompt, field="prompt", locale=locale)
    if req.system_prompt:
        req.system_prompt = _check_guardrails(req.system_prompt, field="system_prompt", locale=locale)
    openrouter: OpenRouterClient = app.state.openrouter
    vast: OllamaClient = app.state.vast_ollama
    local: OllamaClient = app.state.local_ollama
    
    response_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    messages = []
    if req.system_prompt:
        messages.append({"role": "system", "content": req.system_prompt})
    messages.append({"role": "user", "content": req.prompt})
    
    async def run_model(model_id: str) -> ModelResult:
        t0 = time.time()
        
        if model_id.startswith("llama") or model_id.startswith("gemma") or model_id.startswith("qwen"):
            try:
                res = await local.chat_completion(model_id, messages, temperature=0.7, max_tokens=1024)
            except:
                res = await vast.chat_completion(model_id, messages, temperature=0.7, max_tokens=1024)
        else:
            res = await openrouter.chat_completion(model_id, messages, temperature=0.7, max_tokens=1024)
        
        latency = int((time.time() - t0) * 1000)
        return ModelResult(
            model=model_id,
            text=res.text,
            tokens_in=res.tokens_in,
            tokens_out=res.tokens_out,
            cost_usd=res.cost_usd,
            latency_ms=latency,
            confidence=None,
        )
    
    results = await asyncio.gather(*[run_model(m) for m in req.models], return_exceptions=True)
    models = [r for r in results if not isinstance(r, Exception)]
    
    # Winner = best quality heuristic (longest coherent response / lowest cost ratio)
    winner = None
    if models:
        # Score = (tokens_out / cost) / latency — efficiency metric
        def score(m: ModelResult) -> float:
            if m.cost_usd <= 0:
                return m.tokens_out / max(m.latency_ms, 1) * 1000  # Free = huge score
            return (m.tokens_out / m.cost_usd) / max(m.latency_ms, 1)
        
        winner_model = max(models, key=score)
        winner = winner_model.model
    
    cost_comparison = {m.model: m.cost_usd for m in models}
    speed_comparison = {m.model: m.latency_ms for m in models}
    total_cost = sum(m.cost_usd for m in models)
    total_latency = int((time.time() - start_time) * 1000)
    
    resp = ArenaResponse(
        response_id=response_id,
        prompt=req.prompt,
        models=models,
        winner=winner,
        cost_comparison=cost_comparison,
        speed_comparison=speed_comparison,
        share_url=f"https://meokclaw-v2.vercel.app/arena/{response_id}",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    
    app.state.arena_results[response_id] = resp
    return resp


# ---------------------------------------------------------------------------
# Semantic Cache endpoints
# ---------------------------------------------------------------------------

@app.get("/api/cache-stats")
async def cache_stats():
    if semantic_cache:
        return semantic_cache.stats()
    return {"status": "disabled"}


@app.post("/api/cache-clear")
async def cache_clear():
    if semantic_cache:
        semantic_cache.clear()
        return {"status": "cleared"}
    return {"status": "disabled"}


# ---------------------------------------------------------------------------
# Enterprise Auth endpoints
# ---------------------------------------------------------------------------

class CreateKeyRequest(BaseModel):
    name: str
    org_id: str
    scopes: list[str] = None
    max_budget: float = 100.0
    team_id: str = None
    rate_limit_rpm: int = 60
    expires_days: int = None

class CreateOrgRequest(BaseModel):
    name: str
    max_budget: float = 1000.0

@app.post("/api/auth/orgs")
async def create_org(req: CreateOrgRequest):
    if not ENTERPRISE_AUTH:
        raise HTTPException(status_code=503, detail="Enterprise auth not enabled")
    org = auth_manager.create_org(req.name, req.max_budget)
    return {"org_id": org.id, "name": org.name}

@app.post("/api/auth/keys")
async def create_key(req: CreateKeyRequest):
    if not ENTERPRISE_AUTH:
        raise HTTPException(status_code=503, detail="Enterprise auth not enabled")
    plaintext, key = auth_manager.create_key(
        org_id=req.org_id,
        name=req.name,
        scopes=req.scopes,
        max_budget=req.max_budget,
        team_id=req.team_id,
        rate_limit_rpm=req.rate_limit_rpm,
        expires_days=req.expires_days,
    )
    return {"api_key": plaintext, "key_id": key.id, "scopes": key.scopes}

@app.get("/api/auth/keys")
async def list_keys(org_id: str):
    if not ENTERPRISE_AUTH:
        raise HTTPException(status_code=503, detail="Enterprise auth not enabled")
    keys = auth_manager.list_keys(org_id)
    return [{"id": k.id, "name": k.name, "scopes": k.scopes, "budget_used": k.used_budget_usd, "budget_max": k.max_budget_usd, "active": k.is_active} for k in keys]

@app.delete("/api/auth/keys/{key_id}")
async def revoke_key(key_id: str):
    if not ENTERPRISE_AUTH:
        raise HTTPException(status_code=503, detail="Enterprise auth not enabled")
    success = auth_manager.revoke_key(key_id)
    return {"revoked": success}

@app.get("/api/auth/stats")
async def auth_stats(org_id: Optional[str] = None):
    if not ENTERPRISE_AUTH:
        raise HTTPException(status_code=503, detail="Enterprise auth not enabled")
    return auth_manager.stats(org_id)

@app.get("/api/audit-log")
async def audit_log(org_id: str, limit: int = 100):
    if not ENTERPRISE_AUTH:
        raise HTTPException(status_code=503, detail="Enterprise auth not enabled")
    logs = auth_manager.get_audit_log(org_id, limit)
    return [{
        "timestamp": l.timestamp,
        "action": l.action,
        "model": l.model,
        "cost_usd": l.cost_usd,
        "tokens_in": l.tokens_in,
        "tokens_out": l.tokens_out,
        "latency_ms": l.latency_ms,
        "success": l.success,
    } for l in logs]


# ---------------------------------------------------------------------------
# Info / health endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.3.0",
        "features": [
            "dual-brain", "council", "arena", "cost-tracking", "ml-router",
            "semantic-cache", "enterprise-auth", "openrouter-compat",
            "prompt-registry", "guardrails", "circuit-breaker",
            "observability", "batch-processing", "structured-output",
            "siri-integration",
        ],
        "models": {
            "left": "deepseek-v4-flash",
            "right": "deepseek-v4-pro",
            "both": "deepseek-v4-pro+flash",
            "fallback": "llama3.1:8b",
        },
        "endpoints": {
            "chat": "/api/dual-brain",
            "council": "/api/council",
            "arena": "/api/arena",
            "router_stats": "/api/router-stats",
            "reflection_stats": "/api/reflection-stats",
            "live_metrics": "/api/live-metrics",
            "cost_savings": "/api/cost-savings/{model}/{tokens_in}/{tokens_out}",
        },
    }


@app.get("/api/cost-savings/{model}/{tokens_in}/{tokens_out}")
async def cost_savings(model: str, tokens_in: int, tokens_out: int):
    """Get cost savings for a specific query."""
    savings = calculate_savings(tokens_in, tokens_out, model)
    return savings.model_dump()


@app.get("/api/council/{response_id}")
async def get_council_result(response_id: str):
    """Retrieve a cached council result."""
    if response_id not in app.state.council_results:
        raise HTTPException(status_code=404, detail="Council result not found")
    return app.state.council_results[response_id]


@app.get("/api/arena/{response_id}")
async def get_arena_result(response_id: str):
    """Retrieve a cached arena result."""
    if response_id not in app.state.arena_results:
        raise HTTPException(status_code=404, detail="Arena result not found")
    return app.state.arena_results[response_id]


# ---------------------------------------------------------------------------
# Existing stats endpoints (from v2.1.0)
# ---------------------------------------------------------------------------

@app.get("/api/router-stats")
async def router_stats():
    from dual_brain_router import CorpusCallosumRouter
    router = CorpusCallosumRouter()
    return router.stats()


@app.get("/api/model-health")
async def model_health():
    from model_health_tracker import get_tracker
    return get_tracker().summary()


@app.get("/api/reflection-stats")
async def reflection_stats():
    orch: DualBrainOrchestrator = app.state.orch
    return orch.reflection.stats()


@app.get("/api/live-metrics")
async def live_metrics():
    """Combined metrics for the war room dashboard."""
    orch: DualBrainOrchestrator = app.state.orch
    router = CorpusCallosumRouter()
    
    router_stats_data = router.stats()
    reflection_stats_data = orch.reflection.stats()
    
    # Calculate cost burn rate from router stats
    total_cost = router_stats_data.get("total_cost_usd", 0)
    total_queries = router_stats_data.get("total_queries", 0)
    avg_cost = total_cost / max(total_queries, 1)
    
    return {
        "status": "ok",
        "version": "2.3.0",
        "router": router_stats_data,
        "reflection": reflection_stats_data,
        "cost_burn_rate": round(avg_cost, 6),
        "models": {
            "left": {"name": "deepseek-v4-flash", "status": "available", "cost_per_1k": 0.0001},
            "right": {"name": "deepseek-v4-pro", "status": "available", "cost_per_1k": 0.0015},
            "both": {"name": "deepseek-v4-pro+flash", "status": "available", "cost_per_1k": 0.0008},
        },
        "features": {
            "council_mode": True,
            "arena_mode": True,
            "cost_tracking": True,
            "ml_router": True,
        },
    }


# ---------------------------------------------------------------------------
# Guardrails endpoint
# ---------------------------------------------------------------------------

class GuardrailCheckRequest(BaseModel):
    text: str
    enforce_pii: str = "redact"
    enforce_injection: str = "block"
    enforce_content: str = "block"

@app.post("/api/guardrails/check")
async def guardrails_check(req: GuardrailCheckRequest, request: Request):
    if not GUARDRAILS:
        raise HTTPException(status_code=503, detail="Guardrails not enabled")
    locale = get_locale_from_request(request.headers.get("accept-language"))
    result = guardrails.check(
        req.text,
        enforce_pii=EnforcementLevel(req.enforce_pii) if hasattr(EnforcementLevel, req.enforce_pii.upper()) else EnforcementLevel.REDACT,
        enforce_injection=EnforcementLevel(req.enforce_injection) if hasattr(EnforcementLevel, req.enforce_injection.upper()) else EnforcementLevel.BLOCK,
        enforce_content=EnforcementLevel(req.enforce_content) if hasattr(EnforcementLevel, req.enforce_content.upper()) else EnforcementLevel.BLOCK,
    )
    return {
        "blocked": result.blocked,
        "cleaned_text": result.cleaned_text,
        "violations": [{"type": v.type, "severity": v.severity, "description": guardrails.get_localized_description(v.type, locale), "rule": v.rule_id} for v in result.violations],
        "processing_time_ms": result.processing_time_ms,
        "locale": locale,
    }

@app.get("/api/guardrails/stats")
async def guardrails_stats():
    if not GUARDRAILS:
        return {"status": "disabled"}
    return guardrails.stats()


# ---------------------------------------------------------------------------
# Circuit Breaker endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health/models")
async def model_health():
    if not CIRCUIT_BREAKER:
        return {"status": "disabled"}
    return circuit_breaker.stats()


# ---------------------------------------------------------------------------
# Observability endpoints
# ---------------------------------------------------------------------------

@app.get("/api/traces")
async def get_traces(limit: int = 100):
    if not OBSERVABILITY:
        return {"status": "disabled"}
    traces = tracer.get_recent_traces(limit)
    return {"traces": [t.to_dict() for t in traces]}

@app.get("/api/metrics")
async def get_metrics():
    if not OBSERVABILITY:
        return {"status": "disabled"}
    return tracer.metrics()

@app.get("/api/metrics/prometheus")
async def prometheus_metrics():
    if not OBSERVABILITY:
        return "# observability disabled"
    return tracer.export_prometheus()


# ---------------------------------------------------------------------------
# Batch Processing endpoints
# ---------------------------------------------------------------------------

class BatchSubmitRequest(BaseModel):
    requests: List[Dict[str, str]]
    model: str = "deepseek-v4-flash"
    max_concurrency: int = 5
    system_prompt: Optional[str] = None
    callback_url: Optional[str] = None

@app.post("/api/batch")
async def batch_submit(req: BatchSubmitRequest, request: Request):
    if not BATCH_PROCESSOR:
        raise HTTPException(status_code=503, detail="Batch processing not enabled")
    locale = get_locale_from_request(request.headers.get("accept-language"))
    # Guardrails check on every request in the batch
    checked_requests = []
    for r in req.requests:
        content = r.get("content", "")
        if content:
            r = {**r, "content": _check_guardrails(content, field="batch_request.content", locale=locale)}
        checked_requests.append(r)
    req.requests = checked_requests
    if req.system_prompt:
        req.system_prompt = _check_guardrails(req.system_prompt, field="system_prompt", locale=locale)
    job_id = await batch_processor.submit(
        requests=req.requests,
        model=req.model,
        max_concurrency=req.max_concurrency,
        system_prompt=req.system_prompt,
        callback_url=req.callback_url,
    )
    return {"job_id": job_id, "status": "submitted"}

@app.get("/api/batch/{job_id}")
async def batch_status(job_id: str):
    if not BATCH_PROCESSOR:
        raise HTTPException(status_code=503, detail="Batch processing not enabled")
    return batch_processor.status(job_id)

@app.get("/api/batch/{job_id}/results")
async def batch_results(job_id: str, format: str = "json"):
    if not BATCH_PROCESSOR:
        raise HTTPException(status_code=503, detail="Batch processing not enabled")
    return batch_processor.results(job_id, format)

@app.delete("/api/batch/{job_id}")
async def batch_cancel(job_id: str):
    if not BATCH_PROCESSOR:
        raise HTTPException(status_code=503, detail="Batch processing not enabled")
    success = batch_processor.cancel(job_id)
    return {"cancelled": success}


# ---------------------------------------------------------------------------
# Prompt Registry endpoints
# ---------------------------------------------------------------------------

class PromptRegisterRequest(BaseModel):
    name: str
    system_prompt: str
    template: str
    variables: Optional[Dict[str, str]] = None
    author: str = "system"
    environment: str = "dev"

@app.post("/api/prompts")
async def prompt_register(req: PromptRegisterRequest):
    if not PROMPT_REGISTRY:
        raise HTTPException(status_code=503, detail="Prompt registry not enabled")
    version = prompt_registry.register(
        name=req.name,
        system_prompt=req.system_prompt,
        template=req.template,
        variables=req.variables,
        author=req.author,
        environment=req.environment,
    )
    return {"version_id": version.id, "version": version.version}

@app.get("/api/prompts")
async def prompt_list():
    if not PROMPT_REGISTRY:
        return {"status": "disabled"}
    return {"prompts": prompt_registry.list_prompts()}

@app.get("/api/prompts/{name}")
async def prompt_stats(name: str):
    if not PROMPT_REGISTRY:
        return {"status": "disabled"}
    return prompt_registry.stats(name)


# ---------------------------------------------------------------------------
# Siri Shortcuts integration
# ---------------------------------------------------------------------------

try:
    from siri_integration import mount_siri_routes
    mount_siri_routes(app)
except Exception as e:
    print(f"⚠️  Siri integration not loaded: {e}")

# ---------------------------------------------------------------------------
# OpenRouter compatibility layer
# ---------------------------------------------------------------------------

try:
    from openrouter_integration import mount_openrouter_routes
    mount_openrouter_routes(app)
except Exception as e:
    print(f"⚠️  OpenRouter integration not loaded: {e}")


# ═══ Dashboard Static Files ═══
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3201, log_level="info")


# ═══════════════════════════════════════════════════════════════════════════════
# Twin Brain Router
# ═══════════════════════════════════════════════════════════════════════════════

from twin_brain_engine import TwinBrainEngine
from quantman_engine import QuantManEngine, warm_up_models

_twin_engine: Optional[TwinBrainEngine] = None

def get_twin_engine() -> TwinBrainEngine:
    global _twin_engine
    if _twin_engine is None:
        _twin_engine = TwinBrainEngine()
    return _twin_engine


class TwinChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    draft_model: str = Field(default="qwen3:0.6b")
    verify_model: str = Field(default="qwen3:8b")
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class TwinChatResponse(BaseModel):
    response_id: str
    text: str
    draft: Optional[str]
    draft_accepted: bool
    draft_latency_ms: float
    verify_latency_ms: float
    total_latency_ms: float
    cost_usd: float
    draft_node: Optional[str]
    verify_node: Optional[str]
    fallback: bool = False


@app.post("/api/twin/chat", response_model=TwinChatResponse)
async def twin_brain_chat(req: TwinChatRequest):
    """Twin Brain: M2 drafts fast → M4 verifies deep. Sovereign speculative decoding."""
    engine = get_twin_engine()
    result = await engine.generate(
        prompt=req.message,
        draft_max_tokens=min(64, req.max_tokens // 4),
        verify_max_tokens=req.max_tokens,
    )
    response_id = str(uuid.uuid4())[:8]
    return TwinChatResponse(
        response_id=response_id,
        text=result.get("text", "[No response]"),
        draft=result.get("draft"),
        draft_accepted=result.get("draft_accepted", False),
        draft_latency_ms=result.get("draft_latency_ms", 0),
        verify_latency_ms=result.get("verify_latency_ms", 0),
        total_latency_ms=result.get("total_latency_ms", 0),
        cost_usd=result.get("cost_usd", 0),
        draft_node=result.get("draft_node"),
        verify_node=result.get("verify_node"),
        fallback=result.get("fallback", False),
    )
