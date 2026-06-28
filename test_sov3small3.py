"""Tests for SOV3small3 master — the 4-tier cascade + speculative decoding.

Covers:
- ModelTier enum
- TIER_DEFINITIONS, CONFIDENCE_THRESHOLDS, TIER_CALIBRATION constants
- SOV3SMALL3_VMS has all 33+4 VMs
- SOV3SMALL3_CONFIGS has all 3 configs
- BENCHMARK_QUERIES has 10 queries
- ConfidenceEstimator: simple queries get high conf, complex get low
- SpeculativeDecoder: produces accepted/rejected counts
- SOV3small3Master.route(): escalates when confidence < threshold
- Master benchmark produces tier-match scores
"""
import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sov3small3 import (
    ModelTier, TIER_DEFINITIONS, CONFIDENCE_THRESHOLDS, TIER_CALIBRATION,
    SOV3SMALL3_VMS, SOV3SMALL3_CONFIGS, BENCHMARK_QUERIES,
    ConfidenceEstimator, SpeculativeDecoder, SOV3small3Master,
    handle_sov3small3_master_status, handle_sov3small3_master_benchmark,
    handle_sov3small3_speculative_demo,
)


def test_model_tier_enum():
    """The 4 tiers must be present."""
    tiers = list(ModelTier)
    assert len(tiers) == 4
    assert ModelTier.TIER_1 in tiers
    assert ModelTier.TIER_2 in tiers
    assert ModelTier.TIER_3 in tiers
    assert ModelTier.TIER_4 in tiers


def test_tier_definitions_complete():
    """Each tier must have name, models, deployment, latency, cost, share, use_case."""
    for tier in ModelTier:
        d = TIER_DEFINITIONS[tier]
        assert "name" in d, f"{tier.value} missing name"
        assert "models" in d, f"{tier.value} missing models"
        assert "deployment" in d, f"{tier.value} missing deployment"
        assert "latency_target_ms" in d, f"{tier.value} missing latency_target_ms"
        assert "cost_per_1k_tokens_usd" in d, f"{tier.value} missing cost"
        assert "expected_query_share" in d, f"{tier.value} missing share"
        assert "use_case" in d, f"{tier.value} missing use_case"
        assert len(d["models"]) >= 1


def test_tier_query_shares_sum_to_1():
    """The 4 expected_query_shares must sum to ~1.0."""
    total = sum(TIER_DEFINITIONS[t]["expected_query_share"] for t in ModelTier)
    assert 0.99 <= total <= 1.01, f"shares sum to {total}, expected ~1.0"


def test_confidence_thresholds_monotonic():
    """Higher tiers should have LOWER confidence thresholds (cascade accepts them as final)."""
    t1 = CONFIDENCE_THRESHOLDS[ModelTier.TIER_1]
    t2 = CONFIDENCE_THRESHOLDS[ModelTier.TIER_2]
    t3 = CONFIDENCE_THRESHOLDS[ModelTier.TIER_3]
    assert t1 > t2 > t3, f"thresholds should be monotonic decreasing: {t1}, {t2}, {t3}"


def test_tier_calibration_increases_with_tier():
    """Larger models need less calibration (they're already well-calibrated)."""
    c1 = TIER_CALIBRATION[ModelTier.TIER_1]
    c2 = TIER_CALIBRATION[ModelTier.TIER_2]
    c3 = TIER_CALIBRATION[ModelTier.TIER_3]
    c4 = TIER_CALIBRATION[ModelTier.TIER_4]
    assert c1 <= c2 <= c3 <= c4, f"calibration should be monotonic increasing: {c1}, {c2}, {c3}, {c4}"


def test_vms_have_all_categories():
    """We should have the 9 sovereign + 13 districts + 11 layers + 1 meok-master = 34 VMs."""
    assert len(SOV3SMALL3_VMS) >= 33
    # Spot-check categories
    assert "meok-master" in SOV3SMALL3_VMS
    assert "koikeeper" in SOV3SMALL3_VMS
    assert "defoneos-1" in SOV3SMALL3_VMS
    # Each VM has the required fields
    for name, vm in SOV3SMALL3_VMS.items():
        assert "ip" in vm, f"{name} missing ip"
        assert "region" in vm, f"{name} missing region"
        assert "spec" in vm, f"{name} missing spec"
        assert "tier" in vm, f"{name} missing tier"
        assert "purpose" in vm, f"{name} missing purpose"


def test_three_configs():
    """A_speed / B_balanced / C_quality must all exist."""
    assert "A_speed" in SOV3SMALL3_CONFIGS
    assert "B_balanced" in SOV3SMALL3_CONFIGS
    assert "C_quality" in SOV3SMALL3_CONFIGS
    # Quality config should have all 4 tiers; speed only 1
    assert "primary_tier" in SOV3SMALL3_CONFIGS["A_speed"]
    assert "primary_tiers" in SOV3SMALL3_CONFIGS["C_quality"]
    assert len(SOV3SMALL3_CONFIGS["C_quality"]["primary_tiers"]) == 4


def test_ten_benchmark_queries():
    """10 queries, each with query, category, expected_latency, expected_tier."""
    assert len(BENCHMARK_QUERIES) == 10
    categories = {q["category"] for q in BENCHMARK_QUERIES}
    # Diverse categories
    assert "knowledge" in categories
    assert "compliance" in categories
    assert "ai_governance" in categories
    for q in BENCHMARK_QUERIES:
        assert "query" in q
        assert "category" in q
        assert "expected_latency" in q
        assert "expected_tier" in q
        assert q["expected_tier"] in ModelTier


def test_confidence_estimator_simple_query_high_conf():
    """A simple 'knowledge' query with a 30-word response should get HIGH confidence."""
    est = ConfidenceEstimator()
    r = est.ensemble_confidence(
        "What is the EU AI Act Article 50?",
        "The EU AI Act Article 50 covers transparency obligations for AI systems. " * 5,
        task_type="knowledge",
    )
    assert r > 0.85, f"simple query should get high confidence, got {r}"


def test_confidence_estimator_complex_query_low_conf_at_tier1():
    """A complex 'compliance' query with a 30-word response should get LOW confidence at Tier 1."""
    est = ConfidenceEstimator()
    r = est.ensemble_confidence(
        "Audit Monzo Bank's credit scoring AI compliance",
        "Compliance audit: 8/10 controls satisfied, 2 gaps in human oversight.",
        task_type="compliance",
    )
    assert r < 0.85, f"complex query at Tier 1 length should get low confidence, got {r}"


def test_speculative_decoder_basic():
    """Speculative decoder should produce accepted/rejected counts + speedup."""
    sd = SpeculativeDecoder()
    r = sd.speculative_generate("What is the EU AI Act?")
    assert "accepted" in r
    assert "rejected" in r
    assert "speedup_x" in r
    assert r["accepted"] + r["rejected"] == sd.k
    assert r["speedup_x"] > 0


def test_master_routes_simple_query_to_tier1():
    """A simple query should NOT escalate."""
    async def run():
        m = SOV3small3Master("C_quality")  # has all 4 tiers
        r = await m.route("What is the EU AI Act Article 50?", task_type="knowledge")
        return r
    r = asyncio.run(run())
    assert r.tier == ModelTier.TIER_1, f"simple query should stay on Tier 1, got {r.tier.value}"


def test_master_escalates_complex_query():
    """A complex query should escalate to Tier 3+."""
    async def run():
        m = SOV3small3Master("C_quality")
        r = await m.route("Audit Monzo Bank's credit scoring AI compliance",
                          task_type="compliance")
        return r
    r = asyncio.run(run())
    assert r.tier in (ModelTier.TIER_3, ModelTier.TIER_4), f"complex query should escalate, got {r.tier.value}"


def test_master_sigil_hash_present():
    """Every result must have a SIGIL hash for audit."""
    async def run():
        m = SOV3small3Master("C_quality")
        r = await m.route("test", task_type="knowledge")
        return r
    r = asyncio.run(run())
    assert r.sigil_hash
    assert len(r.sigil_hash) == 16  # truncated sha256


def test_master_status():
    """The status handler must return the full fleet info."""
    s = handle_sov3small3_master_status({})
    assert "tiers" in s
    assert "configs" in s
    assert "total_vms" in s
    assert s["total_vms"] >= 33
    for tier, info in s["tiers"].items():
        assert "vms" in info
        assert "models" in info
        assert "latency_target_ms" in info


def test_master_benchmark_3_configs_10_queries():
    """The benchmark must run 3 configs × 10 queries."""
    r = asyncio.run(handle_sov3small3_master_benchmark({}))
    assert "results" in r
    assert len(r["results"]) == 3
    for config_key, r_data in r["results"].items():
        assert r_data["total"] == 10
        assert r_data["passed"] + (r_data["total"] - r_data["passed"]) == 10
        assert "tier_distribution" in r_data
        assert "total_cost_usd" in r_data


def test_speculative_demo():
    """The speculative demo should return 10 demos with speedups."""
    r = asyncio.run(handle_sov3small3_speculative_demo({}))
    assert "demos" in r
    assert len(r["demos"]) == 10
    for d in r["demos"]:
        assert d["speedup_x"] > 0
        assert 0 < d["acceptance_rate"] <= 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))