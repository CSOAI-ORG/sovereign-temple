#!/usr/bin/env python3
"""
Cost guardian for Legion cluster.
Monitors Vast.ai spend, alerts when approaching daily limit.
Kills idle nodes if GPU utilization stays below threshold.
"""

import os
import sys
import time
import json
import urllib.request
from datetime import datetime

VAST_API_KEY = os.getenv("VAST_API_KEY", "")

# Limits
DAILY_LIMIT_USD = 50.0       # Alert threshold
IDLE_THRESHOLD_PCT = 5.0     # GPU util % below which node is "idle"
IDLE_MINUTES = 30            # How long idle before action
KILL_ON_IDLE = False         # Set True to auto-destroy idle nodes (dangerous!)


def vast_api(method: str, path: str, data=None):
    url = f"https://console.vast.ai/api/v0/{path}"
    headers = {"Authorization": f"Bearer {VAST_API_KEY}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[VAST API ERROR] {e}")
        return {}


def check_instances():
    resp = vast_api("GET", "instances/?owner=me")
    return resp.get("instances", [])


def estimate_daily_spend(instances):
    hourly = sum(float(i.get("dph_total", 0)) for i in instances if i.get("actual_status") == "running")
    return hourly * 24


def print_status(instances):
    ts = datetime.now().strftime("%H:%M:%S")
    running = [i for i in instances if i.get("actual_status") == "running"]
    hourly = sum(float(i.get("dph_total", 0)) for i in running)
    daily = hourly * 24

    print(f"\n[{ts}] Legion Cost Report")
    print(f"  Running nodes : {len(running)}/{len(instances)}")
    print(f"  Hourly rate   : ${hourly:.3f}/hr")
    print(f"  Daily estimate: ${daily:.2f}/day")
    print(f"  Daily limit   : ${DAILY_LIMIT_USD:.2f}/day")

    for inst in running:
        iid = inst.get("id")
        gpu = inst.get("gpu_name", "?")
        rate = float(inst.get("dph_total", 0))
        util = inst.get("gpu_util", 0)
        status = inst.get("status_msg", "")
        idle_flag = " ⚠️ IDLE" if (util is not None and util < IDLE_THRESHOLD_PCT) else ""
        print(f"    [{iid}] {gpu:20} ${rate:.3f}/hr  util={util}%{idle_flag}  {status[:30]}")

    if daily >= DAILY_LIMIT_USD:
        print(f"\n  🚨 ALERT: Daily spend ${daily:.2f} exceeds limit ${DAILY_LIMIT_USD:.2f}!")
    elif daily >= DAILY_LIMIT_USD * 0.8:
        print(f"\n  ⚠️  WARNING: Daily spend ${daily:.2f} approaching limit (80%)")


def kill_idle_if_enabled(instances):
    if not KILL_ON_IDLE:
        return
    running = [i for i in instances if i.get("actual_status") == "running"]
    for inst in running:
        util = inst.get("gpu_util")
        if util is not None and util < IDLE_THRESHOLD_PCT:
            iid = inst.get("id")
            gpu = inst.get("gpu_name", "?")
            print(f"  [HEALER] Destroying idle node {iid} ({gpu}, util={util}%)")
            vast_api("DELETE", f"instances/{iid}/")


if __name__ == "__main__":
    if not VAST_API_KEY:
        print("Set VAST_API_KEY env var first.")
        sys.exit(1)

    print(f"Cost Guardian starting — limit ${DAILY_LIMIT_USD}/day, idle threshold {IDLE_THRESHOLD_PCT}%")
    print(f"Auto-kill idle: {'YES' if KILL_ON_IDLE else 'NO (monitoring only)'}")

    while True:
        instances = check_instances()
        print_status(instances)
        kill_idle_if_enabled(instances)
        time.sleep(300)  # Check every 5 min
