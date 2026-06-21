"""Ed25519 attestation verifier with timestamp freshness and Rekor support."""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .keys import jwk_to_public_key
from .schemas import AttestationPayload, VerifyResponse

logger = logging.getLogger(__name__)

DEFAULT_MAX_AGE_HOURS = 24


class AttestationVerifier:
    """Verifies Ed25519 attestation signatures and their freshness.

    Attributes:
        default_public_key: Optional default public key used when a JWK is not
            explicitly provided in a verify call.
        max_age_hours: Maximum age of an attestation before it is considered stale.
    """

    def __init__(
        self,
        default_public_key: Ed25519PublicKey | None = None,
        max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    ) -> None:
        """Initialize the verifier.

        Args:
            default_public_key: Public key to use when none is supplied.
            max_age_hours: Reject attestations older than this many hours.
        """
        self.default_public_key = default_public_key
        self.max_age_hours = max_age_hours

    def verify(
        self,
        payload: AttestationPayload,
        signature_b64: str,
        public_key: Ed25519PublicKey | None = None,
    ) -> bool:
        """Verify an Ed25519 signature over a canonicalized payload.

        Args:
            payload: The attestation payload that was signed.
            signature_b64: Base64-encoded signature.
            public_key: Public key to verify with; falls back to ``default_public_key``.

        Returns:
            True if the signature is valid.

        Raises:
            ValueError: If no public key is available.
        """
        key = public_key or self.default_public_key
        if key is None:
            raise ValueError("No public key provided and no default key configured")

        message = payload.canonical_json().encode("utf-8")
        try:
            signature = base64.b64decode(signature_b64, validate=True)
        except Exception as exc:
            logger.warning("Invalid base64 signature: %s", exc)
            return False

        try:
            key.verify(signature, message)
            logger.debug("Signature valid for session %s", payload.session_id)
            return True
        except InvalidSignature:
            logger.warning("Invalid signature for session %s", payload.session_id)
            return False

    def check_timestamp_freshness(self, timestamp: datetime) -> bool:
        """Check whether a timestamp is within the allowed freshness window.

        Args:
            timestamp: The attestation timestamp (must be timezone-aware).

        Returns:
            True if the timestamp is not older than ``max_age_hours``.
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.max_age_hours)
        fresh = timestamp >= cutoff
        if not fresh:
            logger.warning(
                "Attestation timestamp %s is older than %s hours",
                timestamp.isoformat(),
                self.max_age_hours,
            )
        return fresh

    def verify_full(
        self,
        payload: AttestationPayload,
        signature_b64: str,
        public_key_jwk: dict[str, Any] | None = None,
        check_rekor: bool = False,
        rekor_verified: bool | None = None,
    ) -> VerifyResponse:
        """Perform full verification: signature, freshness, and optional Rekor.

        Args:
            payload: The attestation payload.
            signature_b64: Base64-encoded signature.
            public_key_jwk: JWK dict for the public key (optional if default is set).
            check_rekor: Whether Rekor verification was requested.
            rekor_verified: Result of Rekor verification, if performed.

        Returns:
            A VerifyResponse with the outcome of each check.
        """
        public_key: Ed25519PublicKey | None = None
        if public_key_jwk is not None:
            try:
                public_key = jwk_to_public_key(public_key_jwk)
            except ValueError as exc:
                return VerifyResponse(
                    valid=False,
                    timestamp_fresh=None,
                    rekor_verified=None,
                    message=f"Invalid public key JWK: {exc}",
                )

        try:
            sig_valid = self.verify(payload, signature_b64, public_key)
        except ValueError as exc:
            return VerifyResponse(
                valid=False,
                timestamp_fresh=None,
                rekor_verified=None,
                message=str(exc),
            )

        if not sig_valid:
            return VerifyResponse(
                valid=False,
                timestamp_fresh=None,
                rekor_verified=None,
                message="Signature verification failed",
            )

        fresh = self.check_timestamp_freshness(payload.timestamp)
        if not fresh:
            return VerifyResponse(
                valid=False,
                timestamp_fresh=False,
                rekor_verified=None,
                message=f"Attestation older than {self.max_age_hours} hours",
            )

        if check_rekor and rekor_verified is not None and not rekor_verified:
            return VerifyResponse(
                valid=False,
                timestamp_fresh=True,
                rekor_verified=False,
                message="Rekor transparency log verification failed",
            )

        return VerifyResponse(
            valid=True,
            timestamp_fresh=True,
            rekor_verified=rekor_verified if check_rekor else None,
            message="Attestation is valid",
        )
