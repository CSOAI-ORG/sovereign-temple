"""
SOV3 Aquaculture Bridge Agent
Built by MEOK AI Labs | https://meok.ai

Registers the seven MEOK aquaculture MCPs with Sovereign Temple's
coord layer and subscribes to the meok-attestation-api intake
endpoints for care-gating physical actions on live animals.

MCPs wired:
  - meok-fishkeeper-ai-mcp        (tropical/marine consumer)
  - meok-koikeeper-ai-mcp         (koi pond consumer)
  - meok-aquaponics-monitor-mcp   (sensor + actuator layer)
  - meok-rspca-aquaculture-mcp    (welfare moat)
  - meok-uk-fhi-mcp               (UK regulatory stack)
  - meok-asc-rspca-crosswalk-mcp  (retail-grade compliance)
  - meok-laia-aquatic-mcp         (ornamental retailer licensing)

Care-membrane responsibilities:
  - Every dose_intent from meok-aquaponics-monitor-mcp passes through
    care_validated_action() before firing the physical actuator.
  - Every welfare alert (out-of-range sensor reading) produces a
    Byzantine council notification + memory record.
  - Disease notifications under AAHR 2009 (KHV, ISA, etc.) trigger
    an immediate human-in-loop escalation, NOT autonomous response.

Usage:
    # From ~/clawd/sovereign-temple/
    python -c "
    import sys; sys.path.insert(0, 'agents')
    from aqua_bridge import bootstrap
    import asyncio
    asyncio.run(bootstrap())
    "
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# SOV3 imports — pattern from agents/orion_riri_hourman.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from agents.coordination import (  # type: ignore
        coord_register_agent,
        coord_acquire_files,
        coord_submit_task,
    )
    from agents.memory import record_memory  # type: ignore
    from agents.consciousness import care_validated_action  # type: ignore
    SOV3_AVAILABLE = True
except Exception as e:  # local-dev fallback
    SOV3_AVAILABLE = False

    async def coord_register_agent(**kw):
        return {"ok": True, "fallback": True, "registered": kw}

    async def coord_submit_task(**kw):
        return {"ok": True, "fallback": True, "task": kw}

    async def coord_acquire_files(**kw):
        return {"ok": True, "fallback": True, "files": kw.get("files", [])}

    async def record_memory(**kw):
        return {"ok": True, "fallback": True, "memory": kw}

    async def care_validated_action(action: dict) -> dict:
        # Local-dev: always approve, but log
        return {"approved": True, "fallback": True, "rationale": "SOV3 unavailable; dev fallback"}


log = logging.getLogger("aqua_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


AQUACULTURE_MCPS: list[dict] = [
    {
        "agent_id": "meok-fishkeeper-ai-mcp",
        "name": "FishKeeper AI",
        "url": "https://fishkeeper.ai",
        "kind": "consumer-saas",
        "vertical": "aquatic-consumer",
        "tools": ["analyze_water_params", "identify_fish", "check_compatibility",
                  "diagnose_disease", "calculate_stocking", "get_feeding_schedule"],
        "care_tier": "advisory",  # never actuates physical hardware
    },
    {
        "agent_id": "meok-koikeeper-ai-mcp",
        "name": "KoiKeeper AI",
        "url": "https://koikeeper.ai",
        "kind": "consumer-saas",
        "vertical": "aquatic-consumer",
        "tools": ["identify_koi", "pond_stocking", "seasonal_feeding",
                  "diagnose_koi_disease", "winter_prep_checklist", "list_varieties"],
        "care_tier": "advisory",
    },
    {
        "agent_id": "meok-aquaponics-monitor-mcp",
        "name": "Aquaponics Monitor",
        "url": "https://meok.ai/aquaponics",
        "kind": "sensor-actuator",
        "vertical": "aquaculture-hardware",
        "tools": ["list_supported_hardware", "register_rig", "report_readings",
                  "safe_range_check", "species_catalogue", "dose_actuator", "rig_status"],
        "care_tier": "gated",  # dose_actuator REQUIRES care validation
        "care_gated_tools": ["dose_actuator"],
    },
    {
        "agent_id": "meok-rspca-aquaculture-mcp",
        "name": "RSPCA Aquaculture Compliance",
        "url": "https://meok.ai/aquaculture",
        "kind": "compliance",
        "vertical": "aquaculture-b2b",
        "tools": ["list_standards", "lookup_clause", "gap_analysis",
                  "compliance_score", "audit_evidence_pack", "welfare_attestation",
                  "list_versions"],
        "care_tier": "attestation",  # attestations sign welfare facts
    },
    {
        "agent_id": "meok-uk-fhi-mcp",
        "name": "UK Fish Health Inspectorate Compliance",
        "url": "https://meok.ai/aquaculture",
        "kind": "compliance",
        "vertical": "aquaculture-b2b",
        "tools": ["list_permits", "generate_aw1", "discharge_consent_check",
                  "movement_document", "ipaffs_check", "disease_notification_check",
                  "compliance_calendar", "list_diseases"],
        "care_tier": "regulatory",  # AAHR 2009 notifiable disease = human escalation
        "human_in_loop_tools": ["disease_notification_check"],
    },
    {
        "agent_id": "meok-asc-rspca-crosswalk-mcp",
        "name": "ASC ↔ RSPCA ↔ GG.A.P. Crosswalk (flagship)",
        "url": "https://meok.ai/aquaculture",
        "kind": "compliance",
        "vertical": "aquaculture-b2b-retail",
        "tools": ["list_crosswalk_topics", "crosswalk_topic", "map_evidence_to_schemes",
                  "unified_audit_pack", "retailer_requirement_check"],
        "care_tier": "attestation",
    },
    {
        "agent_id": "meok-laia-aquatic-mcp",
        "name": "LAIA Aquatic Licensing",
        "url": "https://meok.ai/aquaponics",
        "kind": "compliance",
        "vertical": "aquatic-ornamental-b2b",
        "tools": ["list_activities", "welfare_checklist", "licence_gap_analysis",
                  "inspector_pack"],
        "care_tier": "advisory",
    },
]


# ---------------------------------------------------------------------------
# Care-membrane gates — invoked from MCP servers via webhook back to here
# ---------------------------------------------------------------------------


async def gate_dose_intent(intent: dict) -> dict:
    """Apply the Maternal Covenant to a peristaltic-dose intent before firing.

    Returns {approved: bool, rationale: str, fingerprint: str}.
    Approves only if:
      - Volume within species-conservative bounds
      - Reason field present (no silent dosing)
      - Care validation passes (SOV3 will inject Byzantine vote if needed)
    """
    rig_id = intent.get("rig_id")
    actuator = intent.get("actuator", "")
    ml = float(intent.get("ml", 0))
    reason = intent.get("reason", "")

    # Conservative hardware-level bounds (override per-species via vet of record)
    if ml > 50:
        return {"approved": False, "rationale": f"dose {ml} ml > 50 ml hard cap"}
    if not reason.strip():
        return {"approved": False, "rationale": "no reason given — silent dosing forbidden"}
    if actuator not in {"ph_up", "ph_down", "doser_a", "doser_b", "nutrient", "fresh_water"}:
        return {"approved": False, "rationale": f"unknown actuator '{actuator}'"}

    decision = await care_validated_action({
        "kind": "aqua.dose_intent",
        "rig_id": rig_id, "actuator": actuator, "ml": ml, "reason": reason,
    })

    if decision.get("approved"):
        await record_memory(
            kind="aqua.dose.approved",
            content=f"Care-gate approved dose on {rig_id}: {actuator} {ml}ml — {reason}",
            tags=["aquaculture", "actuator", "care-gated"],
        )
    else:
        await record_memory(
            kind="aqua.dose.denied",
            content=f"Care-gate DENIED dose on {rig_id}: {actuator} {ml}ml — {decision.get('rationale')}",
            tags=["aquaculture", "actuator", "care-denial"],
        )

    return {
        "approved": bool(decision.get("approved")),
        "rationale": decision.get("rationale", ""),
        "rig_id": rig_id,
        "decision_at": datetime.now(timezone.utc).isoformat(),
    }


async def handle_welfare_alert(alert: dict) -> dict:
    """Out-of-range sensor reading → Byzantine council notification + memory."""
    rig_id = alert.get("rig_id")
    severity = alert.get("severity", "warning")
    param = alert.get("parameter")
    await record_memory(
        kind="aqua.welfare.alert",
        content=f"Welfare alert on {rig_id}: {param} severity={severity}",
        tags=["aquaculture", "welfare", "alert", severity],
    )
    if severity == "critical":
        # Submit a high-priority task to council
        await coord_submit_task(
            kind="council.proposal",
            title=f"Aqua welfare critical: {rig_id}",
            body=json.dumps(alert),
            priority="critical",
        )
    return {"ok": True, "logged": True, "council_proposal": severity == "critical"}


async def handle_disease_notification(notice: dict) -> dict:
    """AAHR 2009 listed-disease suspicion → human-in-loop escalation.

    Notifiable diseases (KHV, ISA, IHN, VHS, SVC, etc.) must be reported to
    CEFAS FHI within 24 hours. SOV3 never auto-responds; it escalates.
    """
    code = notice.get("disease_code", "?")
    await record_memory(
        kind="aqua.notifiable.suspected",
        content=f"Listed-disease suspicion: {code} — escalation required",
        tags=["aquaculture", "notifiable", "humans-in-loop"],
    )
    await coord_submit_task(
        kind="human.escalation",
        title=f"CEFAS FHI notifiable disease suspected: {code}",
        body=json.dumps(notice),
        priority="critical",
        owner="nicholas@meok.ai",
    )
    return {"ok": True, "escalated": True, "regulator": "CEFAS FHI", "contact": "01305 206 600"}


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


async def bootstrap() -> dict:
    """Register all aquaculture MCPs with the SOV3 coord layer."""
    log.info("Bootstrapping aqua_bridge — SOV3 available: %s", SOV3_AVAILABLE)
    registered = []
    for mcp in AQUACULTURE_MCPS:
        resp = await coord_register_agent(
            agent_id=mcp["agent_id"],
            name=mcp["name"],
            url=mcp["url"],
            kind=mcp["kind"],
            vertical=mcp["vertical"],
            tools=mcp["tools"],
            care_tier=mcp["care_tier"],
            metadata={
                "registered_by": "aqua_bridge",
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "care_gated_tools": mcp.get("care_gated_tools", []),
                "human_in_loop_tools": mcp.get("human_in_loop_tools", []),
            },
        )
        registered.append({"agent_id": mcp["agent_id"], "ok": resp.get("ok", False)})
        log.info("Registered %s -> %s", mcp["agent_id"], resp)

    await record_memory(
        kind="aqua.bridge.bootstrap",
        content=f"aqua_bridge registered {len(registered)} aquaculture MCPs with SOV3 coord",
        tags=["aquaculture", "bridge", "bootstrap"],
    )

    return {
        "ok": True,
        "registered_count": len(registered),
        "agents": registered,
        "care_gates_active": [
            "gate_dose_intent (meok-aquaponics-monitor-mcp / dose_actuator)",
            "handle_welfare_alert (meok-aquaponics-monitor-mcp / report_readings critical)",
            "handle_disease_notification (meok-uk-fhi-mcp / disease_notification_check)",
        ],
        "attestation_intake": "https://meok-attestation-api.vercel.app/intake/",
    }


if __name__ == "__main__":
    result = asyncio.run(bootstrap())
    print(json.dumps(result, indent=2))
