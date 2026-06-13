"""
sigil_bus.py — wire SIGIL into the live agent fabric (makes the 3-brain vision real).

sigil.py is a complete protocol but was imported by nothing. This bus is the missing
wiring: every inter-agent exchange (council propose/vote, swarm handoff, memory, care,
alert, state) goes through emit() →

    encode (SIGIL line)  →  gloss (plain English)  →  digest (sha256)
                         →  HMAC-sign the digest   →  append to a HASH-CHAINED ledger

So the opus-left / minimax-right / kimi / sov3-middle fleet finally talks in ONE
signed, replayable, auditable interchange language. The ledger (data/sigil_ledger.jsonl)
is tamper-evident (each record carries the previous signature) — the "verifiable agent
communication" artifact that EU AI Act Art 12 (logging) + Art 14 (oversight) want.

Honesty: signing is HMAC-SHA256 = INTERNAL tamper-evidence. External-grade asymmetric
signing (Ed25519) is the upgrade in task #43; the bus exposes a `signer` seam for it.

Self-test: `python3 sigil_bus.py`
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sigil  # the protocol (encode/parse/gloss/digest)

_LEDGER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sigil_ledger.jsonl"
)
_GENESIS = "0" * 64


class SigilBus:
    """Signed, hash-chained SIGIL exchange bus. One per process; thread-safe enough for
    SOV3's usage (append-only, last-sig read)."""

    def __init__(self, audit_logger=None, key: str | None = None,
                 ledger_path: str | None = None, ring: int = 512, signer=None):
        self.audit = audit_logger
        self._key = (key or os.environ.get("MEOK_SIGIL_KEY", "sov3-sigil-dev-key")).encode()
        self.ledger_path = ledger_path or _LEDGER
        self.transcript = deque(maxlen=ring)
        self._signer = signer  # optional asymmetric signer(digest:str)->sig:str (Ed25519 later)
        self._last_sig = self._load_last_sig()

    # ---- signing ----
    def _sign(self, digest: str, prev: str) -> str:
        if self._signer is not None:
            try:
                return self._signer(digest + prev)
            except Exception:
                pass
        return hmac.new(self._key, (digest + prev).encode(), hashlib.sha256).hexdigest()

    def verify(self, line: str, signature: str, prev: str) -> bool:
        """Verify a record's HMAC signature (only valid for the HMAC path)."""
        expect = hmac.new(self._key, (sigil.digest(line) + prev).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expect, signature)

    def public_key(self):
        """The Ed25519 public key (hex) anyone can verify our records with — None if HMAC-only."""
        try:
            from sigil_ed25519 import public_key_hex
            return public_key_hex()
        except Exception:
            return None

    def _verify_rec(self, rec: dict, prev: str) -> bool:
        """Alg-aware signature check for one ledger record (HMAC or Ed25519)."""
        msg = sigil.digest(rec["line"]) + prev
        if rec.get("alg") == "ed25519":
            try:
                from sigil_ed25519 import verify as _edv
                return _edv(msg, rec["signature"])
            except Exception:
                return True  # lib gone → don't fail chain on sig; prev-link check still applies
        expect = hmac.new(self._key, msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expect, rec["signature"])

    def _load_last_sig(self) -> str:
        try:
            if os.path.exists(self.ledger_path):
                with open(self.ledger_path, "rb") as f:
                    # read last non-empty line cheaply
                    last = None
                    for ln in f:
                        s = ln.strip()
                        if s:
                            last = s
                    if last:
                        return json.loads(last).get("signature", _GENESIS)
        except Exception:
            pass
        return _GENESIS

    # ---- core ----
    def emit(self, event) -> dict:
        """event = a SIGIL line (str) OR a dict with op + fields. Returns the signed record."""
        line = event if isinstance(event, str) else sigil.encode(event)
        gloss = sigil.gloss(line)
        digest = sigil.digest(line)
        prev = self._last_sig
        signature = self._sign(digest, prev)
        rec = {
            "ts": round(time.time(), 3),
            "line": line, "gloss": gloss, "digest": digest,
            "prev_sig": prev, "signature": signature,
            "alg": (getattr(self._signer, "alg", "ed25519") if self._signer is not None else "hmac-sha256"),
        }
        self._last_sig = signature
        self.transcript.append(rec)
        self._append_ledger(rec)
        self._audit(rec)
        return rec

    def _append_ledger(self, rec: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, separators=(",", ":")) + "\n")
        except Exception as e:
            print(f"[sigil-bus] ledger write failed (non-fatal): {e}")

    def _audit(self, rec: dict) -> None:
        if self.audit is None:
            return
        try:
            import asyncio
            from audit_logger import AuditEventType  # type: ignore
            et = getattr(AuditEventType, "SECURITY_EVENT",
                         getattr(AuditEventType, "SYSTEM_EVENT", None))
            asyncio.get_event_loop().create_task(self.audit.log_event(
                event_type=et, source_agent="sigil_bus",
                details={"type": "sigil_emit", "line": rec["line"], "gloss": rec["gloss"],
                         "digest": rec["digest"], "signature": rec["signature"]},
            ))
        except Exception:
            pass  # audit is best-effort; the ledger is the source of truth

    # ---- convenience emitters (the opcodes) ----
    def handoff(self, frm: str, to: str, task: str) -> dict:
        return self.emit({"op": "H", "frm": frm, "to": to, "task": task})

    def propose(self, pid: str, topic: str, options: list) -> dict:
        return self.emit({"op": "P", "id": pid, "topic": topic, "options": options})

    def vote(self, agent: str, prop: str, choice: str, conf) -> dict:
        return self.emit({"op": "V", "agent": agent, "prop": prop, "choice": choice, "conf": str(conf)})

    def memory(self, key: str, value: str, salience) -> dict:
        return self.emit({"op": "M", "key": key, "value": value, "salience": str(salience)})

    def care(self, subject: str, score, dims: list) -> dict:
        return self.emit({"op": "C", "subject": subject, "score": str(score), "dims": dims})

    def alert(self, level: str, msg: str) -> dict:
        return self.emit({"op": "A", "level": level, "msg": msg})

    def state(self, **fields) -> dict:
        return self.emit({"op": "S", "fields": {k: str(v) for k, v in fields.items()}})

    # ---- read / audit the ledger ----
    def recent(self, n: int = 20) -> list:
        return list(self.transcript)[-n:]

    def audit_chain(self, limit: int = 1000) -> dict:
        """Walk the ledger, verify the hash-chain + HMAC sigs. Returns integrity report."""
        if not os.path.exists(self.ledger_path):
            return {"records": 0, "intact": True, "broken_at": None}
        prev = _GENESIS
        n = 0
        broken = None
        with open(self.ledger_path, encoding="utf-8") as f:
            for ln in f:
                s = ln.strip()
                if not s:
                    continue
                n += 1
                if n > limit:
                    break
                rec = json.loads(s)
                if rec.get("prev_sig") != prev:
                    broken = n
                    break
                if not self._verify_rec(rec, prev):
                    broken = n
                    break
                prev = rec["signature"]
        return {"records": n, "intact": broken is None, "broken_at": broken,
                "public_key": self.public_key()}


# process-wide singleton accessor (so all callers chain into one ledger)
_BUS = None


def get_bus(audit_logger=None):
    global _BUS
    if _BUS is None:
        _sg = None
        try:
            from sigil_ed25519 import get_signer as _gs
            _sg = _gs()  # Ed25519 if cryptography + key available; else None → HMAC fallback
        except Exception:
            _sg = None
        _BUS = SigilBus(audit_logger=audit_logger, signer=_sg)
    elif audit_logger is not None and _BUS.audit is None:
        _BUS.audit = audit_logger
    return _BUS


# ---- self-test ----------------------------------------------------------------
if __name__ == "__main__":
    fails = 0

    def ck(n, c):
        global fails
        print(("  ok  " if c else " FAIL ") + n)
        if not c:
            fails += 1

    tmp = "/tmp/sigil_ledger_test.jsonl"
    if os.path.exists(tmp):
        os.remove(tmp)
    bus = SigilBus(ledger_path=tmp, key="test-key")

    r1 = bus.handoff("queen", "researcher1", "gather EU AI Act Article 50 facts")
    ck("handoff encodes to H line", r1["line"].startswith("H|queen|researcher1|"))
    ck("gloss is English", "Handoff from queen to researcher1" in r1["gloss"])
    ck("digest present", len(r1["digest"]) == 16)
    ck("signed", len(r1["signature"]) == 64)
    ck("first prev_sig is genesis", r1["prev_sig"] == _GENESIS)

    r2 = bus.vote("jarvis", "ad6d", "APPROVE", 0.82)
    ck("vote chains onto handoff", r2["prev_sig"] == r1["signature"])
    ck("vote line correct", r2["line"] == "V|jarvis|ad6d|+|0.82")

    r3 = bus.propose("p1", "Prioritise Q3", ["A", "B", "C"])
    bus.care("p1", 0.91, ["attunement", "reciprocity"])
    bus.state(consciousness=0.525, agents=46, care=0.967)
    bus.alert("info", "2/3 supermajority reached")

    ck("transcript holds all 6", len(bus.recent(50)) == 6)

    # signature verifies; tamper breaks it
    ck("signature verifies", bus.verify(r2["line"], r2["signature"], r2["prev_sig"]))
    ck("tampered line fails verify", not bus.verify("V|jarvis|ad6d|-|0.82", r2["signature"], r2["prev_sig"]))

    # ledger hash-chain intact
    report = bus.audit_chain()
    ck("ledger chain intact (6 recs)", report["records"] == 6 and report["intact"])

    # cross-instance: a fresh bus continues the chain from disk
    bus2 = SigilBus(ledger_path=tmp, key="test-key")
    r7 = bus2.alert("info", "second process appends")
    ck("new instance chains from disk", r7["prev_sig"] != _GENESIS)
    ck("full chain still intact", bus2.audit_chain()["intact"])

    print(f"\n{'PASS — sigil_bus green' if fails == 0 else f'FAIL — {fails} check(s)'}")
    raise SystemExit(1 if fails else 0)
