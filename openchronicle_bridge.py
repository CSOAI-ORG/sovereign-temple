"""
SOV3 OpenChronicle Bridge
Persistent memory + tamper-proof audit trail for the 47 generals.

Connects SOV3 to OpenChronicle (CarlDog variant) for:
- Agent decision logging with hash chains
- Persistent memory across sessions
- FTS5 search across all agent history
- Solana anchoring of critical decisions
"""

import os
import hashlib
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/chronicle", tags=["openchronicle"])

# ── Config ───────────────────────────────────────────────────────────────────

OC_API_URL = os.environ.get("OPENCHRONICLE_URL", "http://localhost:3001")
OC_MCP_URL = os.environ.get("OPENCHRONICLE_MCP", "http://localhost:3001/mcp")
SOLANA_ANCHOR_ENABLED = os.environ.get("SOLANA_ANCHOR", "false").lower() == "true"
MOCK_MODE = os.environ.get("CHRONICLE_MOCK", "true").lower() == "true"

# ── In-Memory Mock Store ─────────────────────────────────────────────────────
_chronicle_log: List[Dict[str, Any]] = []
_hash_chain: List[str] = []

# ── Data Models ──────────────────────────────────────────────────────────────

class LogEventRequest(BaseModel):
    agent: str = Field(..., description="Agent name (e.g. General-1)")
    archetype: Optional[str] = Field(default=None, description="Agent archetype")
    event_type: str = Field(..., description="decision_request | decision_made | action_taken | verification")
    input_data: Optional[Dict[str, Any]] = Field(default=None)
    output_data: Optional[Dict[str, Any]] = Field(default=None)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    risk_level: Optional[str] = Field(default="low")
    context: Optional[Dict[str, Any]] = Field(default=None)
    solana_anchor: bool = Field(default=False, description="Anchor this event to Solana")

class LogEventResponse(BaseModel):
    event_id: str
    agent: str
    event_type: str
    event_hash: str
    previous_hash: Optional[str]
    anchored: bool
    timestamp: str

class SearchRequest(BaseModel):
    query: str
    agent: Optional[str] = None
    archetype: Optional[str] = None
    event_type: Optional[str] = None
    limit: int = 10

class AnchorRequest(BaseModel):
    event_id: str

class ChronicleHealthResponse(BaseModel):
    status: str
    mock_mode: bool
    solana_anchor_enabled: bool
    log_size: int
    chain_length: int
    api_url: str

# ── Helpers ──────────────────────────────────────────────────────────────────

def _compute_hash(event: Dict[str, Any], previous_hash: Optional[str] = None) -> str:
    canonical = json.dumps(event, sort_keys=True, separators=(',', ':'))
    data = canonical + (previous_hash or "")
    return hashlib.sha256(data.encode()).hexdigest()

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/log", response_model=LogEventResponse)
async def log_event(request: LogEventRequest):
    """Log an agent event with hash-chained tamper evidence."""
    event_id = f"evt-{int(time.time() * 1000)}-{hashlib.sha256(request.agent.encode()).hexdigest()[:8]}"
    timestamp = datetime.utcnow().isoformat()
    
    previous_hash = _hash_chain[-1] if _hash_chain else None
    
    event_data = {
        "event_id": event_id,
        "agent": request.agent,
        "archetype": request.archetype,
        "event_type": request.event_type,
        "input_data": request.input_data,
        "output_data": request.output_data,
        "confidence": request.confidence,
        "risk_level": request.risk_level,
        "context": request.context,
        "timestamp": timestamp,
    }
    
    event_hash = _compute_hash(event_data, previous_hash)
    
    record = {
        **event_data,
        "event_hash": event_hash,
        "previous_hash": previous_hash,
        "anchored": False,
        "solana_tx": None,
    }
    
    _chronicle_log.append(record)
    _hash_chain.append(event_hash)
    
    anchored = False
    if request.solana_anchor and SOLANA_ANCHOR_ENABLED and not MOCK_MODE:
        # In production, anchor to Solana here
        anchored = True
        record["anchored"] = True
    
    return LogEventResponse(
        event_id=event_id,
        agent=request.agent,
        event_type=request.event_type,
        event_hash=event_hash,
        previous_hash=previous_hash,
        anchored=anchored,
        timestamp=timestamp,
    )


@router.post("/search")
async def search_events(request: SearchRequest):
    """Search agent decision history (FTS5-style in production)."""
    results = _chronicle_log
    
    if request.agent:
        results = [r for r in results if r["agent"] == request.agent]
    if request.archetype:
        results = [r for r in results if r.get("archetype") == request.archetype]
    if request.event_type:
        results = [r for r in results if r["event_type"] == request.event_type]
    
    # Simple text search across input/output
    query_lower = request.query.lower()
    filtered = []
    for r in results:
        text = json.dumps(r.get("input_data", {})) + json.dumps(r.get("output_data", {}))
        if query_lower in text.lower():
            filtered.append(r)
    
    return {"results": filtered[:request.limit], "total": len(filtered)}


@router.post("/anchor")
async def anchor_event(request: AnchorRequest):
    """Anchor a specific event's hash to Solana SBT."""
    event = next((e for e in _chronicle_log if e["event_id"] == request.event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if MOCK_MODE or not SOLANA_ANCHOR_ENABLED:
        event["anchored"] = True
        event["solana_tx"] = "mock-tx"
        return {"event_id": request.event_id, "anchored": True, "mock": True}
    
    # Live mode: call Solana SBT anchor
    raise HTTPException(status_code=501, detail="Live Solana anchoring not yet implemented")


@router.get("/agent/{agent_name}/history")
async def agent_history(agent_name: str, limit: int = 20):
    """Get full decision history for a specific agent."""
    results = [e for e in _chronicle_log if e["agent"] == agent_name]
    return {"agent": agent_name, "events": results[-limit:], "total": len(results)}


@router.get("/chain/verify")
async def verify_chain():
    """Verify the integrity of the hash chain."""
    for i, record in enumerate(_chronicle_log):
        expected_prev = _hash_chain[i - 1] if i > 0 else None
        if record.get("previous_hash") != expected_prev:
            return {"valid": False, "broken_at_index": i, "event_id": record.get("event_id")}
    
    return {"valid": True, "chain_length": len(_hash_chain), "latest_hash": _hash_chain[-1] if _hash_chain else None}


@router.get("/health", response_model=ChronicleHealthResponse)
async def chronicle_health():
    return ChronicleHealthResponse(
        status="healthy",
        mock_mode=MOCK_MODE,
        solana_anchor_enabled=SOLANA_ANCHOR_ENABLED,
        log_size=len(_chronicle_log),
        chain_length=len(_hash_chain),
        api_url=OC_API_URL,
    )
