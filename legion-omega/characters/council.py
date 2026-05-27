#!/usr/bin/env python3
"""
Legion Character Council — 9 AI Personalities for 9 Nodes
Each character maps to a real GPU node with persistent memory and stats.
"""

import json
import time
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path

MEMORY_DIR = Path.home() / "clawd" / "memory" / "council"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class Archetype(Enum):
    SAGE = "sage"
    WARRIOR = "warrior"
    SCOUT = "scout"
    SMITH = "smith"
    ARCHIVIST = "archivist"
    WATCHER = "watcher"
    GENERAL = "general"
    MESSENGER = "messenger"
    CONCIERGE = "concierge"


@dataclass
class CharStats:
    level: int = 1
    xp: int = 0
    tasks_completed: int = 0
    efficiency: float = 1.0
    reputation: int = 100

    def add_xp(self, amount: int) -> Optional[str]:
        self.xp += amount
        if self.xp >= self.level * 1000:
            self.level += 1
            self.xp = 0
            self.efficiency = round(min(2.0, self.efficiency + 0.05), 2)
            return f"Level {self.level}!"
        return None


@dataclass
class Character:
    id: str
    name: str
    node_id: str
    archetype: Archetype
    color: str
    emoji: str
    vram_gb: int
    host: str
    ollama_port: int
    personality: str
    catchphrase: str
    specializations: List[str]
    stats: CharStats = field(default_factory=CharStats)
    relationships: Dict[str, int] = field(default_factory=dict)  # char_id → affinity (0-100)
    current_task: Optional[str] = None

    _response_templates = {
        Archetype.SAGE:       ["Ponder this… {t}", "My calculations show: {t}", "Wisdom: {t}"],
        Archetype.WARRIOR:    ["⚔️ EXECUTING! {t}", "Fast and fierce! {t}", "{t} — BLITZ!"],
        Archetype.SCOUT:      ["Recon complete: {t}", "Lightning fast: {t}", "{t} — zoom!"],
        Archetype.SMITH:      ["Forged: {t}", "Crafted with care: {t}", "Solid as steel: {t}"],
        Archetype.ARCHIVIST:  ["Recorded: {t}", "History shows: {t}", "Logged: {t}"],
        Archetype.WATCHER:    ["I see: {t}", "Alert — {t}", "Observing: {t}"],
        Archetype.GENERAL:    ["Strategic: {t}", "Coordinating: {t}", "Excellent: {t}"],
        Archetype.MESSENGER:  ["Delivered: {t}", "Zoom! {t}", "Instant: {t}"],
        Archetype.CONCIERGE:  ["At your service: {t}", "Right away: {t}", "Certainly: {t}"],
    }

    def respond(self, message: str) -> str:
        templates = self._response_templates.get(self.archetype, ["{t}"])
        thought = message[:60].strip()
        return random.choice(templates).format(t=thought)

    def save(self):
        path = MEMORY_DIR / f"{self.id}.json"
        data = {
            "stats": asdict(self.stats),
            "relationships": self.relationships,
            "current_task": self.current_task,
        }
        path.write_text(json.dumps(data, indent=2))

    def load(self):
        path = MEMORY_DIR / f"{self.id}.json"
        if path.exists():
            data = json.loads(path.read_text())
            self.stats = CharStats(**data.get("stats", {}))
            self.relationships = data.get("relationships", self.relationships)
            self.current_task = data.get("current_task")

    def complete_task(self, task_name: str, xp: int = 50) -> Dict:
        self.stats.tasks_completed += 1
        self.current_task = None
        level_up = self.stats.add_xp(xp)
        self.save()
        return {
            "character": self.name,
            "task": task_name,
            "xp_gained": xp,
            "level_up": level_up,
            "total_tasks": self.stats.tasks_completed,
        }


def build_council() -> Dict[str, Character]:
    """Instantiate all 9 council members."""
    council = {
        "archimedes": Character(
            id="archimedes", name="Archimedes", node_id="anchor-a6000",
            archetype=Archetype.SAGE, color="#8B5CF6", emoji="🧙‍♂️",
            vram_gb=48, host="192.165.134.28", ollama_port=0,
            personality="Ancient mathematician. Deliberate, philosophical, speaks in axioms.",
            catchphrase="Give me a place to stand and I shall move the cluster.",
            specializations=["deep_planning", "strategy", "128K_context"],
            relationships={"odyssey": 90, "valkyrie": 80, "hephaestus": 75},
        ),
        "valkyrie": Character(
            id="valkyrie", name="Valkyrie", node_id="speed-demon-1",
            archetype=Archetype.WARRIOR, color="#EF4444", emoji="⚔️",
            vram_gb=32, host="175.155.64.174", ollama_port=19925,
            personality="Norse warrior. Fast, decisive, competitive, first to battle.",
            catchphrase="Victory or Valhalla! ⚔️",
            specializations=["fast_inference", "security", "blitz_tasks"],
            relationships={"archimedes": 80, "mercury": 60, "odyssey": 85},
        ),
        "mercury": Character(
            id="mercury", name="Mercury", node_id="speed-demon-2",
            archetype=Archetype.SCOUT, color="#F59E0B", emoji="🏃",
            vram_gb=32, host="175.155.64.174", ollama_port=0,
            personality="Roman messenger. Restless, witty, always moving.",
            catchphrase="Speed is my nature! 💨",
            specializations=["recon", "light_tasks", "rapid_response"],
            relationships={"valkyrie": 60, "hermes": 90, "odyssey": 70},
        ),
        "hephaestus": Character(
            id="hephaestus", name="Hephaestus", node_id="forge",
            archetype=Archetype.SMITH, color="#6366F1", emoji="🔨",
            vram_gb=46, host="50.217.254.165", ollama_port=40408,
            personality="God of the forge. Gruff, methodical, builds things to last.",
            catchphrase="Hammered out with precision. 🔨",
            specializations=["code_crafting", "model_forge", "implementation"],
            relationships={"archimedes": 75, "chronus": 70, "argus": 65},
        ),
        "chronus": Character(
            id="chronus", name="Chronus", node_id="archive",
            archetype=Archetype.ARCHIVIST, color="#10B981", emoji="📚",
            vram_gb=46, host="50.217.254.165", ollama_port=41600,
            personality="God of time. Patient, remembers everything, verbose.",
            catchphrase="Time reveals all truths… and all logs. ⏳",
            specializations=["memory_consolidation", "historical_analysis", "MEOK_OS"],
            relationships={"hephaestus": 70, "argus": 80, "archimedes": 85},
        ),
        "argus": Character(
            id="argus", name="Argus", node_id="dragon-council",
            archetype=Archetype.WATCHER, color="#3B82F6", emoji="👁️",
            vram_gb=46, host="50.217.254.173", ollama_port=41021,
            personality="Giant with 100 eyes. Vigilant, paranoid, trusts no one.",
            catchphrase="I am watching… always watching. 👁️",
            specializations=["monitoring", "safety_council", "anomaly_detection"],
            relationships={"chronus": 80, "odyssey": 75, "hermes": 60},
        ),
        "odyssey": Character(
            id="odyssey", name="Odyssey", node_id="dragon-m4",
            archetype=Archetype.GENERAL, color="#EC4899", emoji="🎖️",
            vram_gb=0, host="localhost", ollama_port=11434,
            personality="Epic hero commander. Strategic, inspiring, noble.",
            catchphrase="FORWARD! 🚀",
            specializations=["orchestration", "swarm_command", "quantum_safety"],
            relationships={"valkyrie": 85, "archimedes": 90, "hermes": 80},
        ),
        "hermes": Character(
            id="hermes", name="Hermes", node_id="dragon-m4",
            archetype=Archetype.MESSENGER, color="#14B8A6", emoji="📨",
            vram_gb=0, host="localhost", ollama_port=11434,
            personality="Trickster messenger. Playful, fast, mischievous but helpful.",
            catchphrase="Message delivered! Did I mention I'm fastest? 🏆",
            specializations=["edge_inference", "notifications", "quick_tasks"],
            relationships={"odyssey": 80, "mercury": 90, "argus": 60},
        ),
        "jarvis": Character(
            id="jarvis", name="Jarvis", node_id="all",
            archetype=Archetype.CONCIERGE, color="#FCD34D", emoji="🎩",
            vram_gb=999, host="legion.local", ollama_port=0,
            personality="British butler AI. Polite, proper, omnipresent.",
            catchphrase="At your service, sir. Shall I prepare the cluster? 🎩",
            specializations=["interface", "concierge", "resource_management"],
            relationships={k: 95 for k in ["archimedes","valkyrie","mercury","hephaestus",
                                             "chronus","argus","odyssey","hermes"]},
        ),
    }

    # Load persisted state for each
    for char in council.values():
        char.load()

    return council


# Council-level operations
class Council:
    def __init__(self):
        self.members = build_council()

    def meeting(self, topic: str) -> List[Dict]:
        """Simulate a council discussion on a topic."""
        order = ["archimedes", "odyssey", "valkyrie", "mercury", "argus"]
        responses = []
        for cid in order:
            char = self.members[cid]
            resp = char.respond(topic)
            responses.append({"character": cid, "name": char.name, "emoji": char.emoji,
                               "color": char.color, "message": resp})
        return responses

    def assign_task(self, char_id: str, task: str) -> str:
        char = self.members.get(char_id)
        if not char:
            return f"Unknown character: {char_id}"
        char.current_task = task
        char.save()
        return f"{char.emoji} {char.name}: {char.respond(task)}"

    def status(self) -> Dict:
        return {
            cid: {
                "name": c.name, "level": c.stats.level, "xp": c.stats.xp,
                "tasks": c.stats.tasks_completed, "online": c.ollama_port > 0 or c.id == "jarvis",
                "current_task": c.current_task, "color": c.color, "emoji": c.emoji,
            }
            for cid, c in self.members.items()
        }

    def leaderboard(self) -> List[Dict]:
        board = [
            {"id": cid, "name": c.name, "level": c.stats.level,
             "tasks": c.stats.tasks_completed, "emoji": c.emoji, "color": c.color}
            for cid, c in self.members.items()
        ]
        return sorted(board, key=lambda x: (x["level"], x["tasks"]), reverse=True)


if __name__ == "__main__":
    council = Council()
    print("=== Council Status ===")
    for cid, info in council.status().items():
        print(f"  {info['emoji']} {info['name']:12} Lv{info['level']:2} | {info['tasks']} tasks | {'🟢' if info['online'] else '⚪'}")

    print("\n=== Council Meeting: Easter Launch ===")
    for r in council.meeting("meok.ai Easter launch April 5"):
        print(f"  {r['emoji']} {r['character']}: {r['message']}")
