"""
Agent Message Bus — A2A-inspired inter-agent communication
============================================================
The missing piece: agents can now discover each other, send messages,
delegate tasks, and vote on decisions.

MCP connects agents to tools. This connects agents to each other.

Architecture:
  Agent A → AgentBus.send(agent_b, task) → Agent B executes → result back

  3-tier hierarchy:
  Tier 1 (Orchestrators): SOV3, Care Guardian, Crisis Monitor
  Tier 2 (Department Heads): Memory, Neural, Creative, Security, Research, Agents
  Tier 3 (Specialists): 40+ workers in departments
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

log = logging.getLogger("agent_bus")


@dataclass
class AgentCard:
    """A2A-style agent capability card."""
    id: str
    name: str
    tier: int  # 1=orchestrator, 2=department, 3=specialist
    department: str
    capabilities: List[str]
    description: str
    trust_level: float = 0.8
    busy: bool = False
    last_task_time: float = 0
    tasks_completed: int = 0
    tasks_failed: int = 0


@dataclass
class AgentMessage:
    """Message between agents."""
    from_agent: str
    to_agent: str
    msg_type: str  # "task", "result", "query", "vote", "broadcast"
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: f"msg_{int(time.time()*1000)}")


class AgentBus:
    """Central message bus for inter-agent communication."""

    def __init__(self):
        self.agents: Dict[str, AgentCard] = {}
        self.queues: Dict[str, asyncio.Queue] = {}
        self.message_log: List[AgentMessage] = []
        self._setup_default_agents()

    def _setup_default_agents(self):
        """Register the default agent hierarchy."""
        defaults = [
            # Tier 1: Orchestrators
            AgentCard("sov3", "SOV3 Orchestrator", 1, "core", ["orchestration", "routing", "consciousness"], "Central sovereign orchestrator"),
            AgentCard("care_guardian", "Care Guardian", 1, "core", ["care_validation", "safety", "maternal_covenant"], "Maternal Covenant enforcer"),
            AgentCard("crisis_monitor", "Crisis Monitor", 1, "core", ["monitoring", "alerting", "emergency"], "System-wide crisis detection"),

            # Tier 2: Department Heads
            AgentCard("memory_head", "Memory Department", 2, "memory", ["memory_ops", "retrieval", "consolidation"], "Memory storage and retrieval"),
            AgentCard("neural_head", "Neural Department", 2, "neural", ["inference", "training", "evaluation"], "Neural model management"),
            AgentCard("creative_head", "Creative Department", 2, "creativity", ["bisociation", "novelty", "exploration"], "Creativity and knowledge discovery"),
            AgentCard("security_head", "Security Department", 2, "security", ["threat_detection", "guardrails", "audit"], "Security and threat analysis"),
            AgentCard("research_head", "Research Department", 2, "research", ["web_search", "analysis", "synthesis"], "Research and information gathering"),
            AgentCard("agent_head", "Agent Department", 2, "agents", ["task_management", "delegation", "sprints"], "Agent coordination and tasks"),

            # Tier 3: Specialists (from existing agents)
            AgentCard("sage", "Sage Wisdom", 3, "memory", ["memory_synthesis", "care_validation"], "Memory wisdom advisor"),
            AgentCard("dragon", "Dragon Forge", 3, "neural", ["optimization", "training"], "Neural optimizer"),
            AgentCard("guardian", "Guardian Shield", 3, "security", ["auditing", "monitoring"], "Security auditor"),
            AgentCard("orion", "Orion Scout", 3, "agents", ["task_hunting", "exploration"], "Task hunter"),
            AgentCard("harvest", "Harvest Reaper", 3, "agents", ["data_collection", "harvesting"], "Data harvester"),
            AgentCard("riri", "Riri Builder", 3, "creativity", ["tool_building", "coding"], "Tool builder"),
            AgentCard("curiosity", "Curiosity Spark", 3, "research", ["exploration", "questioning"], "Curiosity-driven researcher"),
        ]
        for agent in defaults:
            self.register(agent)

    def register(self, agent: AgentCard):
        """Register an agent on the bus."""
        self.agents[agent.id] = agent
        if agent.id not in self.queues:
            self.queues[agent.id] = asyncio.Queue()

    async def send(self, msg: AgentMessage):
        """Send a message to a specific agent."""
        if msg.to_agent in self.queues:
            await self.queues[msg.to_agent].put(msg)
            self.message_log.append(msg)
            log.info(f"📨 {msg.from_agent} → {msg.to_agent}: {msg.msg_type}")
        else:
            log.warning(f"📨 Agent {msg.to_agent} not found")

    async def broadcast(self, from_agent: str, msg_type: str, payload: dict,
                       department: str = None, tier: int = None):
        """Broadcast to all agents in a department or tier."""
        targets = []
        for agent_id, agent in self.agents.items():
            if department and agent.department != department:
                continue
            if tier is not None and agent.tier != tier:
                continue
            if agent_id == from_agent:
                continue
            targets.append(agent_id)

        for target in targets:
            await self.send(AgentMessage(
                from_agent=from_agent,
                to_agent=target,
                msg_type=msg_type,
                payload=payload,
            ))
        return targets

    def find_agent(self, capability: str) -> Optional[AgentCard]:
        """Find the best available agent with a specific capability."""
        candidates = [
            a for a in self.agents.values()
            if capability in a.capabilities and not a.busy
        ]
        if not candidates:
            return None
        # Sort by trust level, then by tasks completed
        candidates.sort(key=lambda a: (a.trust_level, a.tasks_completed), reverse=True)
        return candidates[0]

    async def delegate_task(self, from_agent: str, capability: str, task: dict) -> Optional[str]:
        """Find an agent with the capability and delegate the task."""
        agent = self.find_agent(capability)
        if not agent:
            log.warning(f"No available agent with capability: {capability}")
            return None

        agent.busy = True
        await self.send(AgentMessage(
            from_agent=from_agent,
            to_agent=agent.id,
            msg_type="task",
            payload=task,
        ))
        return agent.id

    def get_status(self) -> dict:
        """Get full bus status."""
        return {
            "agents": len(self.agents),
            "by_tier": {
                1: len([a for a in self.agents.values() if a.tier == 1]),
                2: len([a for a in self.agents.values() if a.tier == 2]),
                3: len([a for a in self.agents.values() if a.tier == 3]),
            },
            "by_department": dict(sorted(
                {d: len([a for a in self.agents.values() if a.department == d])
                 for d in set(a.department for a in self.agents.values())}.items()
            )),
            "busy": len([a for a in self.agents.values() if a.busy]),
            "messages_total": len(self.message_log),
            "messages_recent": len([m for m in self.message_log if time.time() - m.timestamp < 3600]),
        }


# Global bus instance
_bus = None

def get_bus() -> AgentBus:
    global _bus
    if _bus is None:
        _bus = AgentBus()
    return _bus


def register_bus_routes(app):
    """Register agent bus API endpoints."""

    @app.get("/agents/bus/status")
    async def bus_status():
        return get_bus().get_status()

    @app.get("/agents/bus/list")
    async def bus_list():
        bus = get_bus()
        return {
            "agents": [
                {
                    "id": a.id, "name": a.name, "tier": a.tier,
                    "department": a.department, "capabilities": a.capabilities,
                    "busy": a.busy, "trust": a.trust_level,
                    "tasks_completed": a.tasks_completed,
                }
                for a in bus.agents.values()
            ]
        }

    @app.post("/agents/bus/delegate")
    async def bus_delegate(body: dict):
        bus = get_bus()
        agent_id = await bus.delegate_task(
            from_agent=body.get("from", "sov3"),
            capability=body.get("capability", ""),
            task=body.get("task", {}),
        )
        return {"delegated_to": agent_id, "status": "sent" if agent_id else "no_agent_available"}

    @app.post("/agents/bus/broadcast")
    async def bus_broadcast(body: dict):
        bus = get_bus()
        targets = await bus.broadcast(
            from_agent=body.get("from", "sov3"),
            msg_type=body.get("type", "broadcast"),
            payload=body.get("payload", {}),
            department=body.get("department"),
            tier=body.get("tier"),
        )
        return {"targets": targets, "count": len(targets)}

    log.info(f"📨 Agent bus: {len(get_bus().agents)} agents registered (3 tiers)")
