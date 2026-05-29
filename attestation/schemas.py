"""Pydantic schemas for SOV3 attestation payloads and API responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AttestationPayload(BaseModel):
    """Schema for an attestation payload to be signed.

    Attributes:
        session_id: Unique identifier for the agent session.
        timestamp: UTC ISO-8601 timestamp of attestation creation.
        models_used: LLM model identifiers invoked during the session.
        bft_votes: Number of BFT (Byzantine Fault Tolerance) votes cast.
        bft_consensus_rate: Consensus ratio achieved (0.0–1.0).
        tools_called: Names of tools executed during the session.
        files_modified: File paths modified by the session.
        companion_level: Companion classification tier (e.g., "core", "elite").
    """

    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of attestation",
    )
    models_used: list[str] = Field(default_factory=list, description="Models invoked")
    bft_votes: int = Field(default=0, ge=0, description="BFT vote count")
    bft_consensus_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="BFT consensus rate")
    tools_called: list[str] = Field(default_factory=list, description="Tools executed")
    files_modified: list[str] = Field(default_factory=list, description="Files modified")
    companion_level: str = Field(default="core", description="Companion tier level")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_utc(cls, value: Any) -> datetime:
        if isinstance(value, str):
            # Pydantic v2 handles ISO strings automatically, but we ensure tz aware
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def canonical_json(self) -> str:
        """Return a deterministic JSON representation for signing.

        Keys are sorted and whitespace is minimized to ensure
        signature stability across serializations.
        """
        import json
        return json.dumps(
            self.model_dump(by_alias=True, exclude_none=True),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )


class SignRequest(BaseModel):
    """Request body for the /attestation/sign endpoint."""

    payload: AttestationPayload


class SignResponse(BaseModel):
    """Response body for the /attestation/sign endpoint."""

    signature: str = Field(..., description="Base64-encoded Ed25519 signature")
    public_key_jwk: dict[str, Any] | None = Field(
        None, description="Public key in JWK format"
    )
    rekor_log_index: int | None = Field(
        None, description="Rekor transparency log index, if submitted"
    )


class VerifyRequest(BaseModel):
    """Request body for the /attestation/verify endpoint."""

    payload: AttestationPayload
    signature: str = Field(..., description="Base64-encoded Ed25519 signature")
    public_key_jwk: dict[str, Any] | None = Field(
        None, description="Public key in JWK format (optional if system key is configured)"
    )
    check_rekor: bool = Field(default=False, description="Verify presence in Rekor log")


class VerifyResponse(BaseModel):
    """Response body for the /attestation/verify endpoint."""

    valid: bool
    timestamp_fresh: bool | None = None
    rekor_verified: bool | None = None
    message: str | None = None


class JWKSResponse(BaseModel):
    """Response body for the JWKS discovery endpoint."""

    keys: list[dict[str, Any]]
