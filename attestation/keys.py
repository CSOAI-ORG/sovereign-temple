"""Ed25519 key management with JWKS support for the SOV3 attestation system."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


def generate_signing_key() -> Ed25519PrivateKey:
    """Generate a new Ed25519 private key.

    Returns:
        A freshly generated Ed25519 private key.
    """
    return Ed25519PrivateKey.generate()


def load_key_from_file(path: str | Path) -> Ed25519PrivateKey:
    """Load an Ed25519 private key from a PEM-encoded file.

    Args:
        path: Filesystem path to the PEM private key.

    Returns:
        The loaded Ed25519 private key.

    Raises:
        FileNotFoundError: If the key file does not exist.
        ValueError: If the file cannot be parsed as an Ed25519 private key.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Key file not found: {path}")

    data = path.read_bytes()
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except Exception as exc:
        raise ValueError(f"Failed to parse private key from {path}: {exc}") from exc

    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(f"Key in {path} is not an Ed25519 private key")

    logger.info("Loaded Ed25519 private key from %s", path)
    return key


def load_key_from_env(var_name: str = "SOV3_ATTESTATION_PRIVATE_KEY") -> Ed25519PrivateKey:
    """Load an Ed25519 private key from an environment variable.

    The environment variable may contain either:
      - A PEM-encoded private key (with newlines replaced by ``\\n``)
      - A raw base64-encoded 32-byte seed

    Args:
        var_name: Name of the environment variable.

    Returns:
        The loaded Ed25519 private key.

    Raises:
        KeyError: If the environment variable is not set.
        ValueError: If the value cannot be decoded as a key.
    """
    raw = os.getenv(var_name)
    if raw is None:
        raise KeyError(f"Environment variable {var_name} is not set")

    # Try PEM first (commonly stored with literal \n in env vars)
    if "BEGIN PRIVATE KEY" in raw or "BEGIN OPENSSH PRIVATE KEY" in raw:
        pem_data = raw.replace("\\n", "\n").encode()
        try:
            key = serialization.load_pem_private_key(pem_data, password=None)
        except Exception as exc:
            raise ValueError(f"Failed to parse PEM key from {var_name}: {exc}") from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError(f"Key in {var_name} is not Ed25519")
        logger.info("Loaded Ed25519 private key from env var %s (PEM)", var_name)
        return key

    # Otherwise, treat as base64-encoded raw seed
    try:
        seed = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError(f"Failed to base64-decode key from {var_name}: {exc}") from exc

    if len(seed) != 32:
        raise ValueError(f"Ed25519 seed must be 32 bytes, got {len(seed)}")

    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey as Ed25519PrivateKeyImpl,
    )

    key = Ed25519PrivateKeyImpl.from_private_bytes(seed)
    logger.info("Loaded Ed25519 private key from env var %s (raw seed)", var_name)
    return key


def load_or_generate_key(
    env_var: str = "SOV3_ATTESTATION_PRIVATE_KEY",
    file_path: str | Path | None = None,
    generate_fallback: bool = True,
) -> Ed25519PrivateKey:
    """Load a key from env or file, or generate a new one as fallback.

    Args:
        env_var: Environment variable name to check first.
        file_path: Optional file path to check second.
        generate_fallback: If True, generate a new key when no source is found.

    Returns:
        An Ed25519 private key.

    Raises:
        KeyError: If no key source is available and generate_fallback is False.
    """
    try:
        return load_key_from_env(env_var)
    except KeyError:
        pass

    if file_path is not None:
        try:
            return load_key_from_file(file_path)
        except FileNotFoundError:
            pass

    if generate_fallback:
        logger.warning("No key source found; generating a transient Ed25519 key")
        return generate_signing_key()

    raise KeyError(f"No key found in env {env_var} or file {file_path}")


def public_key_to_jwk(public_key: Ed25519PublicKey) -> dict[str, Any]:
    """Convert an Ed25519 public key to a JWK (JSON Web Key) dictionary.

    Args:
        public_key: The public key to encode.

    Returns:
        A JWK dictionary conforming to RFC 8037.
    """
    raw_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x = base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": x,
        "use": "sig",
        "alg": "EdDSA",
    }


def private_key_to_jwk(private_key: Ed25519PrivateKey) -> dict[str, Any]:
    """Convert an Ed25519 private key to a JWK dictionary (includes public components).

    .. warning::
        The resulting JWK contains the private key material. Handle with care.

    Args:
        private_key: The private key to encode.

    Returns:
        A JWK dictionary conforming to RFC 8037.
    """
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    d = base64.urlsafe_b64encode(private_bytes).rstrip(b"=").decode("ascii")
    x = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": x,
        "d": d,
        "use": "sig",
        "alg": "EdDSA",
    }


def jwk_to_public_key(jwk: dict[str, Any]) -> Ed25519PublicKey:
    """Parse an Ed25519 public key from a JWK dictionary.

    Args:
        jwk: A JWK dictionary containing 'kty': 'OKP' and 'crv': 'Ed25519'.

    Returns:
        The reconstructed Ed25519 public key.

    Raises:
        ValueError: If the JWK is malformed or not an Ed25519 key.
    """
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise ValueError("JWK does not represent an Ed25519 key")

    x_b64 = jwk.get("x")
    if not x_b64:
        raise ValueError("JWK missing 'x' coordinate")

    # Pad base64url if needed
    padding = 4 - len(x_b64) % 4
    if padding != 4:
        x_b64 += "=" * padding

    try:
        raw = base64.urlsafe_b64decode(x_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 in JWK 'x': {exc}") from exc

    if len(raw) != 32:
        raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(raw)}")

    return Ed25519PublicKey.from_public_bytes(raw)


def build_jwks(private_key: Ed25519PrivateKey, key_id: str | None = None) -> dict[str, Any]:
    """Build a JWKS (JSON Web Key Set) containing the public key.

    Args:
        private_key: The private key whose public component will be published.
        key_id: Optional Key ID ('kid') to include in the JWK.

    Returns:
        A JWKS dictionary suitable for a ``.well-known/jwks.json`` endpoint.
    """
    jwk = public_key_to_jwk(private_key.public_key())
    if key_id:
        jwk["kid"] = key_id
    return {"keys": [jwk]}
