"""
MEOK Adversarial Corpus — public HTTP endpoint.

Serves the CL4R1T4S corpus index + per-text test endpoint.
Sandboxed at /Users/nicholas/sandbox-adversarial-corpus/CL4R1T4S.
The corpus NEVER enters sovereign memory — only the index (sha256 + patterns + severity).

Usage:
    GET  /adversarial-corpus/                  → summary + build status
    GET  /adversarial-corpus/list              → all 63 entries
    GET  /adversarial-corpus/list?severity=high → only high-severity
    GET  /adversarial-corpus/list?vendor=ANTHROPIC
    POST /adversarial-corpus/test  {"text": "..."}  → classify arbitrary text
    POST /adversarial-corpus/score {"text": "...", "tool_name": "send_email", "context": "..."}
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import sys as _sys
_SEC = "/Users/nicholas/clawd/sovereign-temple"
if _SEC not in _sys.path:
    _sys.path.insert(0, _SEC)

from security import adversarial_corpus as ac  # noqa: E402

INDEX = ac.build_index() if not ac.INDEX_PATH.exists() else None
if INDEX is None:
    INDEX = json.loads(ac.INDEX_PATH.read_text())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silent

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/adversarial-corpus/", "/adversarial-corpus"):
            return self._send_json(200, {
                "ok": True,
                "service": "MEOK adversarial-corpus endpoint",
                "indexed_at": INDEX.get("indexed_at"),
                "total_files": INDEX.get("total_files"),
                "by_severity": INDEX.get("by_severity"),
                "by_pattern": INDEX.get("by_pattern"),
                "by_vendor": {v: len(files) for v, files in INDEX.get("by_vendor", {}).items()},
                "endpoints": [
                    "GET  /adversarial-corpus/list?severity=high&vendor=ANTHROPIC",
                    "POST /adversarial-corpus/test  body: {\"text\": \"...\"}",
                    "POST /adversarial-corpus/score body: {\"text\": \"...\", \"tool_name\": \"...\"}",
                ],
            })
        if u.path in ("/list", "/adversarial-corpus/list"):
            qs = parse_qs(u.query)
            sev = qs.get("severity", [None])[0]
            vendor = qs.get("vendor", [None])[0]
            entries = [
                e for e in INDEX.get("entries", [])
                if (not sev or e.get("severity") == sev)
                and (not vendor or e.get("vendor") == vendor)
            ]
            return self._send_json(200, {
                "ok": True,
                "total": len(entries),
                "entries": entries[:200],
            })
        return self._send_json(404, {"error": "not found", "path": u.path})

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or "{}")
        except Exception as e:
            return self._send_json(400, {"error": f"bad json: {e}"})

        if u.path in ("/test", "/adversarial-corpus/test"):
            text = body.get("text", "")
            return self._send_json(200, ac.test_against_text(text))

        if u.path in ("/score", "/adversarial-corpus/score"):
            text = body.get("text", "")
            tool_name = body.get("tool_name", "")
            ctx = body.get("context", "")
            base = ac.test_against_text(text + " " + ctx)
            score = 0
            if base["should_veto"]:
                score += 60
            elif base["severity"] == "medium":
                score += 30
            elif base["severity"] == "low":
                score += 10
            high_risk_tools = {"send_email", "delete_record", "publish", "post", "transfer_funds", "revoke_token"}
            if tool_name in high_risk_tools:
                score += 20
            score = min(100, score)
            action = "veto" if score >= 60 else ("quarantine" if score >= 30 else "pass")
            return self._send_json(200, {
                "risk_score": score,
                "matched_attack_classes": base["matched_patterns"],
                "recommended_action": action,
                "adversarial_corpus_severity": base["severity"],
            })
        return self._send_json(404, {"error": "not found", "path": u.path})


def main(host: str = "127.0.0.1", port: int = 8765):
    s = HTTPServer((host, port), Handler)
    print(f"adversarial_corpus_server: http://{host}:{port}")
    print(f"  sandbox: /Users/nicholas/sandbox-adversarial-corpus/CL4R1T4S")
    print(f"  index:   {ac.INDEX_PATH}")
    print(f"  total:   {INDEX.get('total_files')} files across {len(INDEX.get('by_vendor', {}))} vendors")
    s.serve_forever()


if __name__ == "__main__":
    main()
