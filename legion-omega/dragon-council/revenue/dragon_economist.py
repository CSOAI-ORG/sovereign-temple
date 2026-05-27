#!/usr/bin/env python3
"""
Dragon Economist — Revenue-Driven Auto-Scale
Wakes heavy GPUs when MEOK AI Labs exam queue builds up
Sleeps them when idle to save money
Revenue: MEOK AI Labs certification exams + API access
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

# Vast.ai instance IDs for heavy lifters
HEAVY_INSTANCES = ["34060491", "34076369", "34077918"]
HEAVY_HOURLY_RATE = 0.219 * 3  # $0.657/hr for 3× RTX 8000
SPEED_HOURLY_RATE = 0.009  # 4080S always-on

# Revenue per job type
REVENUE_TABLE = {
    "csoai_cert_basic": 29.00,      # Basic certification
    "csoai_cert_advanced": 99.00,   # Advanced certification
    "csoai_cert_enterprise": 299.00, # Enterprise certification
    "api_access_1k": 0.10,          # Per 1K tokens via API
    "council_query": 0.50,          # Council deliberation
}

# Thresholds
WAKE_QUEUE_THRESHOLD = 3    # Wake heavy when 3+ premium jobs waiting
SLEEP_IDLE_SECONDS = 600    # Sleep after 10min idle
DAILY_BUDGET_USD = 20.00    # Max daily GPU spend

LOG_DIR = Path.home() / "clawd" / "memory" / "dragon-economist"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "economist.log"
REVENUE_LOG = LOG_DIR / f"revenue_{date.today()}.jsonl"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][ECONOMIST] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def log_revenue(job_type: str, amount: float, cost: float):
    entry = {
        "timestamp": time.time(),
        "job_type": job_type,
        "revenue": amount,
        "cost": cost,
        "profit": amount - cost,
        "date": str(date.today()),
    }
    with open(REVENUE_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


class DragonEconomist:
    def __init__(self):
        self.heavy_online = False
        self.heavy_start_time = None
        self.last_heavy_job = 0.0
        self.today_spend = 0.0
        self.today_revenue = 0.0
        self.job_queue: List[Dict] = []

    @property
    def heavy_hours_running(self) -> float:
        if self.heavy_online and self.heavy_start_time:
            return (time.time() - self.heavy_start_time) / 3600
        return 0.0

    @property
    def heavy_cost_so_far(self) -> float:
        return self.heavy_hours_running * HEAVY_HOURLY_RATE

    def add_job(self, job_type: str, payload: dict) -> str:
        job_id = f"{job_type}_{int(time.time())}"
        self.job_queue.append({
            "id": job_id, "type": job_type,
            "payload": payload, "queued_at": time.time(),
            "revenue": REVENUE_TABLE.get(job_type, 0.0),
        })
        log(f"Job queued: {job_id} (${REVENUE_TABLE.get(job_type, 0):.2f})")
        return job_id

    async def start_heavy(self):
        if self.heavy_online:
            return
        log(f"WAKING heavy lifters ({len(HEAVY_INSTANCES)}× RTX 8000)")
        for inst_id in HEAVY_INSTANCES:
            result = subprocess.run(
                ["vastai", "start", "instance", inst_id],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                log(f"  Started {inst_id}")
            else:
                log(f"  Failed {inst_id}: {result.stderr[:50]}")
        log("Waiting 3min for boot...")
        await asyncio.sleep(180)
        self.heavy_online = True
        self.heavy_start_time = time.time()
        log("Heavy lifters ONLINE")

    async def stop_heavy(self):
        if not self.heavy_online:
            return
        cost = self.heavy_cost_so_far
        log(f"Sleeping heavy lifters (cost so far: ${cost:.3f})")
        for inst_id in HEAVY_INSTANCES:
            subprocess.run(["vastai", "stop", "instance", inst_id], capture_output=True)
        self.today_spend += cost
        self.heavy_online = False
        self.heavy_start_time = None
        log(f"Heavy lifters SLEEPING. Today: spent=${self.today_spend:.2f}, earned=${self.today_revenue:.2f}")

    def should_wake(self) -> bool:
        """Should we wake heavy lifters?"""
        premium_jobs = [j for j in self.job_queue
                       if j["revenue"] >= 25.0]  # $25+ jobs only justify heavy
        potential_revenue = sum(j["revenue"] for j in premium_jobs)
        wake_cost = 0.5 * HEAVY_HOURLY_RATE  # 30min minimum cost

        return (
            len(premium_jobs) >= WAKE_QUEUE_THRESHOLD
            and potential_revenue > wake_cost * 3  # 3× ROI minimum
            and self.today_spend < DAILY_BUDGET_USD
        )

    def should_sleep(self) -> bool:
        """Should we sleep heavy lifters?"""
        idle_secs = time.time() - self.last_heavy_job
        return (
            self.heavy_online
            and idle_secs > SLEEP_IDLE_SECONDS
            and not any(j["revenue"] >= 25.0 for j in self.job_queue)
        )

    async def process_job_on_heavy(self, job: Dict) -> Dict:
        """Execute a job on heavy GPU cluster"""
        import urllib.request
        HEAVY_ENDPOINT = "http://50.217.254.165:40408"  # Forge (primary heavy)

        prompt = self._build_prompt(job)
        payload = json.dumps({
            "model": "qwen3.5:35b",
            "prompt": prompt, "stream": False,
            "options": {"num_predict": 2000, "temperature": 0.3}
        }).encode()

        try:
            req = urllib.request.Request(
                f"{HEAVY_ENDPOINT}/api/generate",
                data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                result = json.loads(r.read())
                response = result.get("response", "")

            cost_est = 0.01  # ~1min heavy usage
            self.today_spend += cost_est
            self.today_revenue += job["revenue"]
            self.last_heavy_job = time.time()

            log_revenue(job["type"], job["revenue"], cost_est)
            log(f"Job {job['id']} complete: +${job['revenue']:.2f} revenue")

            return {
                "job_id": job["id"],
                "status": "complete",
                "result": response,
                "revenue": job["revenue"],
                "cost": cost_est,
                "profit": job["revenue"] - cost_est,
            }
        except Exception as e:
            log(f"Job {job['id']} failed: {e}")
            return {"job_id": job["id"], "status": "failed", "error": str(e)}

    def _build_prompt(self, job: Dict) -> str:
        job_type = job["type"]
        payload = job.get("payload", {})

        if "csoai_cert" in job_type:
            return f"""You are a MEOK AI Labs (Council of Sovereign AI) certification examiner.
Grade this submission:
Student: {payload.get('student_name', 'Unknown')}
Exam: {payload.get('exam_type', 'Basic')}
Submission: {payload.get('submission', 'Empty')}

Provide: Score (0-100), Pass/Fail, Detailed feedback, Certificate recommendation."""
        elif job_type == "council_query":
            return payload.get("query", "No query provided")
        else:
            return payload.get("prompt", f"Process job type: {job_type}")

    async def run(self):
        log("Dragon Economist started")
        log(f"Daily budget: ${DAILY_BUDGET_USD:.2f}")
        log(f"Heavy rate: ${HEAVY_HOURLY_RATE:.3f}/hr")

        while True:
            # Check if should wake/sleep
            if not self.heavy_online and self.should_wake():
                await self.start_heavy()

            if self.heavy_online and self.should_sleep():
                await self.stop_heavy()

            # Process jobs if heavy is online
            if self.heavy_online and self.job_queue:
                job = self.job_queue.pop(0)
                result = await self.process_job_on_heavy(job)
                log(f"Processed: profit=${result.get('profit', 0):.2f}")

            # Daily summary
            now = datetime.now()
            if now.hour == 23 and now.minute == 55:
                log(f"\n=== DAILY SUMMARY ===")
                log(f"Revenue: ${self.today_revenue:.2f}")
                log(f"Spend: ${self.today_spend:.2f}")
                log(f"Profit: ${self.today_revenue - self.today_spend:.2f}")

            await asyncio.sleep(30)


# FastAPI server
try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    import uvicorn

    app = FastAPI(title="Dragon Economist", version="1.0.0")
    economist = DragonEconomist()

    class JobRequest(BaseModel):
        job_type: str
        payload: Dict = {}

    @app.post("/jobs/submit")
    async def submit_job(req: JobRequest):
        job_id = economist.add_job(req.job_type, req.payload)
        return {"job_id": job_id, "queued": True,
                "estimated_revenue": REVENUE_TABLE.get(req.job_type, 0)}

    @app.get("/economics")
    async def economics():
        return {
            "today": {
                "revenue": economist.today_revenue,
                "spend": economist.today_spend,
                "profit": economist.today_revenue - economist.today_spend,
                "budget_remaining": DAILY_BUDGET_USD - economist.today_spend,
            },
            "heavy_lifters": {
                "online": economist.heavy_online,
                "cost_so_far": economist.heavy_cost_so_far,
                "idle_seconds": time.time() - economist.last_heavy_job if economist.heavy_online else 0,
            },
            "queue": {"length": len(economist.job_queue),
                     "premium_jobs": sum(1 for j in economist.job_queue if j["revenue"] >= 25)},
        }

    @app.get("/revenue-table")
    async def revenue_table():
        return REVENUE_TABLE

    if __name__ == "__main__":
        asyncio.get_event_loop().create_task(economist.run())
        port = int(os.environ.get("ECONOMIST_PORT", 8095))
        uvicorn.run(app, host="0.0.0.0", port=port)

except ImportError:
    if __name__ == "__main__":
        asyncio.run(DragonEconomist().run())
