"""
SOV3 Payment Orchestration Bridge
Routes agent payments across Pay.sh (Solana), x402 (Ethereum), and Stripe (fiat).
"""

import os
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

router = APIRouter(prefix="/payments", tags=["payments"])

# ── Config ───────────────────────────────────────────────────────────────────

PAY_SH_API_KEY = os.environ.get("PAY_SH_API_KEY", "")
PAY_SH_API = os.environ.get("PAY_SH_API", "https://api.pay.sh/v1")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
X402_WALLET = os.environ.get("X402_WALLET", "")
MOCK_PAYMENTS = os.environ.get("MOCK_PAYMENTS", "true").lower() == "true"

# ── In-Memory Store ──────────────────────────────────────────────────────────
_payment_sessions: Dict[str, Dict[str, Any]] = {}

# ── Data Models ──────────────────────────────────────────────────────────────

class PaymentCreateRequest(BaseModel):
    agent_id: str = Field(..., description="A2A agent card ID or POAI SBT ID")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USDC", description="USDC, ETH, GBP, USD")
    description: str = Field(default="", max_length=500)
    recipient_wallet: Optional[str] = Field(default=None, description="Solana pubkey for crypto rails")
    recipient_email: Optional[str] = Field(default=None, description="For Stripe fiat")
    rail_preference: Optional[Literal["pay-sh", "x402", "stripe"]] = None
    callback_url: Optional[str] = None

class PaymentResponse(BaseModel):
    session_id: str
    payment_url: Optional[str]
    status: Literal["pending", "completed", "failed"]
    rail: str
    solana_tx: Optional[str]
    stripe_intent_id: Optional[str]
    created_at: str

class PaymentStatusResponse(BaseModel):
    session_id: str
    status: Literal["pending", "completed", "failed"]
    solana_tx: Optional[str]
    stripe_intent_id: Optional[str]
    completed_at: Optional[str]
    response_time_ms: float

class PaymentListResponse(BaseModel):
    sessions: List[Dict[str, Any]]
    count: int

# ── Helpers ──────────────────────────────────────────────────────────────────

def _select_rail(req: PaymentCreateRequest) -> str:
    if req.rail_preference:
        return req.rail_preference
    if req.recipient_wallet:
        return "pay-sh"  # Solana-first
    if req.recipient_email:
        return "stripe"
    return "pay-sh"

def _meok_fee(rail: str) -> float:
    fees = {"pay-sh": 0.025, "x402": 0.025, "stripe": 0.035}
    return fees.get(rail, 0.025)

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create", response_model=PaymentResponse)
async def create_payment(request: PaymentCreateRequest):
    """Create a payment session across Pay.sh, x402, or Stripe."""
    session_id = str(uuid.uuid4())
    rail = _select_rail(request)
    fee = _meok_fee(rail)
    net_amount = request.amount * (1 - fee)
    
    session = {
        "session_id": session_id,
        "agent_id": request.agent_id,
        "amount": request.amount,
        "currency": request.currency,
        "description": request.description,
        "rail": rail,
        "recipient_wallet": request.recipient_wallet,
        "recipient_email": request.recipient_email,
        "fee": fee,
        "net_amount": net_amount,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "solana_tx": None,
        "stripe_intent_id": None,
    }
    _payment_sessions[session_id] = session
    
    if MOCK_PAYMENTS:
        # Simulate async completion after 2 seconds
        # In production, webhook handler updates this
        return PaymentResponse(
            session_id=session_id,
            payment_url=f"https://pay.sh/checkout/{session_id}" if rail == "pay-sh" else None,
            status="pending",
            rail=rail,
            solana_tx=None,
            stripe_intent_id=None,
            created_at=session["created_at"],
        )
    
    # Live mode: call actual payment APIs
    raise HTTPException(status_code=501, detail="Live payments not yet implemented")


@router.get("/{session_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(session_id: str):
    """Check payment session status."""
    start = time.time()
    session = _payment_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Payment session not found")
    
    return PaymentStatusResponse(
        session_id=session_id,
        status=session["status"],
        solana_tx=session.get("solana_tx"),
        stripe_intent_id=session.get("stripe_intent_id"),
        completed_at=session.get("completed_at"),
        response_time_ms=round((time.time() - start) * 1000, 2),
    )


@router.post("/webhook/pay-sh")
async def pay_sh_webhook(payload: Dict[str, Any]):
    """Handle Pay.sh webhook callbacks."""
    session_id = payload.get("session_id")
    status = payload.get("status")
    solana_tx = payload.get("solana_tx")
    
    if session_id not in _payment_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _payment_sessions[session_id]
    session["status"] = status
    if solana_tx:
        session["solana_tx"] = solana_tx
    if status == "completed":
        session["completed_at"] = datetime.utcnow().isoformat()
    
    return {"received": True}


@router.post("/webhook/stripe")
async def stripe_webhook(payload: Dict[str, Any]):
    """Handle Stripe webhook callbacks."""
    # Verify Stripe signature in production
    session_id = payload.get("session_id")
    status = payload.get("status")
    
    if session_id and session_id in _payment_sessions:
        _payment_sessions[session_id]["status"] = status
        if status == "completed":
            _payment_sessions[session_id]["completed_at"] = datetime.utcnow().isoformat()
    
    return {"received": True}


@router.get("/list")
async def list_payments(agent_id: Optional[str] = None, rail: Optional[str] = None):
    """List payment sessions with optional filtering."""
    results = list(_payment_sessions.values())
    if agent_id:
        results = [r for r in results if r["agent_id"] == agent_id]
    if rail:
        results = [r for r in results if r["rail"] == rail]
    return PaymentListResponse(sessions=results, count=len(results))


@router.get("/health")
async def payments_health():
    """Payment bridge health check."""
    return {
        "status": "healthy",
        "mock_mode": MOCK_PAYMENTS,
        "rails": ["pay-sh", "x402", "stripe"],
        "primary_rail": "pay-sh",
        "sessions_count": len(_payment_sessions),
        "pay_sh_configured": bool(PAY_SH_API_KEY),
        "stripe_configured": bool(STRIPE_SECRET_KEY),
    }
