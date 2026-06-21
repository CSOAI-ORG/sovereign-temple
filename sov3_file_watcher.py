#!/usr/bin/env python3
"""
SOV3 File Watcher — Monitors ~/clawd/ for changes, publishes to NATS + SOV3.

Every file change (create/modify/delete) becomes:
  1. A NATS event on file.changed.{ext}
  2. A SOV3 memory episode (for important files)

Filters out noise: .pyc, __pycache__, .git internals, node_modules, .next, tmp files.

Usage:
    python3 sov3_file_watcher.py              # Watch ~/clawd/
    python3 sov3_file_watcher.py /some/path   # Watch custom path
    python3 sov3_file_watcher.py --dry-run    # Log only, no NATS/SOV3
"""
import asyncio
import json
import os
import sys
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("pip3 install watchdog")
    sys.exit(1)

try:
    import nats
except ImportError:
    print("pip3 install nats-py")
    sys.exit(1)

# Config
WATCH_DIR = os.environ.get("WATCH_DIR", os.path.expanduser("~/clawd"))
SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
DRY_RUN = "--dry-run" in sys.argv

# File importance weights by extension/path
IMPORTANCE = {
    # High value — business & config
    ".md": 0.7,
    ".tsx": 0.6,
    ".ts": 0.6,
    ".py": 0.6,
    ".json": 0.4,
    ".sh": 0.5,
    ".yml": 0.4,
    ".yaml": 0.4,
    ".toml": 0.5,
    ".env": 0.3,
    # Medium — web
    ".html": 0.4,
    ".css": 0.3,
    ".js": 0.4,
    # Low
    ".txt": 0.2,
    ".log": 0.1,
    ".csv": 0.3,
}

# Boost patterns — files matching these get higher care weight
BOOST_PATTERNS = {
    "revenue/": 0.85,
    "CLAUDE.md": 0.9,
    "MASTER_ACTION": 0.85,
    "_TOPOLOGY/": 0.8,
    "sovereign-temple/": 0.7,
    "stripe": 0.75,
    "pricing": 0.75,
    "page.tsx": 0.65,
    "vercel.json": 0.6,
}

# Ignore patterns
IGNORE_DIRS = {
    "__pycache__", ".git", "node_modules", ".next", ".vercel",
    ".turbo", "dist", "build", ".cache", ".pytest_cache",
    "venv", ".venv", "env", ".tox", ".mypy_cache",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".class", ".o", ".so", ".dylib",
    ".swp", ".swo", ".tmp", ".bak", ".orig",
    ".DS_Store", ".lock",
}

# Debounce — don't fire on rapid successive changes to same file
_last_event = {}
DEBOUNCE_SECONDS = 2


def should_ignore(path: str) -> bool:
    """Check if a file path should be ignored."""
    parts = Path(path).parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True

    ext = os.path.splitext(path)[1]
    if ext in IGNORE_EXTENSIONS:
        return True

    basename = os.path.basename(path)
    if basename.startswith("."):
        return True

    return False


def get_care_weight(path: str) -> float:
    """Calculate care weight for a file based on extension and path patterns."""
    ext = os.path.splitext(path)[1]
    base_weight = IMPORTANCE.get(ext, 0.2)

    # Apply boost patterns
    for pattern, boost in BOOST_PATTERNS.items():
        if pattern in path:
            base_weight = max(base_weight, boost)
            break

    return min(base_weight, 1.0)


def is_debounced(path: str) -> bool:
    """Check if we should skip this event due to debouncing."""
    now = time.time()
    last = _last_event.get(path, 0)
    if now - last < DEBOUNCE_SECONDS:
        return True
    _last_event[path] = now
    return False


class SOV3FileHandler(FileSystemEventHandler):
    """Handles filesystem events and publishes to NATS + SOV3."""

    def __init__(self, nats_client=None):
        self.nc = nats_client
        self.js = None
        self.event_count = 0
        self.start_time = time.time()

    async def _publish_nats(self, subject: str, data: dict):
        """Publish event to NATS JetStream."""
        if DRY_RUN or not self.js:
            return
        try:
            await self.js.publish(
                subject,
                json.dumps(data).encode(),
            )
        except Exception as e:
            print(f"  NATS publish error: {e}")

    def _record_sov3(self, content: str, tags: list, care_weight: float):
        """Record to SOV3 memory."""
        if DRY_RUN:
            return
        try:
            requests.post(f"{SOV3_URL}/mcp", json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": f"watcher-{int(time.time())}",
                "params": {
                    "name": "record_memory",
                    "arguments": {
                        "content": content[:4000],
                        "source_agent": "file-watcher",
                        "memory_type": "interaction",
                        "care_weight": care_weight,
                        "tags": tags,
                    }
                }
            }, timeout=10)
        except Exception as e:
            print(f"  SOV3 write error: {e}")

    def _handle_event(self, event, action: str):
        """Process a file system event."""
        if event.is_directory:
            return

        path = event.src_path
        if should_ignore(path):
            return
        if is_debounced(path):
            return

        self.event_count += 1
        rel_path = os.path.relpath(path, WATCH_DIR)
        ext = os.path.splitext(path)[1] or "none"
        care_weight = get_care_weight(path)

        # Build NATS subject
        safe_ext = ext.lstrip(".") or "unknown"
        nats_subject = f"file.changed.{safe_ext}"

        # File stats
        size = 0
        try:
            size = os.path.getsize(path)
        except:
            pass

        timestamp = datetime.now().isoformat()

        event_data = {
            "action": action,
            "path": rel_path,
            "extension": ext,
            "size": size,
            "timestamp": timestamp,
            "care_weight": care_weight,
        }

        # Log
        icon = {"created": "✨", "modified": "📝", "deleted": "🗑️"}.get(action, "📄")
        print(f"  {icon} [{action}] {rel_path} (care={care_weight:.1f})")

        # Publish to NATS (async — fire and forget via loop)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._publish_nats(nats_subject, event_data))
        except:
            pass

        # Only record to SOV3 for important files (care >= 0.5)
        if care_weight >= 0.5:
            content = f"[FILE {action.upper()}] {rel_path} ({size} bytes) at {timestamp}"
            tags = ["file-watch", action, safe_ext]
            self._record_sov3(content, tags, care_weight)

    def on_created(self, event):
        self._handle_event(event, "created")

    def on_modified(self, event):
        self._handle_event(event, "modified")

    def on_deleted(self, event):
        self._handle_event(event, "deleted")


async def run_watcher():
    """Main watcher loop."""
    watch_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else WATCH_DIR

    print(f"SOV3 File Watcher starting...")
    print(f"  Watching: {watch_path}")
    print(f"  NATS: {NATS_URL}")
    print(f"  SOV3: {SOV3_URL}")
    print(f"  Dry run: {DRY_RUN}")

    # Connect to NATS
    nc = None
    js = None
    if not DRY_RUN:
        try:
            nc = await nats.connect(NATS_URL)
            js = nc.jetstream()
            print(f"  NATS connected ✅")
        except Exception as e:
            print(f"  NATS connection failed: {e} (continuing without NATS)")

    # Set up handler
    handler = SOV3FileHandler(nc)
    if js:
        handler.js = js

    observer = Observer()
    observer.schedule(handler, watch_path, recursive=True)
    observer.start()

    print(f"\n  Watching for file changes... (Ctrl+C to stop)")
    print(f"  Ignoring: {', '.join(sorted(IGNORE_DIRS))}")

    try:
        while True:
            await asyncio.sleep(30)
            elapsed = time.time() - handler.start_time
            rate = handler.event_count / (elapsed / 3600) if elapsed > 0 else 0
            if handler.event_count > 0 and handler.event_count % 10 == 0:
                print(f"  📊 {handler.event_count} events tracked ({rate:.0f}/hr)")
    except KeyboardInterrupt:
        print(f"\n  Stopping watcher... ({handler.event_count} events tracked)")
    finally:
        observer.stop()
        observer.join()
        if nc:
            await nc.close()


if __name__ == "__main__":
    asyncio.run(run_watcher())
