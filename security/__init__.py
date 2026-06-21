"""
security/__init__.py — SOV3 security primitives (additive, opt-in).

The 4 modules in this package compose the SOVEREIGN SECURITY BRAIN:

  security_brain         per-node 3-tier wrapper (hot/warm/cold)
  bft_threat_council     33-node BFT for threat detection (11 lenses × 3 replicas)
  rainbow_rotate         5-min IP rotation cron
  worm_guard             the underlying regex scanner (Morris-II)

Public surface re-exports the small set of names the rest of the system
should depend on (everything else is implementation detail).
"""
from __future__ import annotations

try:
    from .security_brain import (
        SecurityBrain, BrainResult, quick_guard, default_brain,
        HOT, WARM, COLD,
        VERDICT_PASS, VERDICT_VETO, VERDICT_HOLD, VERDICT_QUARANTINE, VERDICT_LIMIT,
    )
    _BRAIN_OK = True
except Exception as _e:  # never break import chain
    _BRAIN_OK = False
    SecurityBrain = None
    BrainResult = None
    quick_guard = None
    default_brain = None

try:
    from .bft_threat_council import (
        ThreatCouncil, CouncilResult, LensVote, LENSES,
    )
    _COUNCIL_OK = True
except Exception:
    _COUNCIL_OK = False
    ThreatCouncil = None
    CouncilResult = None
    LensVote = None
    LENSES = ()

try:
    from .rainbow_rotate import (
        RainbowRotator, RotationEvent,
        get_rotator, start_cron, stop_cron,
    )
    _ROTATE_OK = True
except Exception:
    _ROTATE_OK = False
    RainbowRotator = None
    RotationEvent = None
    get_rotator = None
    start_cron = None
    stop_cron = None

__all__ = [
    "SecurityBrain", "BrainResult", "quick_guard", "default_brain",
    "ThreatCouncil", "CouncilResult", "LensVote", "LENSES",
    "RainbowRotator", "RotationEvent", "get_rotator", "start_cron", "stop_cron",
    "HOT", "WARM", "COLD",
    "VERDICT_PASS", "VERDICT_VETO", "VERDICT_HOLD", "VERDICT_QUARANTINE", "VERDICT_LIMIT",
]
