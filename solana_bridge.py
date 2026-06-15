"""
SOV3 Solana SBT Bridge
Connects the Sovereign Temple orchestration layer to the POAI Solana program.

Program ID: Dyd7JtmmuA3RZZupk98mqRQ8uySZV9FwTE6aNYmxPxpo
"""

import os
import struct
import base64
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Solana imports
try:
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.instruction import Instruction, AccountMeta
    from solders.transaction import Transaction
    from solders.system_program import ID as SYSTEM_PROGRAM_ID
    from solders.sysvar import RENT as RENT_SYSVAR
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

router = APIRouter(prefix="/sbt", tags=["solana-sbt"])

# ── Config ───────────────────────────────────────────────────────────────────

PROGRAM_ID_STR = os.environ.get("SBT_PROGRAM_ID", "Dyd7JtmmuA3RZZupk98mqRQ8uySZV9FwTE6aNYmxPxpo")
SOLANA_RPC = os.environ.get("SOLANA_RPC", "https://api.devnet.solana.com")
PAYER_KEYPAIR_PATH = os.environ.get("PAYER_KEYPAIR", os.path.expanduser("~/.config/solana/id.json"))
MOCK_MODE = os.environ.get("SBT_MOCK_MODE", "true").lower() == "true"

PROGRAM_ID = Pubkey.from_string(PROGRAM_ID_STR) if SOLANA_AVAILABLE else None
_sbt_counter = 0
_mock_registry: Dict[str, Dict[str, Any]] = {}

# ── Data Models ──────────────────────────────────────────────────────────────

class SbtType(int):
    AgentIdentity = 0
    SafetyCertification = 1
    VerifierReputation = 2
    CharacterGenesis = 3
    EnterpriseTrust = 4

class MintSbtRequest(BaseModel):
    owner_wallet: str = Field(..., description="Solana pubkey of the SBT owner")
    sbt_type: int = Field(..., ge=0, le=4, description="0=AgentIdentity, 1=SafetyCertification, 2=VerifierReputation, 3=CharacterGenesis, 4=EnterpriseTrust")
    metadata_uri: str = Field(default="", max_length=256)
    charter_reference: str = Field(default="", max_length=64)
    risk_tier: int = Field(default=0, ge=0, le=3)
    expires_at: Optional[int] = Field(default=None, description="Unix timestamp")

class SbtResponse(BaseModel):
    token_id: str
    sbt_type: int
    sbt_type_name: str
    owner: str
    issuer: str
    solana_tx: Optional[str]
    status: str
    mock: bool
    created_at: str

class VerifySbtResponse(BaseModel):
    token_id: str
    verified: bool
    sbt_type: int
    sbt_type_name: str
    owner: str
    issuer: str
    revoked: bool
    risk_tier: int
    charter_reference: str
    metadata_uri: str
    response_time_ms: float

class SbtListResponse(BaseModel):
    sbts: List[Dict[str, Any]]
    count: int

# ── Helpers ──────────────────────────────────────────────────────────────────

_SBT_TYPE_NAMES = {
    0: "AgentIdentity",
    1: "SafetyCertification",
    2: "VerifierReputation",
    3: "CharacterGenesis",
    4: "EnterpriseTrust",
}

def _get_sbt_type_name(t: int) -> str:
    return _SBT_TYPE_NAMES.get(t, "Unknown")

def _derive_pda(owner: str, token_id: int) -> str:
    """Derive a deterministic PDA-like identifier for mock mode."""
    return f"sbt-{owner[:8]}-{token_id}"

# ── Mock Mode ────────────────────────────────────────────────────────────────

def _mint_mock(req: MintSbtRequest) -> SbtResponse:
    global _sbt_counter
    _sbt_counter += 1
    token_id = str(_sbt_counter)
    pda = _derive_pda(req.owner_wallet, _sbt_counter)
    issuer = PAYER_KEYPAIR_PATH if not SOLANA_AVAILABLE else "sov3-orchestrator"
    
    record = {
        "token_id": token_id,
        "pda": pda,
        "sbt_type": req.sbt_type,
        "owner": req.owner_wallet,
        "issuer": str(issuer),
        "metadata_uri": req.metadata_uri,
        "charter_reference": req.charter_reference,
        "risk_tier": req.risk_tier,
        "revoked": False,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": req.expires_at,
        "verification_hours": 0,
    }
    _mock_registry[token_id] = record
    
    return SbtResponse(
        token_id=token_id,
        sbt_type=req.sbt_type,
        sbt_type_name=_get_sbt_type_name(req.sbt_type),
        owner=req.owner_wallet,
        issuer=str(issuer),
        solana_tx=None,
        status="minted",
        mock=True,
        created_at=record["created_at"],
    )

def _verify_mock(token_id: str) -> Optional[Dict[str, Any]]:
    return _mock_registry.get(token_id)

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/health")
async def sbt_health():
    """SBT bridge health check."""
    return {
        "status": "healthy",
        "mock_mode": MOCK_MODE,
        "solana_available": SOLANA_AVAILABLE,
        "program_id": PROGRAM_ID_STR,
        "rpc": SOLANA_RPC,
        "mock_registry_size": len(_mock_registry),
    }


@router.post("/mint", response_model=SbtResponse)
async def mint_sbt(request: MintSbtRequest):
    """Mint a new POAI Soulbound Token on Solana (or mock registry if contract not deployed)."""
    import time
    start = time.time()
    
    if MOCK_MODE or not SOLANA_AVAILABLE:
        return _mint_mock(request)
    
    # Live mode: build and send Solana transaction
    try:
        client = Client(SOLANA_RPC)
        
        # Load payer
        with open(PAYER_KEYPAIR_PATH) as f:
            keypair_data = json.load(f)
        payer = Keypair.from_bytes(bytes(keypair_data))
        
        owner = Pubkey.from_string(request.owner_wallet)
        
        # Derive PDA
        seed = f"sbt-{request.sbt_type}-{int(time.time() * 1000)}".encode()
        pda, bump = Pubkey.find_program_address([seed], PROGRAM_ID)
        
        # Build instruction data (manual borsh)
        # Discriminant: Mint = 0
        # Mint { sbt_type: u8, token_id: u64, metadata_uri: String, charter_reference: String, risk_tier: u8, expires_at: i64 }
        token_id = int(time.time())
        uri_bytes = request.metadata_uri.encode()
        charter_bytes = request.charter_reference.encode()
        
        data = struct.pack("<B", 0)  # Mint discriminant
        data += struct.pack("<B", request.sbt_type)
        data += struct.pack("<Q", token_id)
        data += struct.pack("<I", len(uri_bytes)) + uri_bytes
        data += struct.pack("<I", len(charter_bytes)) + charter_bytes
        data += struct.pack("<B", request.risk_tier)
        data += struct.pack("<q", request.expires_at or 0)
        
        accounts = [
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=RENT_SYSVAR, is_signer=False, is_writable=False),
        ]
        
        ix = Instruction(PROGRAM_ID, data, accounts)
        tx = Transaction().add(ix)
        tx.recent_blockhash = client.get_latest_blockhash().value.blockhash
        tx.sign(payer)
        
        result = client.send_transaction(tx, opts=TxOpts(skip_confirmation=False))
        sig = result.value
        
        return SbtResponse(
            token_id=str(token_id),
            sbt_type=request.sbt_type,
            sbt_type_name=_get_sbt_type_name(request.sbt_type),
            owner=request.owner_wallet,
            issuer=str(payer.pubkey()),
            solana_tx=str(sig),
            status="minted",
            mock=False,
            created_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solana transaction failed: {str(e)}")


@router.get("/verify/{token_id}", response_model=VerifySbtResponse)
async def verify_sbt(token_id: str):
    """Verify a POAI SBT by token ID. Returns YES/NO in <200ms."""
    import time
    start = time.time()
    
    if MOCK_MODE or not SOLANA_AVAILABLE:
        record = _verify_mock(token_id)
        if not record:
            raise HTTPException(status_code=404, detail="SBT not found")
        
        return VerifySbtResponse(
            token_id=token_id,
            verified=not record["revoked"],
            sbt_type=record["sbt_type"],
            sbt_type_name=_get_sbt_type_name(record["sbt_type"]),
            owner=record["owner"],
            issuer=record["issuer"],
            revoked=record["revoked"],
            risk_tier=record["risk_tier"],
            charter_reference=record["charter_reference"],
            metadata_uri=record["metadata_uri"],
            response_time_ms=round((time.time() - start) * 1000, 2),
        )
    
    # Live mode: fetch from Solana
    try:
        client = Client(SOLANA_RPC)
        # In real implementation, derive PDA from token_id and fetch account
        # For now, return placeholder
        raise HTTPException(status_code=501, detail="Live verification not yet implemented — use mock mode")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/{token_id}", response_model=Dict[str, Any])
async def get_sbt(token_id: str):
    """Get full SBT record by token ID."""
    if MOCK_MODE or not SOLANA_AVAILABLE:
        record = _verify_mock(token_id)
        if not record:
            raise HTTPException(status_code=404, detail="SBT not found")
        return record
    
    raise HTTPException(status_code=501, detail="Live fetch not yet implemented")


@router.post("/revoke/{token_id}")
async def revoke_sbt(token_id: str):
    """Revoke an SBT (issuer only)."""
    if MOCK_MODE or not SOLANA_AVAILABLE:
        record = _verify_mock(token_id)
        if not record:
            raise HTTPException(status_code=404, detail="SBT not found")
        record["revoked"] = True
        return {"token_id": token_id, "status": "revoked", "mock": True}
    
    raise HTTPException(status_code=501, detail="Live revoke not yet implemented")


@router.get("/list", response_model=SbtListResponse)
async def list_sbts(sbt_type: Optional[int] = None, owner: Optional[str] = None):
    """List all SBTs with optional filtering."""
    if MOCK_MODE or not SOLANA_AVAILABLE:
        results = list(_mock_registry.values())
        if sbt_type is not None:
            results = [r for r in results if r["sbt_type"] == sbt_type]
        if owner:
            results = [r for r in results if r["owner"] == owner]
        return SbtListResponse(sbts=results, count=len(results))
    
    raise HTTPException(status_code=501, detail="Live list not yet implemented")
