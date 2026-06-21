"""A2A Agent Card — Self-describing agent metadata."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import json


@dataclass
class AgentSkill:
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=lambda: ["text"])
    output_modes: List[str] = field(default_factory=lambda: ["text"])


@dataclass
class AgentCard:
    """A2A Agent Card served at /.well-known/agent.json"""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    authentication: Dict = field(default_factory=dict)
    default_input_modes: List[str] = field(default_factory=lambda: ["text"])
    default_output_modes: List[str] = field(default_factory=lambda: ["text"])
    capabilities: Dict = field(default_factory=lambda: {
        "streaming": True,
        "pushNotifications": False,
        "stateTransitionHistory": False,
    })
    skills: List[AgentSkill] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "authentication": self.authentication,
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "capabilities": self.capabilities,
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tags": s.tags,
                    "examples": s.examples,
                    "inputModes": s.input_modes,
                    "outputModes": s.output_modes,
                }
                for s in self.skills
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def meokclaw_default(cls, base_url: str) -> "AgentCard":
        """Generate MEOKCLAW's default Agent Card."""
        return cls(
            name="MEOKCLAW Sovereign Intelligence",
            description="Multi-model AI agent with council mode, cost optimization, and 15-language support. Can delegate to specialized sub-agents.",
            url=base_url,
            skills=[
                AgentSkill(
                    id="chat",
                    name="Conversational AI",
                    description="General chat with dual-brain routing and cost transparency",
                    tags=["chat", "conversation", "qa"],
                ),
                AgentSkill(
                    id="code",
                    name="Code Generation",
                    description="Write, review, and refactor code in any language",
                    tags=["code", "programming", "development"],
                ),
                AgentSkill(
                    id="council",
                    name="Multi-Model Council",
                    description="Run multiple models in parallel and reach consensus",
                    tags=["consensus", "voting", "multi-model"],
                ),
                AgentSkill(
                    id="research",
                    name="Deep Research",
                    description="Web search, document analysis, and synthesis",
                    tags=["research", "search", "analysis"],
                ),
                AgentSkill(
                    id="mcp_tools",
                    name="MCP Tool Execution",
                    description="Execute tools via Model Context Protocol",
                    tags=["tools", "mcp", "automation"],
                ),
            ],
        )
