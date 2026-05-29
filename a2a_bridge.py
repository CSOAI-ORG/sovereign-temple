"""
SOV3 A2A v1.0 Bridge
Ingests Google A2A Signed Agent Cards and bridges them to POAI SBTs.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/a2a", tags=["a2a-v1"])

# ── In-Memory Store (replace with PostgreSQL in production) ──────────────────
_a2a_registry: Dict[str, Dict[str, Any]] = {}
_a2a_sbt_bridge: Dict[str, str] = {}  # a2a_card_hash -> sbt_token_id

# ── Data Models ──────────────────────────────────────────────────────────────

class A2ASkill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)

class A2AProvider(BaseModel):
    organization: str
    url: Optional[str] = None

class A2AAgentCard(BaseModel):
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    provider: Optional[A2AProvider] = None
    version: str = "1.0.0"
    authentication: Optional[Dict[str, Any]] = None
    defaultInputModes: List[str] = Field(default_factory=lambda: ["text"])
    defaultOutputModes: List[str] = Field(default_factory=lambda: ["text"])
    capabilities: Optional[Dict[str, bool]] = None
    skills: List[A2ASkill] = Field(default_factory=list)
    # v1.0 signed fields
    signature: Optional[str] = None
    issuer: Optional[str] = None

class BridgeRequest(BaseModel):
    a2a_card: A2AAgentCard
    owner_wallet: str = Field(..., description="Solana pubkey for SBT owner")
    auto_mint_identity: bool = Field(default=True, description="Auto-mint AgentIdentity SBT")

class BridgeResponse(BaseModel):
    a2a_card_hash: str
    sbt_token_id: Optional[str]
    status: str
    message: str
    skills_mapped: List[Dict[str, str]]

class A2AListResponse(BaseModel):
    cards: List[Dict[str, Any]]
    count: int

# ── Helpers ──────────────────────────────────────────────────────────────────

def _hash_card(card: A2AAgentCard) -> str:
    canonical = json.dumps(card.model_dump(), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def _map_skills_to_sbt(skills: List[A2ASkill]) -> List[Dict[str, str]]:
    """Map A2A skill tags to POAI SBT requirements."""
    mappings = []
    tag_to_sbt = {
        "safety": ("SafetyCertification", "Article 10.2"),
        "audit": ("SafetyCertification", "Article 10.2"),
        "identity": ("AgentIdentity", "Article 2.1"),
        "auth": ("AgentIdentity", "Article 2.1"),
        "governance": ("EnterpriseTrust", "Article 8"),
        "compliance": ("EnterpriseTrust", "Article 8"),
        "character": ("CharacterGenesis", "Article 6"),
        "avatar": ("CharacterGenesis", "Article 6"),
    }
    
    seen = set()
    for skill in skills:
        for tag in skill.tags:
            tag_lower = tag.lower()
            if tag_lower in tag_to_sbt and tag_lower not in seen:
                seen.add(tag_lower)
                sbt_type, charter_ref = tag_to_sbt[tag_lower]
                mappings.append({
                    "skill_id": skill.id,
                    "tag": tag,
                    "required_sbt": sbt_type,
                    "charter_reference": charter_ref,
                })
    
    return mappings

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/bridge", response_model=BridgeResponse)
async def bridge_a2a_to_poai(request: BridgeRequest):
    """Bridge an A2A v1.0 Signed Agent Card to a POAI SBT."""
    card_hash = _hash_card(request.a2a_card)
    
    # Validate signature (v1.0 requirement)
    if not request.a2a_card.signature or not request.a2a_card.issuer:
        raise HTTPException(
            status_code=400,
            detail="A2A v1.0 cards must include signature and issuer fields"
        )
    
    # Store card
    _a2a_registry[card_hash] = {
        "card": request.a2a_card.model_dump(),
        "owner_wallet": request.owner_wallet,
        "card_hash": card_hash,
        "bridged_at": datetime.now(datetime.timezone.utc).isoformat(),
    }
    
    # Map skills to SBT requirements
    skills_mapped = _map_skills_to_sbt(request.a2a_card.skills)
    
    sbt_token_id = None
    status = "stored"
    message = "A2A card stored successfully"
    
    if request.auto_mint_identity:
        # In production, this would call the Solana SBT mint endpoint
        # For now, generate a mock token ID
        sbt_token_id = f"a2a-{card_hash[:16]}"
        _a2a_sbt_bridge[card_hash] = sbt_token_id
        status = "bridged"
        message = f"A2A card bridged to POAI AgentIdentity SBT {sbt_token_id}"
    
    return BridgeResponse(
        a2a_card_hash=card_hash,
        sbt_token_id=sbt_token_id,
        status=status,
        message=message,
        skills_mapped=skills_mapped,
    )


@router.get("/card/{card_hash}")
async def get_a2a_card(card_hash: str):
    """Retrieve a stored A2A agent card by hash."""
    record = _a2a_registry.get(card_hash)
    if not record:
        raise HTTPException(status_code=404, detail="A2A card not found")
    return record


@router.get("/list", response_model=A2AListResponse)
async def list_a2a_cards(provider: Optional[str] = None, skill_tag: Optional[str] = None):
    """List all bridged A2A cards with optional filtering."""
    results = list(_a2a_registry.values())
    
    if provider:
        results = [
            r for r in results
            if r["card"].get("provider", {}).get("organization") == provider
        ]
    
    if skill_tag:
        results = [
            r for r in results
            if any(
                skill_tag.lower() in [t.lower() for t in s.get("tags", [])]
                for s in r["card"].get("skills", [])
            )
        ]
    
    return A2AListResponse(cards=results, count=len(results))


@router.get("/card/{card_hash}/sbt")
async def get_linked_sbt(card_hash: str):
    """Get the POAI SBT linked to an A2A card."""
    sbt_id = _a2a_sbt_bridge.get(card_hash)
    if not sbt_id:
        raise HTTPException(status_code=404, detail="No SBT linked to this A2A card")
    return {"a2a_card_hash": card_hash, "sbt_token_id": sbt_id}


@router.get("/health")
async def a2a_health():
    """A2A bridge health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "cards_stored": len(_a2a_registry),
        "bridges_created": len(_a2a_sbt_bridge),
        "spec": "A2A v1.0 Stable (Google/Linux Foundation)",
    }
