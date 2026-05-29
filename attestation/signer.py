"""Ed25519 attestation signer for SOV3 session payloads."""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .keys import public_key_to_jwk
from .schemas import AttestationPayload, SignResponse

logger = logging.getLogger(__name__)


class AttestationSigner:
    """Signs attestation payloads using Ed25519.

    The signer canonicalizes each payload to deterministic JSON
    (sorted keys, no extraneous whitespace) before signing.
    """

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        """Initialize with a private signing key.

        Args:
            private_key: The Ed25519 key used to produce signatures.
        """
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @property
    def public_key(self) -> Ed25519PrivateKey:
        """The signer's public key."""
        return self._public_key

    def sign(self, payload: AttestationPayload) -> str:
        """Sign an attestation payload and return a base64-encoded signature.

        Args:
            payload: The attestation payload to sign.

        Returns:
            Base64-encoded Ed25519 signature.
        """
        message = payload.canonical_json().encode("utf-8")
        signature = self._private_key.sign(message)
        encoded = base64.b64encode(signature).decode("ascii")
        logger.debug(
            "Signed attestation session=%s sig_prefix=%s...",
            payload.session_id,
            encoded[:16],
        )
        return encoded

    def sign_with_metadata(
        self,
        payload: AttestationPayload,
        include_jwk: bool = True,
        rekor_log_index: int | None = None,
    ) -> SignResponse:
        """Sign a payload and return a structured response.

        Args:
            payload: The attestation payload to sign.
            include_jwk: Whether to include the public key JWK in the response.
            rekor_log_index: Optional Rekor transparency log index.

        Returns:
            A SignResponse containing the signature and metadata.
        """
        signature = self.sign(payload)
        jwk: dict[str, Any] | None = None
        if include_jwk:
            jwk = public_key_to_jwk(self._public_key)
        return SignResponse(
            signature=signature,
            public_key_jwk=jwk,
            rekor_log_index=rekor_log_index,
        )

    @staticmethod
    def hash_payload(payload: AttestationPayload) -> bytes:
        """Compute the SHA-256 digest of the canonical payload.

        This is useful for Sigstore Rekor ``hashedrekord`` entries.

        Args:
            payload: The attestation payload.

        Returns:
            32-byte SHA-256 digest.
        """
        message = payload.canonical_json().encode("utf-8")
        return hashlib.sha256(message).digest()
