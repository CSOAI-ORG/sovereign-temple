"""
sigil_ed25519.py — external-grade signing for the SIGIL bus (task #43, the moat upgrade).

HMAC proves "I didn't tamper" but only the key-holder can check it. Ed25519 is asymmetric:
we sign with a PRIVATE key, publish the PUBLIC key, and ANYONE can verify a SIGIL record
without our secret. That's the honest "third-party-verifiable agent communication" claim.

Keys live in data/ (private key gitignored, 0600). Public key is publishable.
Drop-in: sigil_bus uses get_signer() as its `signer` seam; verify() checks records.

Self-test: python3 sigil_ed25519.py
"""
from __future__ import annotations

import os

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_PRIV = os.path.join(_DATA, "sigil_ed25519.key")   # raw 32 bytes, gitignored
_PUB = os.path.join(_DATA, "sigil_ed25519.pub")    # hex public key, publishable

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    _HAVE = True
except Exception:
    _HAVE = False


def available() -> bool:
    return _HAVE


def _load_or_create():
    """Return an Ed25519PrivateKey, creating + persisting one on first use."""
    os.makedirs(_DATA, exist_ok=True)
    if os.path.isfile(_PRIV):
        with open(_PRIV, "rb") as f:
            raw = f.read()
        return Ed25519PrivateKey.from_private_bytes(raw)
    sk = Ed25519PrivateKey.generate()
    raw = sk.private_bytes_raw()
    # write private key 0600
    fd = os.open(_PRIV, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    pub_hex = sk.public_key().public_bytes_raw().hex()
    with open(_PUB, "w") as f:
        f.write(pub_hex + "\n")
    return sk


def get_signer():
    """Return a callable(msg:str)->sig_hex for the SIGIL bus, or None if unavailable."""
    if not _HAVE:
        return None
    try:
        sk = _load_or_create()
    except Exception:
        return None

    def sign(msg: str) -> str:
        return sk.sign(msg.encode()).hex()

    sign.alg = "ed25519"  # type: ignore[attr-defined]
    return sign


def public_key_hex() -> str | None:
    """The publishable public key (hex). None if no keypair yet / unavailable."""
    if not _HAVE:
        return None
    try:
        _load_or_create()  # ensure exists
        with open(_PUB) as f:
            return f.read().strip()
    except Exception:
        return None


def verify(msg: str, sig_hex: str, pub_hex: str | None = None) -> bool:
    """Verify an Ed25519 signature over msg. Uses our published public key if pub_hex is None.
    Anyone can call this with our public key — no secret required."""
    if not _HAVE:
        return False
    try:
        ph = pub_hex or public_key_hex()
        if not ph:
            return False
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(ph))
        pk.verify(bytes.fromhex(sig_hex), msg.encode())
        return True
    except Exception:
        return False


# ---- self-test ----------------------------------------------------------------
if __name__ == "__main__":
    import tempfile
    fails = 0

    def ck(n, c):
        global fails
        print(("  ok  " if c else " FAIL ") + n)
        if not c:
            fails += 1

    ck("cryptography available", available())
    if available():
        # use a temp keypair so the self-test never touches the real key
        td = tempfile.mkdtemp()
        _PRIV = os.path.join(td, "k.key"); _PUB = os.path.join(td, "k.pub")  # noqa: F811
        # rebind module paths for the test
        globals()["_PRIV"] = _PRIV; globals()["_PUB"] = _PUB
        s = get_signer()
        ck("signer returned", s is not None)
        ck("signer alg tag", getattr(s, "alg", None) == "ed25519")
        msg = "digest123" + "prevsig456"
        sig = s(msg)
        ck("signature is hex", len(sig) == 128 and all(c in "0123456789abcdef" for c in sig))
        ck("verifies with our pubkey", verify(msg, sig))
        ck("tampered msg fails", not verify(msg + "x", sig))
        ck("wrong sig fails", not verify(msg, "00" * 64))
        ck("pubkey is hex64", len((public_key_hex() or "")) == 64)
        # key persists across calls (same pubkey)
        pk1 = public_key_hex(); s2 = get_signer(); pk2 = public_key_hex()
        ck("key persists (stable pubkey)", pk1 == pk2)
        # private key file is 0600
        mode = oct(os.stat(_PRIV).st_mode)[-3:]
        ck("private key is 0600", mode == "600")
    print(f"\n{'PASS — sigil_ed25519 green' if fails == 0 else f'FAIL — {fails} check(s)'}")
    raise SystemExit(1 if fails else 0)
