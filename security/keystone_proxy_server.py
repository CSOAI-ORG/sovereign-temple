"""REV-3: Build a real keystone proxy that returns SOV3 sigil data publicly.

This is a Python HTTP server (like adversarial_corpus_server) that runs
on a different port and exposes a SOV3 sigil-feed proxy endpoint
the manifest-deploy / audit-feed-deploy / transparency-deploy pages
can fetch WITHOUT CORS issues.

The server reads the SOV3 snapshot file (updated by the indexer)
and returns it as JSON.

The server does NOT forward to localhost:3101 (that would require
the keystone to be public). Instead, it serves the snapshot.
"""
from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SNAPSHOT_PATH = Path("/Users/nicholas/clawd/sovereign-temple/security/adversarial_corpus_index.json")
SOV3_HUB = "http://localhost:3101"
HOST = "127.0.0.1"
PORT = 8766  # different from adversarial corpus (8765) and SOV3 hub (3101)


def fetch_live_sigil_transcript(limit: int = 20) -> dict:
    """Forward to SOV3 hub (localhost:3101) — only works locally."""
    import urllib.request
    try:
        req = urllib.request.Request(SOV3_HUB, data=json.dumps({
            "jsonrpc": "2.0", "id": "kf", "method": "tools/call",
            "params": {"name": "sigil_transcript", "arguments": {"limit": limit}}
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            return json.loads(data['result']['content'][0]['text'])
    except Exception as e:
        return {"error": str(e), "sigs": []}


def read_snapshot_file() -> dict:
    if not SNAPSHOT_PATH.exists():
        return {"sigs": [], "snapshot_at": None}
    return json.loads(SNAPSHOT_PATH.read_text())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silent

    def _send_json(self, status: int, payload: dict, allow_cors: bool = True):
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=60")
        if allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        limit = int(qs.get("limit", ["10"])[0])

        if u.path in ("/", "/keystone/", "/keystone"):
            return self._send_json(200, {
                "ok": True,
                "service": "MEOK keystone / SOV3 sigil proxy",
                "host": f"http://{HOST}:{PORT}",
                "endpoints": [
                    "GET  /keystone/sov3-sigils?limit=10  (live from SOV3 hub if reachable, else snapshot)",
                    "GET  /keystone/snapshot               (always snapshot file)",
                    "GET  /keystone/health                 (this service health)",
                ],
                "live_sigs_count": len(read_snapshot_file().get("recent_sigils", [])),
            })

        if u.path in ("/keystone/sov3-sigils", "/sov3-sigils"):
            # Try live first, fall back to snapshot
            live = fetch_live_sigil_transcript(limit=limit)
            if "error" in live or not live.get("sigils"):
                snap = read_snapshot_file()
                return self._send_json(200, {
                    "source": "snapshot",
                    "snapshot_at": snap.get("snapshot_at"),
                    "sigs": snap.get("recent_sigils", [])[:limit],
                })
            return self._send_json(200, {
                "source": "live",
                "sigs": live.get("sigils", live.get("transcript", live.get("recent", [])))[:limit],
            })

        if u.path in ("/keystone/snapshot", "/snapshot"):
            snap = read_snapshot_file()
            return self._send_json(200, snap)

        if u.path in ("/keystone/health", "/health"):
            return self._send_json(200, {
                "ok": True,
                "uptime_seconds": time.time() - _START,
                "snapshot_present": SNAPSHOT_PATH.exists(),
                "snapshot_at": read_snapshot_file().get("snapshot_at"),
            })

        return self._send_json(404, {"error": "not found", "path": u.path})


_START = time.time()


def main():
    s = HTTPServer((HOST, PORT), Handler)
    print(f"meok_keystone_proxy: http://{HOST}:{PORT}")
    print(f"  forwards to: {SOV3_HUB} (localhost:3101)")
    print(f"  snapshot:    {SNAPSHOT_PATH}")
    s.serve_forever()


if __name__ == "__main__":
    main()
