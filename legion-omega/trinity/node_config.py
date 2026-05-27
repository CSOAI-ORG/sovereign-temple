"""
Legion 8-Node Cluster Configuration
GPU Fleet + Macs = Sovereign AI Swarm

Forge:          50.217.254.165:40408   (RTX 8000 #1, JARVIS/SOV3)
Archive:        50.217.254.165:41600   (RTX 8000 #2, MEOK OS)
Dragon Council: 50.217.254.173:41021   (RTX 8000 #3, 192GB RAM, 4-Model Council)
Speed Demon 1:  175.155.64.174:19925   (RTX 4080S #1, speed tier)
Speed Demon 2:  175.155.64.174:??      (RTX 4080S #2, loading)
Anchor:         192.165.134.28:??      (RTX A6000 48GB, created)
Dragon (M4):    localhost:11434        (MacBook M4, local)
"""

import os

NODES = {
    "forge": {
        "name": "RTX 8000 #1 — The Forge (JARVIS/SOV3)",
        "instance_id": 34060491,
        "public_ip": "50.217.254.165",
        "docker_ip": "172.17.0.4",  # Docker bridge (from same host)
        "ssh_port": 41724,
        "ollama_port": 40408,
        "vram_gb": 46,
        "tflops": 14.2,
        "role": "JARVIS Core + SOV3 + MARS Metacognition",
        "models": ["qwen3.5:35b", "qwen3.5:9b", "nomic-embed-text", "tinyllama"],
        "status": "running",
    },
    "archive": {
        "name": "RTX 8000 #2 — The Archive (MEOK OS)",
        "instance_id": 34076369,
        "public_ip": "50.217.254.165",
        "docker_ip": "172.17.0.8",  # Docker bridge
        "ssh_port": 41620,
        "ollama_port": 41600,
        "vram_gb": 46,
        "tflops": 14.2,
        "role": "MEOK OS Inference + Safety + Memory Consolidation",
        "models": ["qwen3.5:35b", "qwen3.5:9b", "nomic-embed-text"],
        "status": "running",
    },
    "dragon-council": {
        "name": "RTX 8000 #3 — Dragon Council (192GB RAM Beast)",
        "instance_id": 34077918,
        "public_ip": "50.217.254.173",
        "ssh_port": 41415,
        "ollama_port": 41021,  # External Ollama port
        "vram_gb": 46,
        "ram_gb": 192,
        "tflops": 14.2,
        "role": "4-Model Democratic Council (Jarvis+Forge+Archive+Edge)",
        "models": ["qwen3.5:35b", "qwen3.5:9b", "nomic-embed-text"],  # Pulling...
        "status": "running",
        "council_ports": {
            "jarvis": 8001, "forge": 8002, "archive": 8003, "edge": 8004, "chamber": 8090
        },
    },
    "speed-demon-1": {
        "name": "RTX 4080S #1 — Speed Demon (Agent 11-18)",
        "instance_id": 34078245,
        "public_ip": "175.155.64.174",
        "ssh_port": 19066,
        "ollama_port": 19925,
        "vram_gb": 32,
        "ram_gb": 377,
        "tflops": 52.2,
        "role": "Speed Demons swarm — fast inference, ExLlamaV2 70B at 240 tok/s",
        "models": ["qwen2.5:14b", "qwen2.5:7b", "nomic-embed-text"],  # Pulling...
        "status": "running",
    },
    "speed-demon-2": {
        "name": "RTX 4080S #2 — Speed Demon (loading)",
        "instance_id": 34079026,
        "public_ip": "175.155.64.174",
        "ssh_port": None,
        "ollama_port": None,
        "vram_gb": 32,
        "tflops": 52.2,
        "role": "Speed Demons overflow",
        "status": "loading",
    },
    "anchor-a6000": {
        "name": "RTX A6000 — Anchor Node (Safety Council 0-10)",
        "instance_id": 34079027,
        "public_ip": "192.165.134.28",
        "ssh_port": None,
        "ollama_port": None,
        "vram_gb": 48,
        "tflops": 38.7,
        "role": "Safety Council agents 0-10, foundation layer",
        "status": "created",  # Waiting for ports
    },
    "dragon-m4": {
        "name": "M4 Max — Dragon (Local MacBook)",
        "instance_id": None,
        "public_ip": "localhost",
        "ssh_port": None,
        "ollama_port": 11434,
        "vram_gb": 0,
        "ram_gb": 128,  # Unified memory
        "tflops": 14.0,  # M4 Max estimate
        "role": "Quantum Safety + Cold Storage Mirror + Local Inference",
        "status": "local",
    },
}

# API Gateway (running on Archive port 6006 → external 41422)
API_GATEWAY = "http://50.217.254.165:41422"
API_TOKEN = os.environ.get("LEGION_API_TOKEN", "legion-trinity-meok")

TOTAL_VRAM_GB = sum(n["vram_gb"] for n in NODES.values() if n.get("status") in ("running", "loading", "created"))
TOTAL_COST_HR = 0.219 + 0.219 + 0.259 + 0.318 + 0.318 + 0.318  # ~$1.65/hr (3×8000 + 2×4080S + A6000)

# Node groupings by role
SAFETY_COUNCIL_NODES = ["anchor-a6000", "dragon-council"]   # Agents 0-10
SPEED_DEMON_NODES = ["speed-demon-1", "speed-demon-2"]       # Agents 11-18
HEAVY_NODES = ["forge", "archive", "dragon-council"]          # 35B+ inference
ALL_ACTIVE = ["forge", "archive", "dragon-council", "speed-demon-1", "dragon-m4"]

# New nodes added 2026-04-03
NODES["rtx_pro4500"] = {
    "instance_id": 34081342, "public_ip": "165.166.241.251",
    "ssh_port": 50922, "ollama_port": 41342, "vram_gb": 32,
    "gpu": "RTX PRO 4500", "status": "running"
}
NODES["rtx_5090"] = {
    "instance_id": 34081352, "public_ip": "142.171.48.138",
    "ssh_port": 33336, "ollama_port": 41352, "vram_gb": 32,
    "gpu": "RTX 5090", "status": "running"
}
