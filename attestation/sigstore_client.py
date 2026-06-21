"""Sigstore Rekor and Fulcio integration for SOV3 attestations.

This module provides a lightweight HTTP client for submitting signed
attestations to the Sigstore transparency log (Rekor) and for
obtaining short-lived signing certificates from Fulcio.

References:
    - Rekor API: https://rekor.sigstore.dev/swagger/index.html
    - Fulcio API: https://fulcio.sigstore.dev/swagger/index.html
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

logger = logging.getLogger(__name__)

PUBLIC_REKOR_URL = "https://rekor.sigstore.dev"
PUBLIC_FULCIO_URL = "https://fulcio.sigstore.dev"


class SigstoreClientError(Exception):
    """Raised when a Sigstore API call fails."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SigstoreClient:
    """Async client for Sigstore Rekor and Fulcio.

    Args:
        rekor_url: Base URL of the Rekor instance.
        fulcio_url: Base URL of the Fulcio instance.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        rekor_url: str = PUBLIC_REKOR_URL,
        fulcio_url: str = PUBLIC_FULCIO_URL,
        timeout: float = 30.0,
    ) -> None:
        self.rekor_url = rekor_url.rstrip("/")
        self.fulcio_url = fulcio_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Rekor — Transparency Log
    # ------------------------------------------------------------------

    async def submit_hashedrekord(
        self,
        signature_b64: str,
        sha256_digest: bytes,
        public_key: Ed25519PublicKey,
        data_content_type: str = "application/json",
    ) -> dict[str, Any]:
        """Submit a hashedrekord entry to Rekor.

        Args:
            signature_b64: Base64-encoded Ed25519 signature.
            sha256_digest: 32-byte SHA-256 digest of the canonical payload.
            public_key: The Ed25519 public key that produced the signature.
            data_content_type: MIME type of the original data.

        Returns:
            The Rekor log entry response as a dictionary.

        Raises:
            SigstoreClientError: If the Rekor API returns an error.
        """
        # Encode public key as PEM for Rekor
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        # Base64-encode the signature for the JSON payload
        signature_bytes = base64.b64decode(signature_b64, validate=True)
        signature_b64url = base64.b64encode(signature_bytes).decode("ascii")

        entry = {
            "kind": "hashedrekord",
            "apiVersion": "0.0.1",
            "spec": {
                "data": {
                    "hash": {"algorithm": "sha256", "value": sha256_digest.hex()},
                    "content": "",
                },
                "signature": {
                    "content": signature_b64url,
                    "publicKey": {"content": base64.b64encode(public_key_pem.encode()).decode("ascii")},
                },
            },
        }

        url = f"{self.rekor_url}/api/v1/log/entries"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.post(url, json=entry)

        if response.status_code not in (200, 201, 202):
            raise SigstoreClientError(
                f"Rekor submission failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        body = response.json()
        logger.info("Submitted attestation to Rekor: %s", body)
        return body

    async def verify_rekor_entry_by_index(
        self,
        log_index: int,
    ) -> dict[str, Any]:
        """Retrieve and verify a Rekor entry by its log index.

        Args:
            log_index: The Rekor log index to query.

        Returns:
            The Rekor entry JSON.

        Raises:
            SigstoreClientError: If the entry is not found or the API errors.
        """
        url = f"{self.rekor_url}/api/v1/log/entries"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, params={"logIndex": log_index})

        if response.status_code == 404:
            raise SigstoreClientError(
                f"Rekor entry not found for logIndex={log_index}",
                status_code=404,
            )
        if response.status_code != 200:
            raise SigstoreClientError(
                f"Rekor query failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        return response.json()

    async def verify_rekor_entry_by_uuid(
        self,
        entry_uuid: str,
    ) -> dict[str, Any]:
        """Retrieve a Rekor entry by its UUID.

        Args:
            entry_uuid: The Rekor entry UUID.

        Returns:
            The Rekor entry JSON.

        Raises:
            SigstoreClientError: If the entry is not found.
        """
        url = f"{self.rekor_url}/api/v1/log/entries/{entry_uuid}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url)

        if response.status_code == 404:
            raise SigstoreClientError(
                f"Rekor entry not found for UUID={entry_uuid}",
                status_code=404,
            )
        if response.status_code != 200:
            raise SigstoreClientError(
                f"Rekor query failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        return response.json()

    async def get_rekor_log_info(self) -> dict[str, Any]:
        """Fetch Rekor log metadata (tree size, signed tree head, etc.).

        Returns:
            Log information dictionary.
        """
        url = f"{self.rekor_url}/api/v1/log"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url)

        if response.status_code != 200:
            raise SigstoreClientError(
                f"Rekor log info query failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        return response.json()

    # ------------------------------------------------------------------
    # Fulcio — Certificate Authority
    # ------------------------------------------------------------------

    async def request_fulcio_certificate(
        self,
        identity_token: str,
        public_key: Ed25519PublicKey,
        challenge_signature: bytes | None = None,
    ) -> list[str]:
        """Request a code-signing certificate from Fulcio.

        Fulcio issues short-lived certificates bound to an OIDC identity.
        The caller must provide a valid OIDC bearer token (e.g., from
        GitHub Actions, Google, or Microsoft identity providers).

        Args:
            identity_token: OIDC bearer token (JWT).
            public_key: The Ed25519 public key to be certified.
            challenge_signature: Optional proof-of-possession signature
                over the OIDC token subject or a Fulcio-provided challenge.

        Returns:
            A list of PEM-encoded certificates (leaf first, then chain).

        Raises:
            SigstoreClientError: If Fulcio refuses the request.
        """
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        payload: dict[str, Any] = {
            "publicKey": {"content": public_key_pem},
            "signedEmailAddress": (
                base64.b64encode(challenge_signature).decode("ascii")
                if challenge_signature
                else ""
            ),
        }

        url = f"{self.fulcio_url}/api/v1/signingCert"
        headers = {
            "Authorization": f"Bearer {identity_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code not in (200, 201):
            raise SigstoreClientError(
                f"Fulcio certificate request failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        # Fulcio returns certificates as a concatenated PEM string
        pem_chain = response.text
        certs = [
            cert.strip()
            for cert in pem_chain.split("-----END CERTIFICATE-----")
            if cert.strip()
        ]
        # Re-append the END marker that split removed
        certs = [
            f"{cert}\n-----END CERTIFICATE-----" for cert in certs
        ]

        logger.info("Received %d certificate(s) from Fulcio", len(certs))
        return certs

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def extract_log_index(self, rekor_response: dict[str, Any]) -> int | None:
        """Extract the log index from a Rekor submission response.

        Rekor returns entries keyed by UUID; each value contains ``logIndex``.
        """
        for entry in rekor_response.values():
            if isinstance(entry, dict):
                return entry.get("logIndex")
        return None

    def extract_entry_uuid(self, rekor_response: dict[str, Any]) -> str | None:
        """Extract the entry UUID from a Rekor submission response."""
        for key in rekor_response.keys():
            # Top-level keys are UUIDs
            return key
        return None
