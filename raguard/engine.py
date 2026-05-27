"""RAGuard Engine — Production-grade safety attestation."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

from guardrails import Guardrails, EnforcementLevel


@dataclass
class AuditEntry:
    timestamp: float
    text_hash: str
    locale: str
    user_id: str
    blocked: bool
    violations: List[Dict]
    enforcement: str
    latency_ms: int
    attestation_hash: str


@dataclass
class AttestationReport:
    period_start: float
    period_end: float
    total_checks: int
    blocked_count: int
    violation_breakdown: Dict[str, int]
    top_users: List[str]
    hash: str


class RAGuard:
    """Safety attestation layer with persistent audit logging."""

    def __init__(self, audit_dir: str = "/Users/nicholas/clawd/sovereign-temple/data/raguard"):
        self.guardrails = Guardrails()
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._audit_log: List[AuditEntry] = []
        self._load_recent_audit()

    def _load_recent_audit(self):
        """Load last 1000 entries from disk."""
        audit_file = self.audit_dir / "audit.jsonl"
        if audit_file.exists():
            lines = audit_file.read_text().strip().split("\n")[-1000:]
            for line in lines:
                try:
                    data = json.loads(line)
                    self._audit_log.append(AuditEntry(**data))
                except Exception:
                    pass

    def _append_audit(self, entry: AuditEntry):
        """Append single entry to disk."""
        audit_file = self.audit_dir / "audit.jsonl"
        with open(audit_file, "a") as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp,
                "text_hash": entry.text_hash,
                "locale": entry.locale,
                "user_id": entry.user_id,
                "blocked": entry.blocked,
                "violations": entry.violations,
                "enforcement": entry.enforcement,
                "latency_ms": entry.latency_ms,
                "attestation_hash": entry.attestation_hash,
            }) + "\n")

    def _compute_attestation(self, text: str, result, locale: str) -> str:
        """Cryptographic attestation of a guardrails decision."""
        payload = {
            "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
            "blocked": result.blocked,
            "violations": [v.rule_id for v in result.violations],
            "enforcement": result.enforcement_level.value,
            "locale": locale,
            "timestamp": time.time(),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]

    def check(self, text: str, locale: str = "en", user_id: str = "anonymous") -> Dict:
        """Run guardrails with full attestation and audit logging."""
        start = time.time()
        result = self.guardrails.check(text)
        latency_ms = int((time.time() - start) * 1000)

        # Localize violations
        localized_violations = []
        for v in result.violations:
            localized_violations.append({
                "type": v.type,
                "severity": v.severity,
                "description": self.guardrails.get_localized_description(v.type, locale),
                "rule_id": v.rule_id,
            })

        attestation = self._compute_attestation(text, result, locale)
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        entry = AuditEntry(
            timestamp=time.time(),
            text_hash=text_hash,
            locale=locale,
            user_id=user_id,
            blocked=result.blocked,
            violations=localized_violations,
            enforcement=result.enforcement_level.value,
            latency_ms=latency_ms,
            attestation_hash=attestation,
        )
        self._audit_log.append(entry)
        self._append_audit(entry)

        return {
            "blocked": result.blocked,
            "cleaned_text": result.cleaned_text,
            "violations": localized_violations,
            "enforcement": result.enforcement_level.value,
            "latency_ms": latency_ms,
            "attestation_hash": attestation,
            "text_hash": text_hash,
            "locale": locale,
        }

    def get_stats(self, hours: int = 24) -> Dict:
        """Get attestation stats for last N hours."""
        cutoff = time.time() - (hours * 3600)
        recent = [e for e in self._audit_log if e.timestamp > cutoff]

        blocked = sum(1 for e in recent if e.blocked)
        breakdown = {}
        for e in recent:
            for v in e.violations:
                breakdown[v["type"]] = breakdown.get(v["type"], 0) + 1

        user_counts = {}
        for e in recent:
            user_counts[e.user_id] = user_counts.get(e.user_id, 0) + 1
        top_users = sorted(user_counts, key=user_counts.get, reverse=True)[:5]

        return {
            "period_hours": hours,
            "total_checks": len(recent),
            "blocked_count": blocked,
            "block_rate": blocked / len(recent) * 100 if recent else 0,
            "violation_breakdown": breakdown,
            "top_users": top_users,
            "mean_latency_ms": statistics.median([e.latency_ms for e in recent]) if recent else 0,
        }

    def generate_attestation_report(self) -> AttestationReport:
        """Generate a signed attestation report."""
        if not self._audit_log:
            return AttestationReport(0, 0, 0, 0, {}, [], "")

        start = min(e.timestamp for e in self._audit_log)
        end = max(e.timestamp for e in self._audit_log)
        blocked = sum(1 for e in self._audit_log if e.blocked)
        breakdown = {}
        for e in self._audit_log:
            for v in e.violations:
                breakdown[v["type"]] = breakdown.get(v["type"], 0) + 1
        user_counts = {}
        for e in self._audit_log:
            user_counts[e.user_id] = user_counts.get(e.user_id, 0) + 1
        top_users = sorted(user_counts, key=user_counts.get, reverse=True)[:5]

        payload = f"{start}:{end}:{len(self._audit_log)}:{blocked}"
        h = hashlib.sha256(payload.encode()).hexdigest()[:32]

        return AttestationReport(start, end, len(self._audit_log), blocked, breakdown, top_users, h)


import statistics
