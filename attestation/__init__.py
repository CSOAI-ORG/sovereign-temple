"""SOV3 Ed25519 Cryptographic Attestation Module.

Provides key management, signing, verification, Sigstore transparency-log
integration, and a FastAPI router for the Sovereign Temple attestation API.

Example::

    from attestation import create_attestation_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(create_attestation_router())
"""

from __future__ import annotations

from .keys import (
    build_jwks,
    generate_signing_key,
    jwk_to_public_key,
    load_key_from_env,
    load_key_from_file,
    load_or_generate_key,
    private_key_to_jwk,
    public_key_to_jwk,
)
from .router import create_attestation_router
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

__all__ = [
    "AttestationPayload",
    "AttestationSigner",
    "AttestationVerifier",
    "build_jwks",
    "create_attestation_router",
    "generate_signing_key",
    "jwk_to_public_key",
    "JWKSResponse",
    "load_key_from_env",
    "load_key_from_file",
    "load_or_generate_key",
    "private_key_to_jwk",
    "public_key_to_jwk",
    "SignRequest",
    "SignResponse",
    "SigstoreClient",
    "SigstoreClientError",
    "VerifyRequest",
    "VerifyResponse",
]
