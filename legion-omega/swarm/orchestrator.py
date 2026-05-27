"""
Legion Swarm: 47 Agents × 33 Nodes = 1,551 total
Federated coordination with differential privacy
MEOK AI Labs
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import numpy as np
import redis


@dataclass
class AgentNode:
    agent_id: int
    node_id: int
    status: str  # active, learning, idle, failed
    skill_version: str
    current_task: Optional[str]
    performance_metric: float
    last_heartbeat: float


class LegionSwarm:
    def __init__(self, agent_count: int = 47, nodes_per_agent: int = 33,
                 redis_url: str = "redis://localhost:6379"):
        self.agent_count = agent_count
        self.nodes_per_agent = nodes_per_agent
        self.total_nodes = agent_count * nodes_per_agent
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.agents: Dict[str, AgentNode] = {}
        self.consensus_threshold = 0.67
        self._init_swarm()

    def _init_swarm(self):
        for agent_id in range(1, self.agent_count + 1):
            for node_id in range(1, self.nodes_per_agent + 1):
                key = f"agent-{agent_id:03d}-node-{node_id:03d}"
                node = AgentNode(
                    agent_id=agent_id,
                    node_id=node_id,
                    status="idle",
                    skill_version="1.0.0",
                    current_task=None,
                    performance_metric=0.0,
                    last_heartbeat=time.time()
                )
                self.agents[key] = node
                self.redis.hset(f"node:{key}", mapping=asdict(node))
        print(f"Legion initialized: {self.total_nodes} nodes across {self.agent_count} agents")

    async def federated_learn(self, skill_update: Dict, privacy_budget: float = 1.0):
        noisy_update = self._add_dp_noise(skill_update, privacy_budget)
        await self._gossip_broadcast(noisy_update)
        consensus = await self._wait_for_consensus(noisy_update.get("skill_hash", ""))
        if consensus:
            self._commit_skill(noisy_update)
            print(f"Skill committed: {noisy_update.get('skill_id', 'unknown')}")

    async def _gossip_broadcast(self, message: Dict):
        sample_size = max(1, int(np.log2(self.total_nodes)) + 1)
        targets = np.random.choice(list(self.agents.keys()), size=sample_size, replace=False)
        tasks = [self._send_message(t, message) for t in targets]
        await asyncio.gather(*tasks)

    async def _wait_for_consensus(self, skill_hash: str, timeout: float = 30.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            votes = sum(1 for k in self.agents if self.redis.get(f"vote:{skill_hash}:{k}"))
            if self.total_nodes > 0 and votes / self.total_nodes >= self.consensus_threshold:
                return True
            await asyncio.sleep(0.1)
        return False

    def _add_dp_noise(self, update: Dict, epsilon: float) -> Dict:
        noisy = update.copy()
        if "weights" in noisy:
            scale = 1.0 / epsilon
            noisy["weights"] = [w + np.random.laplace(0, scale) for w in noisy["weights"]]
        return noisy

    async def _send_message(self, target: str, message: Dict):
        self.redis.publish(f"channel:{target}", json.dumps(message))

    def _commit_skill(self, update: Dict):
        skill_id = update.get("skill_id", "unknown")
        h = hashlib.sha256(json.dumps(update).encode()).hexdigest()[:16]
        self.redis.set(f"skill:{skill_id}:{h}", json.dumps(update))

    async def get_status(self) -> Dict:
        statuses: Dict[str, int] = {}
        for node in self.agents.values():
            statuses[node.status] = statuses.get(node.status, 0) + 1
        return {
            "total": self.total_nodes,
            "by_status": statuses,
            "agents": self.agent_count,
            "nodes_per_agent": self.nodes_per_agent
        }
