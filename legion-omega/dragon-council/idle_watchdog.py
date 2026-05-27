#!/usr/bin/env python3
"""
Idle Watchdog — Auto-shutdown heavy GPU nodes after idle timeout
Saves ~$450/month by not running 24/7
Usage: python idle_watchdog.py --instances 34060491,34076369,34077918 --idle-timeout 600
"""

import argparse
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime

SHUTDOWN_TIMEOUT = int(os.environ.get("SHUTDOWN_AFTER_SECONDS", 600))
VAST_API_KEY = os.environ.get("VAST_API_KEY", "")

MONITORED_ENDPOINTS = [
    ("forge", "http://50.217.254.165:40408"),
    ("archive", "http://50.217.254.165:41600"),
    ("dragon-council", "http://50.217.254.173:41021"),
]


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][watchdog] {msg}", flush=True)


def check_activity(ollama_url: str) -> bool:
    """Check if Ollama is handling requests"""
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def get_ollama_queue(ollama_url: str) -> int:
    """Check if inference is running (basic check)"""
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/ps", timeout=5) as r:
            data = json.loads(r.read())
            return len(data.get("models", []))
    except Exception:
        return 0


def stop_instance(instance_id: str):
    """Stop a Vast.ai instance"""
    cmd = ["vastai", "stop", "instance", instance_id]
    if VAST_API_KEY:
        cmd += ["--api-key", VAST_API_KEY]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        log(f"Stopped instance {instance_id}")
    else:
        log(f"Failed to stop {instance_id}: {result.stderr[:100]}")


def main():
    parser = argparse.ArgumentParser(description="GPU Idle Watchdog")
    parser.add_argument("--instances", default="34060491,34076369,34077918",
                       help="Comma-separated Vast.ai instance IDs")
    parser.add_argument("--idle-timeout", type=int, default=SHUTDOWN_TIMEOUT,
                       help="Seconds of idle before shutdown (default: 600)")
    parser.add_argument("--dry-run", action="store_true", help="Log but don't actually stop")
    args = parser.parse_args()

    instances = [i.strip() for i in args.instances.split(",")]
    timeout = args.idle_timeout

    log(f"Watching {len(instances)} instances, idle timeout: {timeout}s")
    log(f"Instances: {instances}")

    last_activity = {name: time.time() for name, _ in MONITORED_ENDPOINTS}

    while True:
        any_active = False
        for name, url in MONITORED_ENDPOINTS:
            online = check_activity(url)
            queue_depth = get_ollama_queue(url) if online else 0

            if online and queue_depth > 0:
                last_activity[name] = time.time()
                any_active = True
            elif online:
                idle_secs = time.time() - last_activity.get(name, time.time())
                log(f"{name}: online, idle {int(idle_secs)}s")
            else:
                log(f"{name}: offline")

        if not any_active:
            # Check if ANY node has been idle too long
            max_idle = max(time.time() - t for t in last_activity.values())

            if max_idle > timeout:
                log(f"All nodes idle for {int(max_idle)}s > {timeout}s threshold")

                if args.dry_run:
                    log("DRY RUN: Would stop instances now")
                else:
                    log("Stopping heavy lifters to save cost...")
                    for inst_id in instances:
                        stop_instance(inst_id)
                    log("Heavy lifters stopped. ~$0.22/hr per node saved.")
                    log("To restart: vastai start instance <id>")
                    break

        time.sleep(30)


if __name__ == "__main__":
    main()
