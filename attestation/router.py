"""FastAPI router for SOV3 attestation endpoints.

Routes:
    POST /attestation/sign      — Sign an attestation payload.
    POST /attestation/verify    — Verify an attestation signature.
    GET  /attestation/.well-known/jwks.json — Public key discovery.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status

from .keys import build_jwks, load_or_generate_key
from .schemas import (
    AttestationPayload,
    JWKSResponse,
    SignRequest,
    SignResponse,
    VerifyRequest,
    VerifyResponse,
)
from .signer import AttestationSigner
from .sigstore_client import SigstoreClient, SigstoreClientError
from .verifier import AttestationVerifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_attestation_router(
    private_key: Any | None = None,
    max_age_hours: int = 24,
    rekor_url: str | None = None,
    fulcio_url: str | None = None,
    key_id: str | None = None,
    submit_to_rekor_on_sign: bool = False,
) -> APIRouter:
    """Create and configure the attestation FastAPI router.

    Args:
        private_key: An Ed25519 private key. If None, one is loaded/generated.
        max_age_hours: Maximum attestation age for verification.
        rekor_url: URL of the Rekor instance (defaults to public Rekor).
        fulcio_url: URL of the Fulcio instance (defaults to public Fulcio).
        key_id: Optional ``kid`` for the JWKS endpoint.
        submit_to_rekor_on_sign: Whether to auto-submit every signed attestation
            to Rekor. Defaults to False to avoid external dependency surprises.

    Returns:
        Configured FastAPI APIRouter.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if private_key is None:
        private_key = load_or_generate_key(
            env_var="SOV3_ATTESTATION_PRIVATE_KEY",
            file_path=os.getenv("SOV3_ATTESTATION_KEY_FILE"),
            generate_fallback=True,
        )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private_key must be an Ed25519PrivateKey instance")

    signer = AttestationSigner(private_key)
    verifier = AttestationVerifier(
        default_public_key=private_key.public_key(),
        max_age_hours=max_age_hours,
    )
    sigstore = SigstoreClient(
        rekor_url=rekor_url or os.getenv("SIGSTORE_REKOR_URL", "https://rekor.sigstore.dev"),
        fulcio_url=fulcio_url or os.getenv("SIGSTORE_FULCIO_URL", "https://fulcio.sigstore.dev"),
    )

    router = APIRouter(prefix="/attestation", tags=["Attestation"])

    # ------------------------------------------------------------------
    # POST /attestation/sign
    # ------------------------------------------------------------------
    @router.post(
        "/sign",
        response_model=SignResponse,
        status_code=status.HTTP_200_OK,
        summary="Sign an attestation payload",
        description="Canonicalizes the payload and produces an Ed25519 signature.",
    )
    async def sign_attestation(request: SignRequest) -> SignResponse:
        signature = signer.sign(request.payload)
        rekor_log_index: int | None = None

        if submit_to_rekor_on_sign:
            try:
                payload_hash = signer.hash_payload(request.payload)
                rekor_resp = await sigstore.submit_hashedrekord(
                    signature_b64=signature,
                    sha256_digest=payload_hash,
                    public_key=signer.public_key,
                )
                rekor_log_index = sigstore.extract_log_index(rekor_resp)
                logger.info(
                    "Auto-submitted attestation to Rekor (logIndex=%s)",
                    rekor_log_index,
                )
            except SigstoreClientError as exc:
                logger.warning("Rekor submission failed (non-fatal): %s", exc)
            except Exception as exc:
                logger.warning("Unexpected Rekor error (non-fatal): %s", exc)

        return signer.sign_with_metadata(
            payload=request.payload,
            include_jwk=True,
            rekor_log_index=rekor_log_index,
        )

    # ------------------------------------------------------------------
    # POST /attestation/verify
    # ------------------------------------------------------------------
    @router.post(
        "/verify",
        response_model=VerifyResponse,
        status_code=status.HTTP_200_OK,
        summary="Verify an attestation signature",
        description="Validates Ed25519 signature, timestamp freshness, and optional Rekor entry.",
    )
    async def verify_attestation(request: VerifyRequest) -> VerifyResponse:
        rekor_verified: bool | None = None

        if request.check_rekor:
            # If the client wants Rekor verification but didn't supply a log index,
            # we cannot verify. In a real flow the client would include the index
            # or UUID in the request. Here we gracefully skip.
            # TODO: extend VerifyRequest to accept rekor_log_index or uuid.
            logger.info("Rekor verification requested but no log index provided; skipping")
            rekor_verified = None

        return verifier.verify_full(
            payload=request.payload,
            signature_b64=request.signature,
            public_key_jwk=request.public_key_jwk,
            check_rekor=request.check_rekor,
            rekor_verified=rekor_verified,
        )

    # ------------------------------------------------------------------
    # GET /attestation/.well-known/jwks.json
    # ------------------------------------------------------------------
    @router.get(
        "/.well-known/jwks.json",
        response_model=JWKSResponse,
        summary="JWKS public key discovery",
        description="Returns the Ed25519 public key as a JWKS (RFC 7517).",
    )
    async def jwks_endpoint() -> JWKSResponse:
        jwks = build_jwks(private_key, key_id=key_id)
        return JWKSResponse(**jwks)

    return router
