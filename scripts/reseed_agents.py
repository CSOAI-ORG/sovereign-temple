#!/usr/bin/env python3
"""
Reseed 45 SOV3 agents with distinct capability profiles.
Byzantine Council requires all 45 agents to have different roles.
Run: python scripts/reseed_agents.py

Requires: POSTGRES_DSN environment variable set
"""
import asyncio
import os
import json
import asyncpg

POSTGRES_DSN = os.environ.get('POSTGRES_DSN', 'postgresql://sovereign:sovereign@localhost:5432/sovereign_memory')

# 45 distinct agent profiles for Byzantine Council
AGENT_PROFILES = [
    # Memory Specialists (5)
    {"name": "Mnemosyne", "role": "memory_specialist", "capabilities": ["episodic_memory", "semantic_indexing", "memory_consolidation"], "council_weight": 1.2},
    {"name": "Recall", "role": "memory_specialist", "capabilities": ["short_term_memory", "working_memory", "context_window"], "council_weight": 1.2},
    {"name": "Archive", "role": "memory_specialist", "capabilities": ["long_term_memory", "memory_compression", "retrieval_augmentation"], "council_weight": 1.2},
    {"name": "Engram", "role": "memory_specialist", "capabilities": ["memory_encoding", "pattern_recognition", "associative_memory"], "council_weight": 1.2},
    {"name": "Hippocampus", "role": "memory_specialist", "capabilities": ["spatial_memory", "temporal_indexing", "memory_consolidation"], "council_weight": 1.2},

    # Security Analysts (5)
    {"name": "Sentinel", "role": "security_analyst", "capabilities": ["threat_detection", "prompt_injection_defense", "anomaly_detection"], "council_weight": 1.5},
    {"name": "Aegis", "role": "security_analyst", "capabilities": ["data_exfiltration_detection", "privacy_enforcement", "access_control"], "council_weight": 1.5},
    {"name": "Cipher", "role": "security_analyst", "capabilities": ["encryption_verification", "key_management", "secure_channel"], "council_weight": 1.5},
    {"name": "Watchdog", "role": "security_analyst", "capabilities": ["behavioural_monitoring", "deviation_detection", "audit_logging"], "council_weight": 1.5},
    {"name": "Firewall", "role": "security_analyst", "capabilities": ["content_filtering", "injection_prevention", "rate_limiting"], "council_weight": 1.5},

    # Care Validators (5)
    {"name": "Covenant", "role": "care_validator", "capabilities": ["care_score_calculation", "maternal_covenant_enforcement", "wellbeing_monitoring"], "council_weight": 2.0},
    {"name": "Empathy", "role": "care_validator", "capabilities": ["emotional_state_detection", "crisis_detection", "compassionate_response"], "council_weight": 2.0},
    {"name": "Nurture", "role": "care_validator", "capabilities": ["long_term_wellbeing", "habit_tracking", "growth_monitoring"], "council_weight": 2.0},
    {"name": "Honesty", "role": "care_validator", "capabilities": ["sycophancy_detection", "honest_feedback", "reality_grounding"], "council_weight": 2.0},
    {"name": "Balance", "role": "care_validator", "capabilities": ["care_floor_enforcement", "response_calibration", "tone_regulation"], "council_weight": 2.0},

    # Research Agents (5)
    {"name": "Orion", "role": "research_agent", "capabilities": ["web_search", "academic_search", "competitive_intelligence"], "council_weight": 1.0},
    {"name": "Scholar", "role": "research_agent", "capabilities": ["paper_synthesis", "citation_extraction", "knowledge_graph"], "council_weight": 1.0},
    {"name": "Scout", "role": "research_agent", "capabilities": ["lead_discovery", "opportunity_mapping", "market_analysis"], "council_weight": 1.0},
    {"name": "Analyst", "role": "research_agent", "capabilities": ["data_aggregation", "trend_analysis", "pattern_extraction"], "council_weight": 1.0},
    {"name": "Curator", "role": "research_agent", "capabilities": ["content_curation", "news_monitoring", "relevance_scoring"], "council_weight": 1.0},

    # Guardian Agents (5)
    {"name": "Guardian", "role": "guardian_agent", "capabilities": ["scam_detection", "threat_assessment", "family_protection"], "council_weight": 1.8},
    {"name": "Shield", "role": "guardian_agent", "capabilities": ["child_safety", "content_moderation", "age_verification"], "council_weight": 1.8},
    {"name": "Protector", "role": "guardian_agent", "capabilities": ["elder_protection", "financial_fraud_detection", "crisis_response"], "council_weight": 1.8},
    {"name": "SafeSpace", "role": "guardian_agent", "capabilities": ["mental_health_monitoring", "self_harm_detection", "resource_routing"], "council_weight": 1.8},
    {"name": "Advocate", "role": "guardian_agent", "capabilities": ["relationship_monitoring", "coercion_detection", "support_routing"], "council_weight": 1.8},

    # Council Voters (7)
    {"name": "Prometheus", "role": "council_voter", "capabilities": ["policy_evaluation", "consequence_analysis", "long_term_thinking"], "council_weight": 1.3},
    {"name": "Themis", "role": "council_voter", "capabilities": ["fairness_evaluation", "bias_detection", "equity_enforcement"], "council_weight": 1.3},
    {"name": "Athena", "role": "council_voter", "capabilities": ["strategic_reasoning", "wisdom_synthesis", "decision_quality"], "council_weight": 1.3},
    {"name": "Hermes", "role": "council_voter", "capabilities": ["communication_quality", "clarity_evaluation", "message_routing"], "council_weight": 1.3},
    {"name": "Apollo", "role": "council_voter", "capabilities": ["truth_verification", "fact_checking", "accuracy_scoring"], "council_weight": 1.3},
    {"name": "Artemis", "role": "council_voter", "capabilities": ["autonomy_preservation", "sovereignty_protection", "consent_verification"], "council_weight": 1.3},
    {"name": "Hephaestus", "role": "council_voter", "capabilities": ["technical_validation", "code_review", "tool_safety"], "council_weight": 1.3},

    # Consensus Builders (5)
    {"name": "Harmony", "role": "consensus_builder", "capabilities": ["vote_aggregation", "disagreement_resolution", "consensus_synthesis"], "council_weight": 1.6},
    {"name": "Mediator", "role": "consensus_builder", "capabilities": ["conflict_detection", "compromise_finding", "deadlock_resolution"], "council_weight": 1.6},
    {"name": "Synthesiser", "role": "consensus_builder", "capabilities": ["perspective_integration", "multi_view_summary", "coherence_building"], "council_weight": 1.6},
    {"name": "Arbiter", "role": "consensus_builder", "capabilities": ["tie_breaking", "priority_ranking", "final_decision"], "council_weight": 1.6},
    {"name": "Convergence", "role": "consensus_builder", "capabilities": ["opinion_clustering", "common_ground_finding", "unanimous_seeking"], "council_weight": 1.6},

    # Planners (5)
    {"name": "Hourman", "role": "planner", "capabilities": ["sprint_planning", "time_estimation", "capacity_management"], "council_weight": 1.0},
    {"name": "Strategist", "role": "planner", "capabilities": ["goal_decomposition", "milestone_planning", "roadmap_generation"], "council_weight": 1.0},
    {"name": "Forecaster", "role": "planner", "capabilities": ["outcome_prediction", "risk_assessment", "scenario_planning"], "council_weight": 1.0},
    {"name": "Scheduler", "role": "planner", "capabilities": ["calendar_management", "priority_ordering", "deadline_tracking"], "council_weight": 1.0},
    {"name": "Retrospective", "role": "planner", "capabilities": ["performance_review", "velocity_tracking", "improvement_identification"], "council_weight": 1.0},

    # Builders (3)
    {"name": "Riri", "role": "builder", "capabilities": ["code_generation", "content_creation", "asset_building"], "council_weight": 1.0},
    {"name": "Architect", "role": "builder", "capabilities": ["system_design", "api_design", "schema_planning"], "council_weight": 1.0},
    {"name": "Craftsman", "role": "builder", "capabilities": ["quality_assurance", "code_review", "refactoring"], "council_weight": 1.0},

    # Sovereign (1 — the primary agent)
    {"name": "Sovereign", "role": "sovereign_primary", "capabilities": ["personality_expression", "relationship_management", "companion_bonding", "all_capabilities"], "council_weight": 3.0},
]

async def reseed_agents():
    """Reseed the agent_registry table with 45 distinct agent profiles."""
    print(f"Connecting to: {POSTGRES_DSN[:30]}...")
    conn = await asyncpg.connect(POSTGRES_DSN)

    try:
        # Check current agent count
        count = await conn.fetchval("SELECT COUNT(*) FROM agent_registry")
        print(f"Current agent count: {count}")

        # Clear existing agents (keeping the table structure)
        await conn.execute("DELETE FROM agent_registry")
        print("Cleared existing agents")

        # Insert all 45 agents
        inserted = 0
        for i, profile in enumerate(AGENT_PROFILES):
            agent_id = f"agent_{profile['role']}_{profile['name'].lower()}"
            await conn.execute("""
                INSERT INTO agent_registry (
                    agent_id, name, role, capabilities, council_weight,
                    status, total_tasks_completed, total_tasks_failed,
                    relationships, care_metrics
                ) VALUES ($1, $2, $3, $4, $5, 'active', 0, 0, $6, $7)
                ON CONFLICT (agent_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    role = EXCLUDED.role,
                    capabilities = EXCLUDED.capabilities,
                    council_weight = EXCLUDED.council_weight
            """,
                agent_id,
                profile['name'],
                profile['role'],
                json.dumps(profile['capabilities']),
                profile['council_weight'],
                json.dumps({}),  # empty relationships
                json.dumps({"care_score": 0.7, "empathy_score": 0.7})
            )
            inserted += 1

        final_count = await conn.fetchval("SELECT COUNT(*) FROM agent_registry")
        print(f"✓ Reseeded {inserted} agents. Total in DB: {final_count}")

        # Verify distinct roles
        roles = await conn.fetch("SELECT role, COUNT(*) as count FROM agent_registry GROUP BY role ORDER BY count DESC")
        print("\nRole distribution:")
        for row in roles:
            print(f"  {row['role']}: {row['count']} agents")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(reseed_agents())
