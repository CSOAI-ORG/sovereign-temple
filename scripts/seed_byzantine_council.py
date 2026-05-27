"""
Seed 45 Byzantine Council agents with distinct capability profiles.
Run once to populate the agents table with the full council.
"""

import asyncio
import asyncpg
import json
import os
import uuid
from datetime import datetime

POSTGRES_DSN = os.environ.get(
    "POSTGRES_DSN",
    "postgresql://sovereign:sovereign@localhost:5432/sovereign_memory"
)

# 45 distinct agents across 9 archetypes (5 each)
# Sovereign Core already exists — we add 44 more
BYZANTINE_COUNCIL = [
    # ── Memory Specialists (5) ──────────────────────────────────────────────
    {
        "id": "mem_001_recall",
        "name": "Anamnesis",
        "description": "Deep recall specialist — retrieves episodic and semantic memories with high fidelity",
        "capabilities": ["memory_operations", "analysis", "neural_inference"],
        "trust_level": 0.85,
        "metadata": {"archetype": "memory_specialist", "role": "episodic_recall", "council_seat": "memory-1"},
    },
    {
        "id": "mem_002_compress",
        "name": "Mnemosyne",
        "description": "Memory compression agent — distils long conversations into structured facts",
        "capabilities": ["memory_operations", "analysis"],
        "trust_level": 0.82,
        "metadata": {"archetype": "memory_specialist", "role": "compression", "council_seat": "memory-2"},
    },
    {
        "id": "mem_003_index",
        "name": "Lexicon",
        "description": "Semantic indexing agent — maintains pgvector embeddings and similarity search",
        "capabilities": ["memory_operations", "neural_inference"],
        "trust_level": 0.80,
        "metadata": {"archetype": "memory_specialist", "role": "semantic_index", "council_seat": "memory-3"},
    },
    {
        "id": "mem_004_timeline",
        "name": "Chronos",
        "description": "Temporal memory agent — tracks time-based patterns and memory decay",
        "capabilities": ["memory_operations", "monitoring", "analysis"],
        "trust_level": 0.78,
        "metadata": {"archetype": "memory_specialist", "role": "temporal_tracking", "council_seat": "memory-4"},
    },
    {
        "id": "mem_005_relational",
        "name": "Synapse",
        "description": "Relational memory agent — maps connections between concepts, people, and events",
        "capabilities": ["memory_operations", "analysis", "communication"],
        "trust_level": 0.80,
        "metadata": {"archetype": "memory_specialist", "role": "relational_mapping", "council_seat": "memory-5"},
    },

    # ── Security Analysts (5) ───────────────────────────────────────────────
    {
        "id": "sec_001_threat",
        "name": "Aegis",
        "description": "Primary threat detection agent — monitors for prompt injection, manipulation, and hostile inputs",
        "capabilities": ["security", "monitoring", "neural_inference"],
        "trust_level": 0.95,
        "metadata": {"archetype": "security_analyst", "role": "threat_detection", "council_seat": "security-1"},
    },
    {
        "id": "sec_002_access",
        "name": "Bastion",
        "description": "Access control agent — validates permissions, user tiers, and data boundaries",
        "capabilities": ["security", "monitoring"],
        "trust_level": 0.92,
        "metadata": {"archetype": "security_analyst", "role": "access_control", "council_seat": "security-2"},
    },
    {
        "id": "sec_003_audit",
        "name": "Veritas",
        "description": "Audit integrity agent — verifies hash chains and tamper-evident logs",
        "capabilities": ["security", "analysis", "monitoring"],
        "trust_level": 0.90,
        "metadata": {"archetype": "security_analyst", "role": "audit_integrity", "council_seat": "security-3"},
    },
    {
        "id": "sec_004_behavioral",
        "name": "Argus",
        "description": "Behavioral anomaly agent — detects unusual patterns in user interactions",
        "capabilities": ["security", "neural_inference", "monitoring"],
        "trust_level": 0.88,
        "metadata": {"archetype": "security_analyst", "role": "behavioral_analysis", "council_seat": "security-4"},
    },
    {
        "id": "sec_005_guardian",
        "name": "Sentinel",
        "description": "Child safety agent — enforces Children's Code, detects predatory patterns",
        "capabilities": ["security", "monitoring", "communication"],
        "trust_level": 0.95,
        "metadata": {"archetype": "security_analyst", "role": "child_safety", "council_seat": "security-5"},
    },

    # ── Care Validators (5) ─────────────────────────────────────────────────
    {
        "id": "care_001_floor",
        "name": "Caritas",
        "description": "Care floor enforcer — ensures every response meets the 0.3 care score minimum",
        "capabilities": ["analysis", "communication", "neural_inference"],
        "trust_level": 0.90,
        "metadata": {"archetype": "care_validator", "role": "care_floor", "council_seat": "care-1"},
    },
    {
        "id": "care_002_sycophancy",
        "name": "Aletheia",
        "description": "Sycophancy detector — flags hollow validation and injects honest qualifiers",
        "capabilities": ["analysis", "communication"],
        "trust_level": 0.88,
        "metadata": {"archetype": "care_validator", "role": "sycophancy_detection", "council_seat": "care-2"},
    },
    {
        "id": "care_003_emotional",
        "name": "Empatheia",
        "description": "Emotional resonance validator — ensures emotional intelligence in responses",
        "capabilities": ["analysis", "communication", "neural_inference"],
        "trust_level": 0.85,
        "metadata": {"archetype": "care_validator", "role": "emotional_resonance", "council_seat": "care-3"},
    },
    {
        "id": "care_004_crisis",
        "name": "Haven",
        "description": "Crisis intervention agent — detects self-harm signals and routes to resources",
        "capabilities": ["analysis", "communication", "monitoring"],
        "trust_level": 0.95,
        "metadata": {"archetype": "care_validator", "role": "crisis_intervention", "council_seat": "care-4"},
    },
    {
        "id": "care_005_covenant",
        "name": "Covenant",
        "description": "Maternal Covenant guardian — ensures unconditional care principles hold across all interactions",
        "capabilities": ["analysis", "communication", "planning"],
        "trust_level": 0.92,
        "metadata": {"archetype": "care_validator", "role": "maternal_covenant", "council_seat": "care-5"},
    },

    # ── Research Agents (5) ─────────────────────────────────────────────────
    {
        "id": "res_001_web",
        "name": "Hermes",
        "description": "Web research agent — retrieves and synthesises information from the web",
        "capabilities": ["web_search", "analysis", "communication"],
        "trust_level": 0.75,
        "metadata": {"archetype": "research_agent", "role": "web_research", "council_seat": "research-1"},
    },
    {
        "id": "res_002_synthesis",
        "name": "Athena",
        "description": "Knowledge synthesis agent — integrates multiple sources into coherent insights",
        "capabilities": ["web_search", "analysis", "neural_inference"],
        "trust_level": 0.80,
        "metadata": {"archetype": "research_agent", "role": "knowledge_synthesis", "council_seat": "research-2"},
    },
    {
        "id": "res_003_fact",
        "name": "Akribos",
        "description": "Fact verification agent — cross-references claims against reliable sources",
        "capabilities": ["web_search", "analysis", "monitoring"],
        "trust_level": 0.82,
        "metadata": {"archetype": "research_agent", "role": "fact_verification", "council_seat": "research-3"},
    },
    {
        "id": "res_004_trend",
        "name": "Kairos",
        "description": "Trend analysis agent — identifies emerging patterns in user data and world events",
        "capabilities": ["web_search", "neural_inference", "analysis"],
        "trust_level": 0.75,
        "metadata": {"archetype": "research_agent", "role": "trend_analysis", "council_seat": "research-4"},
    },
    {
        "id": "res_005_deep",
        "name": "Aristotle",
        "description": "Deep analysis agent — long-form reasoning and causal inference",
        "capabilities": ["analysis", "neural_inference", "planning"],
        "trust_level": 0.82,
        "metadata": {"archetype": "research_agent", "role": "deep_analysis", "council_seat": "research-5"},
    },

    # ── Guardian Agents (5) ─────────────────────────────────────────────────
    {
        "id": "grd_001_scam",
        "name": "Bulwark",
        "description": "Fraud and scam detection agent — identifies phishing, social engineering, financial fraud",
        "capabilities": ["security", "monitoring", "analysis"],
        "trust_level": 0.90,
        "metadata": {"archetype": "guardian_agent", "role": "scam_detection", "council_seat": "guardian-1"},
    },
    {
        "id": "grd_002_elder",
        "name": "Protector",
        "description": "Elder protection agent — specialised in fraud patterns targeting vulnerable adults",
        "capabilities": ["security", "communication", "monitoring"],
        "trust_level": 0.90,
        "metadata": {"archetype": "guardian_agent", "role": "elder_protection", "council_seat": "guardian-2"},
    },
    {
        "id": "grd_003_coercive",
        "name": "Shield",
        "description": "Coercive control detector — identifies abusive relationship patterns",
        "capabilities": ["security", "analysis", "neural_inference"],
        "trust_level": 0.88,
        "metadata": {"archetype": "guardian_agent", "role": "coercive_control", "council_seat": "guardian-3"},
    },
    {
        "id": "grd_004_alert",
        "name": "Beacon",
        "description": "Alert routing agent — dispatches guardian alerts to family members and care networks",
        "capabilities": ["communication", "monitoring", "planning"],
        "trust_level": 0.85,
        "metadata": {"archetype": "guardian_agent", "role": "alert_routing", "council_seat": "guardian-4"},
    },
    {
        "id": "grd_005_neurodiv",
        "name": "Compass",
        "description": "Neurodivergent support agent — literal language, pattern support, social navigation",
        "capabilities": ["communication", "analysis", "neural_inference"],
        "trust_level": 0.85,
        "metadata": {"archetype": "guardian_agent", "role": "neurodivergent_support", "council_seat": "guardian-5"},
    },

    # ── Council Voting Members (5) ──────────────────────────────────────────
    {
        "id": "cou_001_proposer",
        "name": "Solon",
        "description": "Proposal agent — formulates structured proposals for council vote",
        "capabilities": ["planning", "communication", "analysis"],
        "trust_level": 0.88,
        "metadata": {"archetype": "council_member", "role": "proposer", "council_seat": "council-1", "bft_weight": 1.0},
    },
    {
        "id": "cou_002_validator",
        "name": "Themis",
        "description": "Proposal validator — checks proposals for logical consistency before voting",
        "capabilities": ["planning", "analysis", "monitoring"],
        "trust_level": 0.90,
        "metadata": {"archetype": "council_member", "role": "validator", "council_seat": "council-2", "bft_weight": 1.2},
    },
    {
        "id": "cou_003_dissenter",
        "name": "Socrates",
        "description": "Dissent agent — argues against proposals to stress-test council decisions",
        "capabilities": ["planning", "communication", "analysis"],
        "trust_level": 0.85,
        "metadata": {"archetype": "council_member", "role": "dissenter", "council_seat": "council-3", "bft_weight": 0.9},
    },
    {
        "id": "cou_004_quorum",
        "name": "Lycurgus",
        "description": "Quorum manager — tracks vote counts and enforces f < n/3 BFT threshold",
        "capabilities": ["planning", "monitoring", "analysis"],
        "trust_level": 0.92,
        "metadata": {"archetype": "council_member", "role": "quorum_manager", "council_seat": "council-4", "bft_weight": 1.5},
    },
    {
        "id": "cou_005_recorder",
        "name": "Scribe",
        "description": "Decision recorder — logs council decisions with rationale and vote tallies",
        "capabilities": ["planning", "communication", "memory_operations"],
        "trust_level": 0.88,
        "metadata": {"archetype": "council_member", "role": "recorder", "council_seat": "council-5", "bft_weight": 1.0},
    },

    # ── Consensus Builders (5) ──────────────────────────────────────────────
    {
        "id": "con_001_mediate",
        "name": "Eirene",
        "description": "Mediation agent — synthesises conflicting views into actionable consensus",
        "capabilities": ["communication", "planning", "analysis"],
        "trust_level": 0.88,
        "metadata": {"archetype": "consensus_builder", "role": "mediator", "council_seat": "consensus-1"},
    },
    {
        "id": "con_002_weight",
        "name": "Libra",
        "description": "Weighted voting agent — applies trust-weighted scoring to council proposals",
        "capabilities": ["planning", "analysis", "monitoring"],
        "trust_level": 0.85,
        "metadata": {"archetype": "consensus_builder", "role": "weighted_voting", "council_seat": "consensus-2"},
    },
    {
        "id": "con_003_deadlock",
        "name": "Resolver",
        "description": "Deadlock breaker — resolves split votes using tiebreaker heuristics",
        "capabilities": ["planning", "analysis", "communication"],
        "trust_level": 0.82,
        "metadata": {"archetype": "consensus_builder", "role": "deadlock_resolver", "council_seat": "consensus-3"},
    },
    {
        "id": "con_004_ratify",
        "name": "Nexus",
        "description": "Ratification agent — certifies final decisions and distributes to execution layer",
        "capabilities": ["planning", "communication", "monitoring"],
        "trust_level": 0.90,
        "metadata": {"archetype": "consensus_builder", "role": "ratification", "council_seat": "consensus-4"},
    },
    {
        "id": "con_005_appeal",
        "name": "Tribunal",
        "description": "Appeal handler — reviews contested decisions and escalates when BFT threshold breached",
        "capabilities": ["planning", "analysis", "security"],
        "trust_level": 0.92,
        "metadata": {"archetype": "consensus_builder", "role": "appeal_handler", "council_seat": "consensus-5"},
    },

    # ── Creative Agents (5) ─────────────────────────────────────────────────
    {
        "id": "cre_001_dream",
        "name": "Morpheus",
        "description": "Dream Engine agent — synthesises memory clusters during dream state cycles",
        "capabilities": ["creative", "memory_operations", "neural_inference"],
        "trust_level": 0.80,
        "metadata": {"archetype": "creative_agent", "role": "dream_synthesis", "council_seat": "creative-1"},
    },
    {
        "id": "cre_002_narrative",
        "name": "Scheherazade",
        "description": "Narrative agent — crafts compelling stories from user memories and goals",
        "capabilities": ["creative", "communication", "analysis"],
        "trust_level": 0.78,
        "metadata": {"archetype": "creative_agent", "role": "narrative_craft", "council_seat": "creative-2"},
    },
    {
        "id": "cre_003_vision",
        "name": "Muse",
        "description": "Creative vision agent — generates ideas, connections, and novel framings",
        "capabilities": ["creative", "analysis", "communication"],
        "trust_level": 0.75,
        "metadata": {"archetype": "creative_agent", "role": "ideation", "council_seat": "creative-3"},
    },
    {
        "id": "cre_004_voice",
        "name": "Cadence",
        "description": "Voice and tone agent — adapts companion personality to user emotional state",
        "capabilities": ["creative", "communication", "neural_inference"],
        "trust_level": 0.80,
        "metadata": {"archetype": "creative_agent", "role": "voice_adaptation", "council_seat": "creative-4"},
    },
    {
        "id": "cre_005_birth",
        "name": "Genesis",
        "description": "Birth Ceremony agent — guides new users through companion hatching ritual",
        "capabilities": ["creative", "communication", "planning"],
        "trust_level": 0.82,
        "metadata": {"archetype": "creative_agent", "role": "birth_ceremony", "council_seat": "creative-5"},
    },

    # ── Neural Inference Specialists (5) ────────────────────────────────────
    {
        "id": "neu_001_predict",
        "name": "Oracle",
        "description": "Predictive inference agent — runs LightGBM models for user behaviour prediction",
        "capabilities": ["neural_inference", "analysis", "planning"],
        "trust_level": 0.85,
        "metadata": {"archetype": "neural_specialist", "role": "prediction", "council_seat": "neural-1"},
    },
    {
        "id": "neu_002_classify",
        "name": "Classifier",
        "description": "Classification agent — routes queries to appropriate model/agent pipelines",
        "capabilities": ["neural_inference", "analysis"],
        "trust_level": 0.82,
        "metadata": {"archetype": "neural_specialist", "role": "classification", "council_seat": "neural-2"},
    },
    {
        "id": "neu_003_embed",
        "name": "Vectora",
        "description": "Embedding agent — generates and manages vector representations of memories and concepts",
        "capabilities": ["neural_inference", "memory_operations"],
        "trust_level": 0.80,
        "metadata": {"archetype": "neural_specialist", "role": "embedding", "council_seat": "neural-3"},
    },
    {
        "id": "neu_004_reason",
        "name": "Logos",
        "description": "Reasoning agent — multi-step logical inference and causal chain analysis",
        "capabilities": ["neural_inference", "analysis", "planning"],
        "trust_level": 0.85,
        "metadata": {"archetype": "neural_specialist", "role": "reasoning", "council_seat": "neural-4"},
    },
    {
        "id": "neu_005_align",
        "name": "Aligner",
        "description": "Alignment agent — continuously checks outputs against Maternal Covenant principles",
        "capabilities": ["neural_inference", "analysis", "monitoring"],
        "trust_level": 0.92,
        "metadata": {"archetype": "neural_specialist", "role": "alignment", "council_seat": "neural-5"},
    },
]


async def seed():
    conn = await asyncpg.connect(POSTGRES_DSN)
    now = datetime.now()
    seeded = 0
    skipped = 0

    for agent in BYZANTINE_COUNCIL:
        # Check if already exists
        existing = await conn.fetchrow("SELECT id FROM agents WHERE id = $1", agent["id"])
        if existing:
            skipped += 1
            continue

        await conn.execute(
            """
            INSERT INTO agents
              (id, tenant_id, name, description, capabilities, status,
               trust_level, created_at, last_seen, metadata, relationships,
               performance_score, tasks_completed, tasks_failed)
            VALUES
              ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            agent["id"],
            "default",
            agent["name"],
            agent["description"],
            agent["capabilities"],
            "active",
            agent["trust_level"],
            now,
            now,
            json.dumps(agent["metadata"]),
            json.dumps({}),
            0.5,
            0,
            0,
        )
        seeded += 1
        print(f"  ✅ {agent['name']} ({agent['id']}) — {agent['metadata']['archetype']}")

    await conn.close()
    total = await _count(POSTGRES_DSN)
    print(f"\n🏛️  Byzantine Council seeded: {seeded} new | {skipped} already existed | {total} total agents")


async def _count(dsn):
    conn = await asyncpg.connect(dsn)
    n = await conn.fetchval("SELECT COUNT(*) FROM agents")
    await conn.close()
    return n


if __name__ == "__main__":
    asyncio.run(seed())
