"""
rainbow_rotate.py — IP rotation cron (5 min roll), stub implementation.

The "rainbow" pattern (csoai-platform/tests/rainbow-simulation.test.ts):
the node's externally-visible IP address rolls every 5 minutes through a
pre-computed schedule. This makes a worm tunnel hard to track (the
ingress moves), a probe hard to correlate (the same target appears to
come from many IPs), and a DDoS hard to sustain (the new IP isn't on
their blocklist yet).

STUB semantics:
  * The IP pool is a config-supplied list (e.g. cloud providers, VPN
    endpoints, residential proxies).
  * `roll()` returns the next IP + epoch + checksum, and is what a cron
    job calls every 5 minutes.
  * `current()` returns the active IP without advancing.
  * `force_rotate(reason)` jumps to a fresh IP immediately (used by the
    worm-tunnel-kill switch).
  * `stats()` returns the rotation history + the next scheduled roll.
  * `csoai_compatibility()` confirms the rotation shape matches what the
    rainbow-simulation test expects (interval_s, pool_size, byzantine
    fault tolerance).

This does NOT actually bind sockets / change network state — it is the
control plane. The integration point is whoever swaps the egress IP
(Cloudflare worker, Wireguard, caddy, etc.). A hook is exposed via
set_ip_applier(callable) so the live deploy can register the function
that actually applies the new IP.

Wired in:
  • sovereign-mcp-server.py  — rainbow_rotate tool
  • bft_threat_council.py    — force_rotate() on VETO (kill switch)
"""
from __future__ import annotations

import os
import time
import json
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

DEFAULT_INTERVAL_S = 300          # 5 min
DEFAULT_POOL = [
    "10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4", "10.0.0.5",
    "10.0.0.6", "10.0.0.7", "10.0.0.8", "10.0.0.9", "10.0.0.10",
    "10.0.0.11", "10.0.0.12", "10.0.0.13", "10.0.0.14", "10.0.0.15",
    "10.0.0.16",
]


@dataclass
class RotationEvent:
    epoch: float
    old_ip: str
    new_ip: str
    reason: str
    checksum: str


class RainbowRotator:
    """The rotation controller. Thread-safe."""

    def __init__(self, pool: Optional[list] = None, interval_s: int = DEFAULT_INTERVAL_S,
                 applier: Optional[Callable[[str], bool]] = None,
                 start_at: Optional[int] = None):
        self.pool = list(pool or DEFAULT_POOL)
        self.interval_s = int(interval_s)
        self._lock = threading.RLock()
        self._idx = (start_at or 0) % max(len(self.pool), 1)
        self._last_roll: Optional[RotationEvent] = None
        self._history: list[RotationEvent] = []
        self._applier = applier
        # seed an initial event so stats() is meaningful
        if self.pool:
            ev = RotationEvent(
                epoch=time.time(), old_ip="-", new_ip=self.pool[self._idx],
                reason="init", checksum=self._checksum(self.pool[self._idx], 0),
            )
            self._history.append(ev)
            self._last_roll = ev

    # ---- public API ------------------------------------------------------
    def current(self) -> str:
        with self._lock:
            return self.pool[self._idx] if self.pool else "0.0.0.0"

    def roll(self, reason: str = "schedule") -> RotationEvent:
        """Advance to the next IP. Returns the new RotationEvent."""
        with self._lock:
            old = self.pool[self._idx]
            self._idx = (self._idx + 1) % len(self.pool) if self.pool else 0
            new = self.pool[self._idx] if self.pool else "0.0.0.0"
            ev = RotationEvent(
                epoch=time.time(), old_ip=old, new_ip=new, reason=reason,
                checksum=self._checksum(new, self._idx),
            )
            self._history.append(ev)
            self._last_roll = ev
            if self._applier:
                try:
                    self._applier(new)
                except Exception:
                    pass
            return ev

    def force_rotate(self, reason: str = "veto") -> RotationEvent:
        """Jumps to a new IP immediately (skip interval). Used by the kill switch."""
        return self.roll(reason=reason)

    def next_roll_in_s(self) -> float:
        if not self._last_roll:
            return 0.0
        return max(0.0, self.interval_s - (time.time() - self._last_roll.epoch))

    def set_ip_applier(self, fn: Callable[[str], bool]) -> None:
        """Register the function that actually applies the new egress IP
        (e.g. talks to cloudflare / wireguard / iptables)."""
        with self._lock:
            self._applier = fn

    def history(self, limit: int = 50) -> list:
        with self._lock:
            return [asdict(e) for e in self._history[-limit:]]

    def stats(self) -> dict:
        with self._lock:
            return {
                "pool_size": len(self.pool),
                "current_ip": self.pool[self._idx] if self.pool else None,
                "index": self._idx,
                "interval_s": self.interval_s,
                "next_roll_in_s": round(self.next_roll_in_s(), 1),
                "last_roll": asdict(self._last_roll) if self._last_roll else None,
                "history_len": len(self._history),
                "applier_registered": self._applier is not None,
            }

    def csoai_compatibility(self) -> dict:
        """Shape check against csoai-platform/tests/rainbow-simulation.test.ts.
        That test expects: interval (s), pool_size, byzantine fault tolerance.
        Returns a dict the test can assert against."""
        n = len(self.pool)
        f = (n - 1) // 3 if n else 0
        return {
            "interval_s": self.interval_s,
            "pool_size": n,
            "byzantine_fault_tolerance_f": f,
            "byzantine_quorum": 2 * f + 1,
            "current_ip": self.current(),
            "next_roll_in_s": round(self.next_roll_in_s(), 1),
        }

    # ---- internals -------------------------------------------------------
    @staticmethod
    def _checksum(ip: str, idx: int) -> str:
        h = hashlib.sha256(f"{ip}|{idx}|{int(time.time())}".encode()).hexdigest()
        return h[:16]


# ── Module-level singleton + cron loop ─────────────────────────────────────
_ROTATOR = None
_CRON_THREAD = None
_CRON_STOP = threading.Event()


def get_rotator(pool: Optional[list] = None, interval_s: int = DEFAULT_INTERVAL_S,
                applier: Optional[Callable[[str], bool]] = None) -> RainbowRotator:
    global _ROTATOR
    if _ROTATOR is None:
        _ROTATOR = RainbowRotator(pool=pool, interval_s=interval_s, applier=applier)
    return _ROTATOR


def start_cron(interval_s: int = DEFAULT_INTERVAL_S,
               applier: Optional[Callable[[str], bool]] = None) -> dict:
    """Start the background 5-min roll cron. Idempotent."""
    global _CRON_THREAD
    rot = get_rotator(interval_s=interval_s, applier=applier)
    if _CRON_THREAD and _CRON_THREAD.is_alive():
        return {"started": False, "reason": "already running", "stats": rot.stats()}

    def _loop():
        while not _CRON_STOP.is_set():
            _CRON_STOP.wait(interval_s)
            if _CRON_STOP.is_set():
                break
            try:
                rot.roll(reason="schedule")
            except Exception:
                pass

    _CRON_STOP.clear()
    _CRON_THREAD = threading.Thread(target=_loop, name="rainbow-rotate", daemon=True)
    _CRON_THREAD.start()
    return {"started": True, "stats": rot.stats()}


def stop_cron() -> dict:
    global _CRON_THREAD
    _CRON_STOP.set()
    _CRON_THREAD = None
    return {"stopped": True, "stats": get_rotator().stats()}


def _wipe_singletons() -> None:
    """Test helper: clear module-level rotator + thread state."""
    global _ROTATOR, _CRON_THREAD
    if _CRON_THREAD and _CRON_THREAD.is_alive():
        _CRON_STOP.set()
        _CRON_THREAD.join(timeout=1.0)
    _ROTATOR = None
    _CRON_THREAD = None
    _CRON_STOP.clear()


# ── Self-test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fails = 0
    def check(name, cond):
        global fails
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond:
            fails += 1

    print("rainbow_rotate self-test")
    rot = RainbowRotator(pool=["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"], interval_s=300)

    check("starts on pool[0]", rot.current() == "1.1.1.1")
    ev1 = rot.roll(reason="test1")
    check("roll advances to pool[1]", rot.current() == "2.2.2.2" and ev1.new_ip == "2.2.2.2")
    ev2 = rot.roll(reason="test2")
    check("roll advances to pool[2]", rot.current() == "3.3.3.3" and ev2.new_ip == "3.3.3.3")
    rot.roll(); rot.roll(); rot.roll(); rot.roll()
    check("roll wraps around", rot.current() == "3.3.3.3")  # 6 rolls from idx 0 → 6 % 4 = 2

    # csoai compatibility shape
    compat = rot.csoai_compatibility()
    check("csoai interval_s == 300", compat["interval_s"] == 300)
    check("csoai pool_size == 4", compat["pool_size"] == 4)
    check("csoai f == 1 (4 nodes, f=floor(3/3)=1)", compat["byzantine_fault_tolerance_f"] == 1)
    check("csoai quorum == 3 (2f+1)", compat["byzantine_quorum"] == 3)

    # force_rotate
    rot.force_rotate(reason="worm_tunnel_kill")
    last = rot.history(limit=1)[0]
    check("force_rotate logs reason=worm_tunnel_kill", last["reason"] == "worm_tunnel_kill")

    # stats
    s = rot.stats()
    check("stats has current_ip", "current_ip" in s and s["current_ip"])
    check("stats has history_len > 0", s["history_len"] > 0)

    # cron start/stop — wipe the singleton + thread (which may already exist
    # from a prior call) and then verify the cron actually rolls on a fresh one.
    _wipe_singletons()
    singleton = get_rotator(pool=["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"], interval_s=1)
    pre_history = singleton.stats()["history_len"]
    r = start_cron(interval_s=1)
    check("cron starts", r["started"] is True)
    time.sleep(2.5)  # give the cron thread time to do at least 2 rolls
    r2 = start_cron(interval_s=1)  # second call is no-op
    check("cron is idempotent", r2["started"] is False)
    check("cron produced a scheduled roll",
          r2["stats"]["history_len"] > pre_history)
    stop_cron()
    check("cron stops", stop_cron()["stopped"] is True)

    print(f"\n{'PASS — rainbow_rotate green' if fails == 0 else f'FAIL — {fails} check(s)'}")
    raise SystemExit(1 if fails else 0)
