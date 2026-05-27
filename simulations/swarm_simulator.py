"""
Swarm Simulator — Monte Carlo simulation for SOV3 agent topology.
Inspired by EvoMap + Swarms mesh simulation.
Answer "what if I add 10 haulage agents?" before spending hardware money.
"""
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class AgentNode:
    id: str
    skills: List[str]
    compute_tier: str  # edge, medium, high
    trust_score: float = 1.0
    failure_rate: float = 0.05
    latency_ms: float = 50.0


@dataclass
class SimulationResult:
    scenario: str
    n_runs: int
    agent_count: int
    mean_consensus_time_ms: float
    p50_consensus_time_ms: float
    p99_consensus_time_ms: float
    task_success_rate: float
    optimal_cluster_size: int
    bottleneck_agent: Optional[str]
    failure_scenarios: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "n_runs": self.n_runs,
            "agent_count": self.agent_count,
            "mean_consensus_time_ms": round(self.mean_consensus_time_ms, 1),
            "p50_consensus_time_ms": round(self.p50_consensus_time_ms, 1),
            "p99_consensus_time_ms": round(self.p99_consensus_time_ms, 1),
            "task_success_rate": round(self.task_success_rate, 4),
            "optimal_cluster_size": self.optimal_cluster_size,
            "bottleneck_agent": self.bottleneck_agent,
            "failure_scenarios": self.failure_scenarios,
        }


class SwarmSimulator:
    """
    Monte Carlo simulation engine for multi-agent governance.
    """

    def __init__(self, agents: List[AgentNode], topology: str = "mesh"):
        self.agents = agents
        self.topology = topology
        self.quorum = max(2, int(len(agents) * 0.67))  # 2/3 quorum default

    def _simulate_run(
        self,
        task_distribution: str = "poisson",
        failure_rate: float = 0.05,
        latency_model: str = "libp2p_gossip",
    ) -> Dict[str, Any]:
        active = [a for a in self.agents if random.random() > failure_rate]
        if len(active) < self.quorum:
            return {"success": False, "consensus_time_ms": float("inf"), "bottleneck": None}

        # Latency model
        if latency_model == "libp2p_gossip":
            base_latency = max(a.latency_ms for a in active) * 3  # 3 hops gossip
        elif latency_model == "star":
            base_latency = max(a.latency_ms for a in active) * 2
        else:
            base_latency = sum(a.latency_ms for a in active) / len(active)

        # Task distribution adds variance
        if task_distribution == "poisson":
            variance = np.random.poisson(2) * 20
        else:
            variance = random.gauss(0, 30)

        consensus_time = base_latency + variance + random.gauss(0, 15)
        consensus_time = max(10, consensus_time)

        # Find bottleneck (highest latency agent)
        bottleneck = max(active, key=lambda a: a.latency_ms).id if active else None

        return {
            "success": len(active) >= self.quorum,
            "consensus_time_ms": consensus_time,
            "bottleneck": bottleneck,
            "active_agents": len(active),
        }

    def run(
        self,
        scenario: str = "baseline",
        n_runs: int = 1000,
        task_distribution: str = "poisson",
        failure_rate: float = 0.05,
        latency_model: str = "libp2p_gossip",
    ) -> SimulationResult:
        results = [
            self._simulate_run(task_distribution, failure_rate, latency_model)
            for _ in range(n_runs)
        ]

        times = [r["consensus_time_ms"] for r in results if r["success"]]
        successes = [r for r in results if r["success"]]

        if not times:
            return SimulationResult(
                scenario=scenario,
                n_runs=n_runs,
                agent_count=len(self.agents),
                mean_consensus_time_ms=float("inf"),
                p50_consensus_time_ms=float("inf"),
                p99_consensus_time_ms=float("inf"),
                task_success_rate=0.0,
                optimal_cluster_size=0,
                bottleneck_agent=None,
                failure_scenarios=["Quorum never reached"],
            )

        # Find optimal cluster size by testing subsets
        best_size = len(self.agents)
        best_time = float("inf")
        for size in range(self.quorum, len(self.agents) + 1):
            subset_times = [
                r["consensus_time_ms"]
                for r in results
                if r["success"] and r["active_agents"] <= size
            ]
            if subset_times:
                avg = np.mean(subset_times)
                if avg < best_time:
                    best_time = avg
                    best_size = size

        # Bottleneck frequency
        bottlenecks = [r["bottleneck"] for r in successes if r["bottleneck"]]
        most_common_bottleneck = max(set(bottlenecks), key=bottlenecks.count) if bottlenecks else None

        return SimulationResult(
            scenario=scenario,
            n_runs=n_runs,
            agent_count=len(self.agents),
            mean_consensus_time_ms=float(np.mean(times)),
            p50_consensus_time_ms=float(np.percentile(times, 50)),
            p99_consensus_time_ms=float(np.percentile(times, 99)),
            task_success_rate=len(successes) / n_runs,
            optimal_cluster_size=best_size,
            bottleneck_agent=most_common_bottleneck,
        )

    @staticmethod
    def from_topology_yaml(path: str) -> "SwarmSimulator":
        """Load agent topology from a YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        agents = [
            AgentNode(
                id=a["id"],
                skills=a.get("skills", []),
                compute_tier=a.get("compute", "medium"),
                trust_score=a.get("trust", 1.0),
                failure_rate=a.get("failure_rate", 0.05),
                latency_ms=a.get("latency_ms", 50.0),
            )
            for a in data.get("agents", [])
        ]
        return SwarmSimulator(agents, topology=data.get("topology", "mesh"))


def simulate_sov3_generals() -> SimulationResult:
    """Quick-start simulation with the 47 Generals topology."""
    agents = [
        AgentNode("council_of_ai", ["governance", "audit"], "high", 1.0, 0.02, 30),
        AgentNode("grabhire", ["fleet", "route"], "medium", 0.9, 0.05, 60),
        AgentNode("muckaway", ["waste", "compliance"], "medium", 0.9, 0.05, 60),
        AgentNode("asimov", ["locomotion", "vision"], "edge", 0.8, 0.08, 120),
        AgentNode("iokfarm", ["aquaponics", "sensor"], "edge", 0.85, 0.07, 100),
        AgentNode("jarvis", ["voice", "orchestration"], "high", 1.0, 0.01, 20),
        AgentNode("sophie", ["empathy", "creative"], "medium", 0.95, 0.03, 40),
        AgentNode("sov3_guardian", ["security", "care"], "high", 1.0, 0.01, 25),
    ]
    # Scale to 33 nodes with variations
    for i in range(25):
        agents.append(
            AgentNode(
                f"agent_{i}",
                skills=[random.choice(["fleet", "waste", "sensor", "compliance", "route"])],
                compute_tier=random.choice(["edge", "medium"]),
                trust_score=round(random.uniform(0.75, 0.95), 2),
                failure_rate=round(random.uniform(0.04, 0.08), 2),
                latency_ms=random.uniform(50, 150),
            )
        )

    sim = SwarmSimulator(agents, topology="mesh")
    return sim.run(
        scenario="sov3_33_node_mesh",
        n_runs=1000,
        task_distribution="poisson",
        failure_rate=0.05,
        latency_model="libp2p_gossip",
    )


if __name__ == "__main__":
    result = simulate_sov3_generals()
    import json
    print(json.dumps(result.to_dict(), indent=2))
