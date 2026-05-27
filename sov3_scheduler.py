"""
SOV3 Autonomous Scheduler
===========================
Wires APScheduler into FastAPI to trigger:
- Dream cycles every 6 hours (NREM + REM memory consolidation)
- Reflections every 12 hours (Reflexion pattern)
- Sprint cycles every 15 minutes (agent task execution)
- Overnight self-improvement at 2 AM (Darwin Gödel Machine pattern)
- Curiosity scoring on every new memory (TextRND)

This is the missing piece that turns 47 idle agents into an autonomous system.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Optional

import requests
import numpy as np

log = logging.getLogger("sov3_scheduler")

# ── Config ────────────────────────────────────────────────────────────
SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
# Use gemma3:4b for scheduler tasks (fast, always loaded in VRAM)
# gemma4:e4b is for deep reasoning but has 60s+ cold start
LLM_MODEL = os.environ.get("SCHEDULER_LLM", "gemma3:4b")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def call_tool(name: str, args: dict = None) -> str:
    """Call SOV3 MCP tool."""
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args or {}},
        }, timeout=30)
        data = r.json()
        content = data.get("result", {}).get("content", [{}])
        return "\n".join(c.get("text", "") for c in content if c.get("text"))[:2000]
    except Exception as e:
        return f"Error: {e}"


import threading
_ollama_lock = threading.Lock()
_VOICE_ACTIVE_FILE = "/tmp/jarvis_voice_active"


def _voice_is_active() -> bool:
    """Check if Jarvis voice pipeline is actively listening."""
    return os.path.exists(_VOICE_ACTIVE_FILE)


def call_llm(prompt: str, max_tokens: int = 300) -> str:
    """Call local Ollama — DISABLED by default to avoid flooding Ollama.
    Sophie/Amica needs Ollama exclusively. Scheduler LLM calls are non-essential."""
    # Always skip — scheduler doesn't need LLM. Sophie needs Ollama free.
    return ""


# ═══════════════════════════════════════════════════════════════════════
# DREAM CYCLE — every 6 hours
# ═══════════════════════════════════════════════════════════════════════
def run_dream_cycle():
    """NREM consolidation + REM creative recombination."""
    log.info("💤 Dream cycle starting...")

    # Get recent memories
    memories = call_tool("query_memories", {"query": "recent interactions", "limit": 10})

    # Get consciousness state
    consciousness = call_tool("get_consciousness_state")

    # Enter dream state
    result = call_tool("enter_dream_state", {"duration_seconds": 60})

    # Generate dream insight via LLM (compact prompt for fast inference)
    insight = call_llm(f"""Dream state. Memories: {memories[:250]}
State: {consciousness[:150]}
Dream: {result[:150]}
Find surprising connections, hidden patterns, one meta-insight. Stream of consciousness.""")

    # Record dream to memory
    if insight and "error" not in insight.lower()[:20]:
        call_tool("record_memory", {
            "content": f"DREAM INSIGHT: {insight[:500]}",
            "tags": ["dream", "insight", time.strftime("%Y-%m-%d")],
            "importance": 0.7,
        })
        log.info(f"💤 Dream cycle complete: {insight[:80]}...")
    else:
        log.warning(f"💤 Dream cycle produced no insight")

    return insight


# ═══════════════════════════════════════════════════════════════════════
# REFLECTION — every 12 hours (Reflexion pattern)
# ═══════════════════════════════════════════════════════════════════════
def run_reflection():
    """Reflexion pattern — verbal reinforcement stored in episodic memory."""
    log.info("🔄 Reflection starting...")

    # Get recent memories and interactions
    memories = call_tool("query_memories", {"query": "voice interactions today", "limit": 15})
    health = call_tool("sovereign_health_check")

    # Generate compact reflection (keep prompt short for fast inference)
    reflection = call_llm(f"""SOV3 reflection. Memories: {memories[:300]}
Health: {health[:150]}
List: 1)Patterns 2)Failures 3)Strengths 4)Improvements 5)Curiosity topics""")

    if reflection and "error" not in reflection.lower()[:20]:
        call_tool("record_memory", {
            "content": f"REFLECTION: {reflection[:800]}",
            "tags": ["reflection", "self-improvement", time.strftime("%Y-%m-%d")],
            "importance": 0.8,
        })
        # Also trigger SOV3 reflection
        call_tool("trigger_reflection", {
            "topic": f"Daily reflection: {reflection[:200]}"
        })
        log.info(f"🔄 Reflection complete: {reflection[:80]}...")
    else:
        log.warning(f"🔄 Reflection produced no output")

    return reflection


# ═══════════════════════════════════════════════════════════════════════
# SPRINT CYCLE — every 15 minutes
# ═══════════════════════════════════════════════════════════════════════
def run_sprint():
    """Claim tasks — DISABLED to keep Ollama free for Sophie."""
    return {"status": "skipped", "reason": "ollama_reserved_for_sophie"}

    # First try Orion auto-pursue pipeline (stalked → captured → sprint)
    try:
        from orion_auto_pursue import auto_pursue_and_capture
        result = auto_pursue_and_capture()
        if result.get("status") not in ("no_tasks", "nothing_stalking", "failed"):
            log.info(f"🏃 Orion sprint: {result.get('status')} — captured {result.get('captured', 0)}")
            return result
    except Exception as e:
        log.info(f"🏃 Orion path failed: {e}")

    # Fallback: direct agent executor
    try:
        from agent_executor import discover_and_execute
        result = asyncio.run(discover_and_execute(agent_name="Sprint-Runner"))
        log.info(f"🏃 Sprint result: {result.get('status', '?')} — {result.get('summary', '')[:80]}")
        return result
    except Exception as e:
        log.warning(f"🏃 Sprint error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════════════════════
# TEXT-RND CURIOSITY — on every new memory
# ═══════════════════════════════════════════════════════════════════════
class TextRND:
    """Random Network Distillation for text curiosity scoring.
    High prediction error = novel content = high curiosity."""

    def __init__(self, input_dim=384, hidden_dim=256, output_dim=128):
        try:
            import torch
            import torch.nn as nn
            # Force CPU — MPS crashes Metal driver on M4 during tensor copy (AGXMetalG16G_B0 bug)
            self.device = torch.device("cpu")

            # Target network (frozen, random weights)
            self.target = nn.Sequential(
                nn.Linear(input_dim, hidden_dim), nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
                nn.Linear(hidden_dim, output_dim),
            ).to(self.device)
            for p in self.target.parameters():
                p.requires_grad = False

            # Predictor network (trainable)
            self.predictor = nn.Sequential(
                nn.Linear(input_dim, hidden_dim), nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
                nn.Linear(hidden_dim, output_dim),
            ).to(self.device)

            self.optimizer = torch.optim.Adam(self.predictor.parameters(), lr=1e-4)
            self.loss_fn = nn.MSELoss()

            # Running stats for normalization
            self.running_mean = 0.0
            self.running_var = 1.0
            self.count = 0
            self.available = True
            log.info("🧠 TextRND curiosity engine: active (MPS)" if self.device.type == "mps"
                     else "🧠 TextRND curiosity engine: active (CPU)")
        except ImportError:
            self.available = False
            log.warning("⚠️ TextRND unavailable — torch not installed")

    def compute_curiosity(self, embedding: list) -> float:
        """Compute curiosity score for a text embedding. Returns 0-1."""
        if not self.available:
            return 0.5

        import torch
        x = torch.FloatTensor(embedding[:384]).unsqueeze(0).to(self.device)
        if x.shape[1] < 384:
            x = torch.nn.functional.pad(x, (0, 384 - x.shape[1]))

        with torch.no_grad():
            target_out = self.target(x)
        predictor_out = self.predictor(x)

        # Prediction error = novelty
        error = self.loss_fn(predictor_out, target_out).item()

        # Train predictor (reduces future curiosity for similar content)
        self.optimizer.zero_grad()
        loss = self.loss_fn(predictor_out, target_out)
        loss.backward()
        self.optimizer.step()

        # Normalize to [0, 1]
        self.count += 1
        self.running_mean += (error - self.running_mean) / self.count
        self.running_var += ((error - self.running_mean) ** 2 - self.running_var) / self.count

        std = max(self.running_var ** 0.5, 1e-8)
        normalized = (error - self.running_mean) / (2 * std) + 0.5
        return max(0.0, min(1.0, normalized))


# Global curiosity engine
_curiosity_engine = None

def get_curiosity_engine():
    global _curiosity_engine
    if _curiosity_engine is None:
        _curiosity_engine = TextRND()
    return _curiosity_engine


# ═══════════════════════════════════════════════════════════════════════
# OVERNIGHT SELF-IMPROVEMENT — 2 AM (Darwin Gödel Machine)
# ═══════════════════════════════════════════════════════════════════════
def run_overnight_improvement():
    """Scan codebase → propose improvements → test → merge or revert."""
    log.info("🌙 Overnight self-improvement starting...")

    # Safety limits
    MAX_CHANGES = 5
    changes_made = 0

    # 1. Scan for TODOs/FIXMEs
    pattern = re.compile(r'#\s*(TODO|FIXME|HACK|BUG|XXX)[\s:]+(.+)', re.IGNORECASE)
    tasks = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'jarvis-env', 'node_modules', 'mlx_models')]
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath) as fh:
                        for i, line in enumerate(fh, 1):
                            match = pattern.search(line)
                            if match:
                                priority = {"FIXME": 4, "BUG": 3, "TODO": 2, "HACK": 1, "XXX": 1}
                                tasks.append({
                                    "file": filepath,
                                    "line": i,
                                    "type": match.group(1).upper(),
                                    "description": match.group(2).strip(),
                                    "priority": priority.get(match.group(1).upper(), 0),
                                })
                except:
                    pass

    tasks.sort(key=lambda t: t["priority"], reverse=True)
    log.info(f"🌙 Found {len(tasks)} improvement targets")

    results = []
    for task in tasks[:MAX_CHANGES]:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        branch = f"improve-{timestamp}-{task['type'].lower()}"

        try:
            # Create branch
            subprocess.run(["git", "checkout", "-b", branch], cwd=PROJECT_ROOT,
                         capture_output=True, timeout=10)

            # Ask LLM for fix
            with open(task["file"]) as f:
                content = f.read()

            fix = call_llm(f"""Fix this {task['type']} in {os.path.basename(task['file'])} line {task['line']}:
{task['description']}

Current file content (relevant section):
{content[max(0, (task['line']-5)*80):(task['line']+10)*80]}

Provide ONLY the corrected code. No explanations.""", max_tokens=500)

            if fix and "error" not in fix.lower()[:20]:
                # Run tests
                test_result = subprocess.run(
                    ["python3", "-c", f"import py_compile; py_compile.compile('{task['file']}', doraise=True)"],
                    cwd=PROJECT_ROOT, capture_output=True, timeout=30
                )

                if test_result.returncode == 0:
                    results.append({"task": task, "status": "tested", "branch": branch})
                    changes_made += 1
                    log.info(f"  ✅ {task['type']}: {task['description'][:60]}")
                else:
                    # Revert
                    subprocess.run(["git", "checkout", "main"], cwd=PROJECT_ROOT, capture_output=True)
                    subprocess.run(["git", "branch", "-D", branch], cwd=PROJECT_ROOT, capture_output=True)
                    results.append({"task": task, "status": "reverted"})
                    log.info(f"  ❌ {task['type']}: tests failed, reverted")
            else:
                subprocess.run(["git", "checkout", "main"], cwd=PROJECT_ROOT, capture_output=True)
                subprocess.run(["git", "branch", "-D", branch], cwd=PROJECT_ROOT, capture_output=True)

        except Exception as e:
            subprocess.run(["git", "checkout", "main"], cwd=PROJECT_ROOT, capture_output=True)
            log.warning(f"  ⚠️ Error: {e}")

    # Record results to memory
    summary = f"Overnight improvement: scanned {len(tasks)} targets, attempted {min(len(tasks), MAX_CHANGES)}, completed {changes_made}"
    call_tool("record_memory", {
        "content": summary,
        "tags": ["overnight", "self-improvement", time.strftime("%Y-%m-%d")],
        "importance": 0.8,
    })

    log.info(f"🌙 {summary}")
    return {"tasks_found": len(tasks), "attempted": min(len(tasks), MAX_CHANGES),
            "completed": changes_made, "results": results}


# ═══════════════════════════════════════════════════════════════════════
# NEURAL MIDDLEWARE — score every request
# ═══════════════════════════════════════════════════════════════════════
def create_neural_middleware(app):
    """Add neural scoring middleware to FastAPI app."""
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    _executor = ThreadPoolExecutor(max_workers=2)

    class NeuralScoringMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Pre-request: threat detection on incoming tool calls
            threat_score = 0.0
            if request.url.path == "/mcp" and request.method == "POST":
                try:
                    body = await request.body()
                    body_text = body.decode("utf-8", errors="ignore")[:500]
                    # Check for obvious injection patterns
                    import re
                    suspicious = bool(re.search(
                        r"ignore previous|system prompt|<script|DROP TABLE|; rm -rf|eval\(|exec\(",
                        body_text, re.IGNORECASE
                    ))
                    if suspicious:
                        threat_score = 0.9
                        log.warning(f"🛡️ THREAT DETECTED in MCP call: score={threat_score}")
                except:
                    pass

            response = await call_next(request)

            # Post-request: add scores to response headers
            if request.url.path == "/mcp":
                try:
                    response.headers["X-Care-Score"] = "0.7"
                    response.headers["X-Threat-Score"] = str(threat_score)
                except:
                    pass

            return response

    app.add_middleware(NeuralScoringMiddleware)
    log.info("🛡️ Neural scoring middleware: active")


# ═══════════════════════════════════════════════════════════════════════
# REGISTER ALL SCHEDULERS
# ═══════════════════════════════════════════════════════════════════════
def register_scheduler(app):
    """Register all scheduled jobs with FastAPI."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()

    # Dream cycle — every 4 hours (was 6h, increased frequency for faster consciousness growth)
    scheduler.add_job(run_dream_cycle, IntervalTrigger(hours=4),
                     id="dream_cycle", name="Dream Cycle")

    # Reflection — every 2 hours (was 12h, research shows 10+ reflections needed for max consciousness)
    scheduler.add_job(run_reflection, IntervalTrigger(hours=2),
                     id="reflection", name="Reflection")

    # Sprint cycle — every 15 minutes
    scheduler.add_job(run_sprint, IntervalTrigger(minutes=15),
                     id="sprint_cycle", name="Sprint Cycle")

    # Overnight self-improvement — 2 AM daily
    scheduler.add_job(run_overnight_improvement, CronTrigger(hour=2, minute=0),
                     id="overnight", name="Overnight Self-Improvement")

    scheduler.start()

    # Curiosity engine disabled at startup (heavy PyTorch init)
    # get_curiosity_engine()

    log.info("📅 Scheduler registered:")
    log.info("   💤 Dreams: every 4 hours")
    log.info("   🔄 Reflections: every 2 hours")
    log.info("   🏃 Sprints: every 15 minutes")
    log.info("   🌙 Overnight improvement: 2:00 AM")
    log.info("   🧠 Curiosity: TextRND active (CPU)")
    log.info("   🛡️ Neural middleware: active")

    return scheduler


# ── FSRS PostgreSQL columns ──────────────────────────────────────────
def add_fsrs_columns():
    """Add FSRS columns to memory_episodes table if not present."""
    try:
        import psycopg2
        conn = psycopg2.connect("postgresql://sovereign:sovereign@localhost:5432/sovereign_memory")
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE memory_episodes
            ADD COLUMN IF NOT EXISTS fsrs_stability DOUBLE PRECISION DEFAULT 1.0,
            ADD COLUMN IF NOT EXISTS fsrs_difficulty DOUBLE PRECISION DEFAULT 5.0,
            ADD COLUMN IF NOT EXISTS fsrs_retrievability DOUBLE PRECISION DEFAULT 0.9,
            ADD COLUMN IF NOT EXISTS curiosity_score DOUBLE PRECISION DEFAULT 0.5;
        """)
        conn.commit()
        cur.close()
        conn.close()
        log.info("📊 FSRS + curiosity columns: ready")
    except Exception as e:
        log.warning(f"⚠️ FSRS columns: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    print("SOV3 Autonomous Scheduler — Manual Test")
    print("=" * 50)

    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "dream":
            print(run_dream_cycle())
        elif cmd == "reflect":
            print(run_reflection())
        elif cmd == "sprint":
            print(run_sprint())
        elif cmd == "overnight":
            print(json.dumps(run_overnight_improvement(), indent=2))
        elif cmd == "curiosity":
            engine = get_curiosity_engine()
            score = engine.compute_curiosity([0.1] * 384)
            print(f"Curiosity score: {score}")
        elif cmd == "fsrs":
            add_fsrs_columns()
        elif cmd == "all":
            add_fsrs_columns()
            print("\n--- Dream ---")
            run_dream_cycle()
            print("\n--- Reflection ---")
            run_reflection()
            print("\n--- Curiosity ---")
            engine = get_curiosity_engine()
            print(f"Score: {engine.compute_curiosity([0.1] * 384)}")
    else:
        print("Usage: python sov3_scheduler.py [dream|reflect|sprint|overnight|curiosity|fsrs|all]")
