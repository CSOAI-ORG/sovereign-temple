#!/usr/bin/env python3
"""
SOV3 Event Bridge — Connects NATS JetStream to SOV3 memory.

Subscribes to all agent.* events and records them as SOV3 memories.
Also publishes SOV3 state changes to NATS for other agents.

Usage:
    python3 sov3_event_bridge.py          # Start bridge
    python3 sov3_event_bridge.py --test   # Send test event
"""
import asyncio
import json
import sys
import os
import time
import requests
from datetime import datetime

try:
    import nats
    from nats.js.api import StreamConfig, RetentionPolicy
except ImportError:
    print("pip3 install nats-py")
    sys.exit(1)

# --- Compat shim: NATS server v2.14 returns timestamps with variable-length
# fractional seconds (e.g. 5 digits: '...03.22862+00:00'). Python 3.9's strict
# datetime.fromisoformat only accepts exactly 3 or 6 fractional digits, and
# nats-py's _parse_utc_iso trims to <=6 but never pads, so a 5-digit value
# raises ValueError and kills consumer subscription. Pad fractional secs to 6.
def _patch_nats_iso_parse():
    from datetime import datetime, timezone
    from nats.js import api as _napi

    def _parse_utc_iso(time_string):
        s = time_string.replace("Z", "+00:00")
        if "." in s:
            date_part, frac_tz = s.split(".", 1)
            sep = "+" if "+" in frac_tz else ("-" if "-" in frac_tz else "")
            if sep:
                frac, tz = frac_tz.split(sep, 1)
                frac = frac[:6].ljust(6, "0")  # exactly 6 digits for py3.9
                s = f"{date_part}.{frac}{sep}{tz}"
            else:
                s = f"{date_part}.{frac_tz[:6].ljust(6, '0')}"
        return datetime.fromisoformat(s).astimezone(timezone.utc)

    _napi.Base._parse_utc_iso = staticmethod(_parse_utc_iso)

try:
    _patch_nats_iso_parse()
except Exception as _e:
    print(f"warn: could not patch nats iso parser: {_e}")

SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")

# Event → memory mapping
EVENT_CARE_WEIGHTS = {
    "agent.claude": 0.8,
    "agent.hermes": 0.7,
    "agent.n8n": 0.6,
    "agent.git": 0.5,
    "file.changed": 0.3,
    "system": 0.4,
}


def record_to_sov3(content: str, source: str, tags: list, care_weight: float = 0.5):
    """Record an event as a SOV3 memory episode."""
    try:
        resp = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": f"bridge-{int(time.time())}",
            "params": {
                "name": "record_memory",
                "arguments": {
                    "content": content[:4000],
                    "source_agent": f"nats-bridge-{source}",
                    "memory_type": "interaction",
                    "care_weight": care_weight,
                    "tags": tags,
                }
            }
        }, timeout=10)
        result = resp.json()
        return True
    except Exception as e:
        print(f"  SOV3 write failed: {e}")
        return False


async def run_bridge():
    """Main event bridge loop."""
    print(f"SOV3 Event Bridge starting...")
    print(f"  NATS: {NATS_URL}")
    print(f"  SOV3: {SOV3_URL}")

    # Check SOV3 health
    try:
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        print(f"  SOV3 status: {r.json().get('status', '?')}")
    except:
        print("  WARNING: SOV3 not responding")

    # Connect to NATS
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    # Create streams for agent events
    try:
        await js.add_stream(StreamConfig(
            name="AGENT_EVENTS",
            subjects=["agent.>"],
            retention=RetentionPolicy.LIMITS,
            max_msgs=10000,
            max_bytes=50 * 1024 * 1024,  # 50MB
        ))
        print("  Stream AGENT_EVENTS created/verified")
    except Exception as e:
        print(f"  Stream exists or error: {e}")

    try:
        await js.add_stream(StreamConfig(
            name="FILE_EVENTS",
            subjects=["file.>"],
            retention=RetentionPolicy.LIMITS,
            max_msgs=50000,
            max_bytes=100 * 1024 * 1024,  # 100MB
        ))
        print("  Stream FILE_EVENTS created/verified")
    except Exception as e:
        print(f"  Stream exists or error: {e}")

    # Subscribe to all agent events
    async def handle_agent_event(msg):
        subject = msg.subject
        try:
            data = json.loads(msg.data.decode())
        except:
            data = {"raw": msg.data.decode()}

        # Determine care weight from subject
        care_weight = 0.5
        for prefix, weight in EVENT_CARE_WEIGHTS.items():
            if subject.startswith(prefix):
                care_weight = weight
                break

        content = f"[{subject}] {json.dumps(data)[:2000]}"
        tags = ["nats", "event", subject.split(".")[1] if "." in subject else "unknown"]

        print(f"  Event: {subject} → SOV3 (care={care_weight})")
        record_to_sov3(content, subject, tags, care_weight)
        await msg.ack()

    # Subscribe with durable consumer
    sub = await js.subscribe("agent.>", durable="sov3-bridge", deliver_policy="new")

    print(f"\n  Listening for events on agent.> ...")
    print(f"  Publish test: nats pub agent.test '{{\"msg\": \"hello SOV3\"}}'")

    # Process messages
    try:
        while True:
            try:
                msg = await sub.next_msg(timeout=5)
                await handle_agent_event(msg)
            except asyncio.TimeoutError:
                pass  # No messages, continue waiting
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down bridge...")
    finally:
        await nc.close()


async def send_test():
    """Send a test event to verify the bridge."""
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    await js.publish("agent.test.hello", json.dumps({
        "timestamp": datetime.now().isoformat(),
        "source": "bridge-test",
        "message": "SOV3 event bridge test event",
        "system": "sovereign-temple",
    }).encode())

    print("Test event published to agent.test.hello")
    await nc.close()


if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(send_test())
    else:
        asyncio.run(run_bridge())
