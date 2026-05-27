"""RAGuard — Safety Attestation & Audit Layer for MEOKCLAW.

Wraps the base guardrails with:
- Persistent audit logging
- Attestation reports (cryptographic hashes of decisions)
- i18n violation localization
- Rate-limiting per user/IP
- Export to Prometheus/SIEM

Usage:
    from raguard import RAGuard
    rg = RAGuard()
    result = rg.check("user query", locale="zh", user_id="u123")
    print(result.attestation_hash)
"""
from __future__ import annotations

from .engine import RAGuard, AttestationReport, AuditEntry

__all__ = ["RAGuard", "AttestationReport", "AuditEntry"]
