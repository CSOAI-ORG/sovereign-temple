#!/usr/bin/env python3
"""
SOV3 Enhanced Council Deliberation
Improvements:
- Better voting mechanisms with confidence scores
- Quantum-inspired decision making
- Stakeholder impact analysis
- Dissent tracking and resolution

Run: python sov3_enhanced_council.py demo
"""

import asyncio
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class VoteType(Enum):
    """Types of votes"""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    DELEGATE = "delegate"
    CONDITIONAL = "conditional"  # Approve with conditions


class CouncilRole(Enum):
    """Council member roles"""

    SOVEREIGN = "sovereign"  # Final arbiter
    GUARDIAN = "guardian"  # Safety focused
    SCHOLAR = "scholar"  # Knowledge focused
    BUILDER = "builder"  # Action focused
    ARTIST = "artist"  # Creative focused
    HEALER = "healer"  # Care focused


class Stakeholder(Enum):
    """Stakeholder categories for impact analysis"""

    USER = "user"
    SYSTEM = "system"
    AGENTS = "agents"
    EXTERNAL = "external"
    FUTURE_SELF = "future_self"
    ECOSYSTEM = "ecosystem"


@dataclass
class CouncilMember:
    """Council member representation"""

    role: CouncilRole
    name: str
    expertise: List[str] = field(default_factory=list)
    weight: float = 1.0  # Voting weight
    conviction_strength: float = 1.0  # How strongly they hold positions


@dataclass
class Proposal:
    """Council proposal"""

    proposal_id: str
    title: str
    description: str
    proposer: str
    created_at: str
    urgency: float  # 0-1
    risk_level: float  # 0-1
    conditions: List[str] = field(default_factory=list)


@dataclass
class Vote:
    """Individual vote with reasoning"""

    voter: str
    vote_type: VoteType
    confidence: float  # 0-1 how confident
    reasoning: str
    conditions: List[str] = field(default_factory=list)  # For conditional votes
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ImpactAssessment:
    """Impact analysis on stakeholders"""

    stakeholder: Stakeholder
    impact_score: float  # -1 (negative) to 1 (positive)
    confidence: float  # How certain
    concerns: List[str] = field(default_factory=list)
    mitigation: List[str] = field(default_factory=list)


@dataclass
class CouncilDecision:
    """Final council decision"""

    decision_id: str
    proposal_id: str
    outcome: str  # approved, rejected, tabled, deferred
    votes: List[Vote] = field(default_factory=list)
    impact_assessments: List[ImpactAssessment] = field(default_factory=list)
    dissent_record: List[Dict] = field(default_factory=list)  # Minority opinions
    conditions: List[str] = field(default_factory=list)
    quorum_met: bool = False
    consensus_level: float = 0.0  # 0-1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class QuantumDeliberation:
    """Quantum-inspired multi-perspective deliberation"""

    def __init__(self):
        self.perspectives = [
            "optimistic",
            "pessimistic",
            "neutral",
            "creative",
            "conservative",
        ]

    def superpose_evaluate(self, proposal: Proposal) -> Dict[str, float]:
        """Evaluate proposal from multiple perspectives simultaneously"""
        results = {}

        for perspective in self.perspectives:
            score = self._evaluate_perspective(proposal, perspective)
            results[perspective] = score

        return results

    def _evaluate_perspective(self, proposal: Proposal, perspective: str) -> float:
        """Evaluate from specific perspective"""
        base_score = 0.5

        # Adjust based on perspective and proposal characteristics
        if perspective == "optimistic":
            base_score += (1 - proposal.risk_level) * 0.3
            base_score += proposal.urgency * 0.2
        elif perspective == "pessimistic":
            base_score -= proposal.risk_level * 0.4
            base_score -= 0.1  # Natural skepticism
        elif perspective == "neutral":
            pass  # No adjustment
        elif perspective == "creative":
            base_score += random.random() * 0.2  # Creative solutions
            base_score += 0.1
        elif perspective == "conservative":
            base_score -= proposal.risk_level * 0.3
            base_score -= 0.1

        return max(0, min(1, base_score))

    def collapse_wavefunction(
        self, evaluations: Dict[str, float]
    ) -> Tuple[float, List[str]]:
        """Collapse superposed states into decision with reasoning"""
        weights = {
            "optimistic": 0.2,
            "pessimistic": 0.25,  # Higher weight for safety
            "neutral": 0.25,
            "creative": 0.15,
            "conservative": 0.15,
        }

        weighted_sum = sum(evaluations[p] * weights[p] for p in self.perspectives)

        # Generate collapse explanation
        reasons = []
        if evaluations["pessimistic"] < 0.4:
            reasons.append("Safety concerns from conservative analysis")
        if evaluations["optimistic"] > 0.7:
            reasons.append("High potential upsides identified")
        if evaluations["creative"] > 0.6:
            reasons.append("Creative solutions available")

        return weighted_sum, reasons


class StakeholderAnalyzer:
    """Analyze impact on different stakeholders"""

    def __init__(self):
        self.stakeholders = list(Stakeholder)

    def analyze_impact(self, proposal: Proposal) -> List[ImpactAssessment]:
        """Analyze impact across all stakeholders"""
        assessments = []

        for stakeholder in self.stakeholders:
            impact = self._assess_stakeholder_impact(proposal, stakeholder)
            assessments.append(impact)

        return assessments

    def _assess_stakeholder_impact(
        self, proposal: Proposal, stakeholder: Stakeholder
    ) -> ImpactAssessment:
        """Assess impact on specific stakeholder"""

        # Different stakeholders affected differently based on proposal
        if stakeholder == Stakeholder.USER:
            if proposal.risk_level < 0.3:
                impact = 0.6
                confidence = 0.8
                concerns = []
                mitigation = []
            else:
                impact = -0.3
                confidence = 0.7
                concerns = ["Potential disruption to service"]
                mitigation = ["Phase rollout", "Rollback plan"]

        elif stakeholder == Stakeholder.SYSTEM:
            if proposal.risk_level > 0.5:
                impact = -0.4
                confidence = 0.8
                concerns = ["Stability risk"]
                mitigation = ["Load testing", "Monitoring"]
            else:
                impact = 0.2
                confidence = 0.7
                concerns = []
                mitigation = []

        elif stakeholder == Stakeholder.AGENTS:
            if "agent" in proposal.description.lower():
                impact = 0.5
                confidence = 0.6
                concerns = []
                mitigation = []
            else:
                impact = 0.1
                confidence = 0.5
                concerns = []
                mitigation = []

        elif stakeholder == Stakeholder.EXTERNAL:
            impact = -0.1 if proposal.risk_level > 0.5 else 0.1
            confidence = 0.4  # Less predictable
            concerns = ["Third-party dependencies"]
            mitigation = ["Contingency plans"]

        elif stakeholder == Stakeholder.FUTURE_SELF:
            # Long-term impact assessment
            if proposal.urgency > 0.7:
                impact = 0.3  # Future benefits from acting now
            else:
                impact = 0.1
            confidence = 0.5
            concerns = []
            mitigation = []

        elif stakeholder == Stakeholder.ECOSYSTEM:
            # Broader ecosystem impact
            if (
                "open" in proposal.description.lower()
                or "share" in proposal.description.lower()
            ):
                impact = 0.4
                confidence = 0.6
                concerns = []
                mitigation = []
            else:
                impact = 0.0
                confidence = 0.5
                concerns = []
                mitigation = []

        return ImpactAssessment(
            stakeholder=stakeholder,
            impact_score=impact,
            confidence=confidence,
            concerns=concerns,
            mitigation=mitigation,
        )


class EnhancedCouncil:
    """
    Enhanced Council with:
    - Quantum deliberation
    - Stakeholder analysis
    - Dissent tracking
    - Better voting mechanisms
    """

    def __init__(self):
        self.members = self._create_council()
        self.proposals: List[Proposal] = []
        self.decisions: List[CouncilDecision] = []
        self.quantum = QuantumDeliberation()
        self.stakeholder_analyzer = StakeholderAnalyzer()

    def _create_council(self) -> Dict[str, CouncilMember]:
        """Create council members"""
        return {
            "sovereign": CouncilMember(
                role=CouncilRole.SOVEREIGN,
                name="Sovereign",
                expertise=["ethics", "strategy", "final_arbiter"],
                weight=2.0,  # Higher weight
            ),
            "guardian": CouncilMember(
                role=CouncilRole.GUARDIAN,
                name="Guardian",
                expertise=["safety", "risk", "protection"],
                weight=1.5,
            ),
            "scholar": CouncilMember(
                role=CouncilRole.SCHOLAR,
                name="Scholar",
                expertise=["knowledge", "analysis", "research"],
                weight=1.0,
            ),
            "builder": CouncilMember(
                role=CouncilRole.BUILDER,
                name="Builder",
                expertise=["execution", "implementation", "action"],
                weight=1.0,
            ),
            "artist": CouncilMember(
                role=CouncilRole.ARTIST,
                name="Artist",
                expertise=["creativity", "aesthetics", "novelty"],
                weight=1.0,
            ),
            "healer": CouncilMember(
                role=CouncilRole.HEALER,
                name="Healer",
                expertise=["care", "empathy", "wellbeing"],
                weight=1.5,  # Higher weight for care decisions
            ),
        }

    def submit_proposal(
        self,
        title: str,
        description: str,
        proposer: str,
        urgency: float = 0.5,
        risk_level: float = 0.5,
    ) -> Proposal:
        """Submit a proposal to council"""
        proposal = Proposal(
            proposal_id=f"prop_{len(self.proposals) + 1}",
            title=title,
            description=description,
            proposer=proposer,
            created_at=datetime.now().isoformat(),
            urgency=urgency,
            risk_level=risk_level,
        )
        self.proposals.append(proposal)
        return proposal

    def cast_vote(
        self,
        proposal: Proposal,
        voter: str,
        vote_type: VoteType,
        reasoning: str,
        confidence: float = 0.8,
        conditions: List[str] = None,
    ) -> Vote:
        """Cast a vote with reasoning"""
        return Vote(
            voter=voter,
            vote_type=vote_type,
            confidence=confidence,
            reasoning=reasoning,
            conditions=conditions or [],
        )

    async def deliberate(
        self, proposal: Proposal, votes: List[Vote]
    ) -> CouncilDecision:
        """Deliberate and reach decision"""
        decision_id = f"dec_{len(self.decisions) + 1}"

        # Quantum deliberation
        evaluations = self.quantum.superpose_evaluate(proposal)
        quantum_score, quantum_reasons = self.quantum.collapse_wavefunction(evaluations)

        # Stakeholder analysis
        impact_assessments = self.stakeholder_analyzer.analyze_impact(proposal)

        # Calculate weighted vote outcome
        total_weight = 0
        weighted_votes = 0

        for vote in votes:
            weight = self.members.get(
                vote.voter, CouncilMember(CouncilRole.SCHOLAR, "unknown")
            ).weight
            vote_value = (
                1
                if vote.vote_type == VoteType.APPROVE
                else (-1 if vote.vote_type == VoteType.REJECT else 0)
            )

            total_weight += weight * vote.confidence
            weighted_votes += vote_value * weight * vote.confidence

        # Consensus level
        approval_votes = sum(1 for v in votes if v.vote_type == VoteType.APPROVE)
        consensus_level = approval_votes / max(len(votes), 1)

        # Determine outcome
        if total_weight < 3:  # Quorum not met
            outcome = "deferred"
            quorum_met = False
        elif weighted_votes > total_weight * 0.5:
            outcome = "approved"
            quorum_met = True
        elif weighted_votes < -total_weight * 0.3:
            outcome = "rejected"
            quorum_met = True
        else:
            outcome = "tabled"
            quorum_met = True

        # Record dissent
        dissent_record = []
        for vote in votes:
            if vote.vote_type == VoteType.REJECT and vote.confidence > 0.7:
                dissent_record.append(
                    {
                        "voter": vote.voter,
                        "reason": vote.reasoning,
                        "strength": vote.confidence,
                    }
                )

        # Extract conditions from votes
        conditions = []
        for vote in votes:
            if vote.vote_type == VoteType.CONDITIONAL:
                conditions.extend(vote.conditions)

        decision = CouncilDecision(
            decision_id=decision_id,
            proposal_id=proposal.proposal_id,
            outcome=outcome,
            votes=votes,
            impact_assessments=impact_assessments,
            dissent_record=dissent_record,
            conditions=conditions,
            quorum_met=quorum_met,
            consensus_level=consensus_level,
        )

        self.decisions.append(decision)

        return decision

    def get_deliberation_summary(self) -> Dict:
        """Get summary of council deliberations"""
        if not self.decisions:
            return {"total_decisions": 0, "approved": 0, "rejected": 0}

        approved = sum(1 for d in self.decisions if d.outcome == "approved")
        rejected = sum(1 for d in self.decisions if d.outcome == "rejected")

        return {
            "total_decisions": len(self.decisions),
            "approved": approved,
            "rejected": rejected,
            "approval_rate": approved / len(self.decisions),
            "dissent_count": sum(len(d.dissent_record) for d in self.decisions),
            "quorum_rate": sum(1 for d in self.decisions if d.quorum_met)
            / len(self.decisions),
        }


async def demo():
    """Demo enhanced council"""
    print("=" * 50)
    print("SOV3 Enhanced Council Deliberation Demo")
    print("=" * 50)

    council = EnhancedCouncil()

    # Submit proposals
    print("\n1. Submitting proposals...")
    prop1 = council.submit_proposal(
        title="Enable Ralph Mode",
        description="Allow autonomous task execution without human approval for trivial tasks",
        proposer="research_agent",
        urgency=0.7,
        risk_level=0.4,
    )
    print(
        f"   Proposal: {prop1.title} (urgency: {prop1.urgency}, risk: {prop1.risk_level})"
    )

    # Quantum deliberation
    print("\n2. Quantum deliberation...")
    evaluations = council.quantum.superpose_evaluate(prop1)
    for pers, score in evaluations.items():
        print(f"   {pers}: {score:.2f}")

    score, reasons = council.quantum.collapse_wavefunction(evaluations)
    print(f"   Collapsed score: {score:.2f}")
    print(f"   Reasons: {reasons}")

    # Stakeholder analysis
    print("\n3. Stakeholder impact analysis...")
    impacts = council.stakeholder_analyzer.analyze_impact(prop1)
    for imp in impacts:
        print(
            f"   {imp.stakeholder.value}: {imp.impact_score:+.2f} (confidence: {imp.confidence:.2f})"
        )

    # Cast votes
    print("\n4. Casting votes...")
    votes = [
        council.cast_vote(
            prop1, "sovereign", VoteType.APPROVE, "Benefits outweigh risks", 0.9
        ),
        council.cast_vote(
            prop1,
            "guardian",
            VoteType.CONDITIONAL,
            "Need monitoring",
            0.8,
            conditions=["require_logging"],
        ),
        council.cast_vote(prop1, "scholar", VoteType.APPROVE, "Worth trying", 0.7),
        council.cast_vote(
            prop1, "healer", VoteType.REJECT, "Too risky for users", 0.85
        ),
    ]

    for vote in votes:
        print(
            f"   {vote.voter}: {vote.vote_type.value} ({vote.confidence:.0%} confidence)"
        )

    # Deliberate
    print("\n5. Final deliberation...")
    decision = await council.deliberate(prop1, votes)
    print(f"   Outcome: {decision.outcome}")
    print(f"   Quorum: {decision.quorum_met}")
    print(f"   Consensus: {decision.consensus_level:.0%}")
    print(f"   Dissent: {len(decision.dissent_record)} minority opinions")

    # Summary
    print("\n6. Council summary:")
    summary = council.get_deliberation_summary()
    for k, v in summary.items():
        print(f"   {k}: {v}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo())
    else:
        print("Usage: python sov3_enhanced_council.py demo")
