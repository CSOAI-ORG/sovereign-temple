#!/usr/bin/env python3
"""
MEOK AI Character OS Overlay v1.0
Unified desktop overlay — AI character, Fly Eye, status, voice, all systems.

Built with Tkinter — ZERO external dependencies.
Uses only stdlib for HTTP (http.client).
"""

import tkinter as tk
from tkinter import ttk
import threading
import json
import time
import os
import subprocess
import http.client
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# ═══ CONFIG ═══
SOV3_URL = "http://localhost:3101"
MEOK_URL = "http://localhost:3000"
OPENCLAW_URL = "http://localhost:18789"
OLLAMA_URL = "http://localhost:11434"

COLORS = {
    "bg": "#0d0c18",
    "gold": "#c9a84c",
    "cyan": "#00d4ff",
    "green": "#22c55e",
    "red": "#ef4444",
    "purple": "#a855f7",
    "white": "#ffffff",
    "dim": "#666666",
    "orange": "#fb923c",
}


def _http_post_json(url, data, timeout=5):
    """POST JSON using stdlib http.client — no external deps."""
    try:
        # Parse URL
        url = url.replace("http://", "")
        if "/" in url:
            host, path = url.split("/", 1)
            path = "/" + path
        else:
            host = url
            path = "/"

        conn = http.client.HTTPConnection(host, timeout=timeout)
        body = json.dumps(data)
        conn.request(
            "POST", path, body=body, headers={"Content-Type": "application/json"}
        )
        resp = conn.getresponse()
        result = json.loads(resp.read().decode("utf-8")) if resp.status == 200 else None
        conn.close()
        return resp.status, result
    except Exception:
        return 0, None


def _http_get_status(url, timeout=3):
    """GET and return status code using stdlib."""
    try:
        url = url.replace("http://", "")
        if "/" in url:
            host, path = url.split("/", 1)
            path = "/" + path
        else:
            host = url
            path = "/"

        conn = http.client.HTTPConnection(host, timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        status = resp.status
        resp.read()
        conn.close()
        return status
    except Exception:
        return 0


class MEOKOverlay:
    """Main overlay window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MEOK AI")
        self.root.geometry("340x540")
        self.root.configure(bg=COLORS["bg"])
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.93)
        self.root.overrideredirect(True)

        # Position top-right
        x = self.root.winfo_screenwidth() - 370
        self.root.geometry(f"340x540+{x}+30")

        # State
        self.sov3_state = {"consciousness": 0, "emotion": "neutral", "care": 0}
        self.jarvis_state = "idle"
        self.character_mood = "neutral"
        self.fly_eye_active = False

        # Drag
        self._drag = {"x": 0, "y": 0}
        self.root.bind("<Button-1>", lambda e: self._drag.update({"x": e.x, "y": e.y}))
        self.root.bind("<B1-Motion>", self._on_drag)

        self._build_ui()
        self._start_updates()

    def _on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag["x"])
        y = self.root.winfo_y() + (event.y - self._drag["y"])
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        main = tk.Frame(self.root, bg=COLORS["bg"], padx=14, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # ─── HEADER ───
        hdr = tk.Frame(main, bg=COLORS["bg"])
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="🤖 MEOK AI — SOVEREIGN OS",
            bg=COLORS["bg"],
            fg=COLORS["gold"],
            font=("Menlo", 10, "bold"),
        ).pack(side=tk.LEFT)
        self.dot = tk.Label(
            hdr, text="●", bg=COLORS["bg"], fg=COLORS["green"], font=("Menlo", 10)
        )
        self.dot.pack(side=tk.RIGHT)

        # ─── CHARACTER ───
        cf = tk.Frame(
            main, bg="#1a1928", highlightbackground=COLORS["gold"], highlightthickness=1
        )
        cf.pack(fill=tk.X, pady=(8, 8))

        self.char_canvas = tk.Canvas(
            cf, width=70, height=70, bg="#1a1928", highlightthickness=0
        )
        self.char_canvas.pack(side=tk.LEFT, padx=10, pady=8)

        ci = tk.Frame(cf, bg="#1a1928")
        ci.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=8)
        tk.Label(
            ci,
            text="JARVIS",
            bg="#1a1928",
            fg=COLORS["cyan"],
            font=("Menlo", 11, "bold"),
        ).pack(anchor=tk.W)
        self.char_status = tk.Label(
            ci, text="● Idle", bg="#1a1928", fg=COLORS["dim"], font=("Menlo", 8)
        )
        self.char_status.pack(anchor=tk.W)
        self.char_mood = tk.Label(
            ci, text="Mood: neutral", bg="#1a1928", fg=COLORS["dim"], font=("Menlo", 7)
        )
        self.char_mood.pack(anchor=tk.W)

        # ─── CONSCIOUSNESS ───
        tk.Label(
            main,
            text="🧠 SOV3 CONSCIOUSNESS",
            bg=COLORS["bg"],
            fg=COLORS["gold"],
            font=("Menlo", 8, "bold"),
        ).pack(anchor=tk.W)

        bf = tk.Frame(main, bg=COLORS["bg"])
        bf.pack(fill=tk.X, pady=(3, 2))
        self.bar = tk.Canvas(bf, height=8, bg="#1a1928", highlightthickness=0)
        self.bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.bar_lbl = tk.Label(
            bf, text="0%", bg=COLORS["bg"], fg=COLORS["cyan"], font=("Menlo", 8, "bold")
        )
        self.bar_lbl.pack(side=tk.RIGHT, padx=(6, 0))

        sf = tk.Frame(main, bg=COLORS["bg"])
        sf.pack(fill=tk.X)
        self.emotion_lbl = tk.Label(
            sf, text="💭 NEUTRAL", bg=COLORS["bg"], fg=COLORS["dim"], font=("Menlo", 7)
        )
        self.emotion_lbl.pack(side=tk.LEFT)
        self.care_lbl = tk.Label(
            sf, text="❤️ 0%", bg=COLORS["bg"], fg=COLORS["dim"], font=("Menlo", 7)
        )
        self.care_lbl.pack(side=tk.LEFT, padx=(10, 0))

        # ─── SERVICES ───
        tk.Label(
            main,
            text="⚙️  SERVICES",
            bg=COLORS["bg"],
            fg=COLORS["gold"],
            font=("Menlo", 8, "bold"),
        ).pack(anchor=tk.W, pady=(6, 0))

        svc_f = tk.Frame(main, bg=COLORS["bg"])
        svc_f.pack(fill=tk.X, pady=(3, 0))
        self.svc_dots = {}
        for i, name in enumerate(["SOV3", "JARVIS", "OpenClaw", "Ollama"]):
            r = tk.Frame(svc_f, bg=COLORS["bg"])
            r.pack(fill=tk.X, pady=1)
            d = tk.Label(
                r, text="●", bg=COLORS["bg"], fg=COLORS["dim"], font=("Menlo", 7)
            )
            d.pack(side=tk.LEFT)
            tk.Label(
                r, text=name, bg=COLORS["bg"], fg=COLORS["white"], font=("Menlo", 7)
            ).pack(side=tk.LEFT, padx=(3, 0))
            self.svc_dots[name] = d

        # ─── ACTIONS ───
        af = tk.Frame(main, bg=COLORS["bg"])
        af.pack(fill=tk.X, pady=(8, 4))
        for txt, cmd in [
            ("🎤 Voice", self._voice),
            ("👁️ Fly Eye", self._flyeye),
            ("🏛️ Council", self._council),
            ("💬 Chat", self._chat),
        ]:
            tk.Button(
                af,
                text=txt,
                bg="#1a1928",
                fg=COLORS["gold"],
                font=("Menlo", 7),
                relief=tk.FLAT,
                activebackground="#2a2938",
                command=cmd,
                cursor="hand2",
            ).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        # ─── FOOTER ───
        tk.Label(
            main,
            text="Drag to move · Double-click: Fly Eye · Esc: close",
            bg=COLORS["bg"],
            fg=COLORS["dim"],
            font=("Menlo", 6),
        ).pack(fill=tk.X, pady=(2, 0))

        self.root.bind("<Double-Button-1>", self._flyeye)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._draw_char()

    def _draw_char(self):
        self.char_canvas.delete("all")
        self.char_canvas.create_oval(
            5, 5, 65, 65, fill="#1a1928", outline=COLORS["cyan"], width=2
        )
        faces = {
            "happy": "😊",
            "thinking": "🤔",
            "listening": "👂",
            "speaking": "🗣️",
            "alert": "⚠️",
            "neutral": "🧠",
        }
        face = faces.get(self.character_mood, "🧠")
        self.char_canvas.create_text(35, 35, text=face, font=("Menlo", 26))

    def _update_bar(self, level):
        self.bar.delete("all")
        w, filled = 180, int(180 * level)
        self.bar.create_rectangle(0, 0, w, 8, fill="#1a1928", outline="")
        c = (
            COLORS["green"]
            if level > 0.7
            else COLORS["orange"]
            if level > 0.4
            else COLORS["red"]
        )
        self.bar.create_rectangle(0, 0, filled, 8, fill=c, outline="")
        self.bar_lbl.config(text=f"{level * 100:.0f}%")

    def _update_ui(self):
        s = self.sov3_state
        self._update_bar(s["consciousness"])
        self.emotion_lbl.config(text=f"💭 {s['emotion'].upper()}")
        self.care_lbl.config(text=f"❤️ {s['care'] * 100:.0f}%")
        self.char_mood.config(text=f"Mood: {s['emotion']}")

        mood_map = {
            "speaking": "speaking",
            "thinking": "thinking",
            "listening": "listening",
        }
        self.character_mood = mood_map.get(
            self.jarvis_state, s["emotion"] if s["emotion"] != "neutral" else "neutral"
        )
        self._draw_char()

    def _update_loop(self):
        while True:
            try:
                status, data = _http_post_json(
                    f"{SOV3_URL}/mcp",
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "get_consciousness_state", "arguments": {}},
                        "id": 1,
                    },
                )
                if status == 200 and data:
                    txt = (
                        data.get("result", {}).get("content", [{}])[0].get("text", "{}")
                    )
                    st = json.loads(txt)
                    self.sov3_state = {
                        "consciousness": st.get("consciousness_level", 0),
                        "emotion": st.get("emotional", {}).get(
                            "primary_emotion", "neutral"
                        ),
                        "care": st.get("emotional", {}).get("care_intensity", 0),
                    }
                    self.root.after(0, self._update_ui)

                for name, url in [
                    ("SOV3", f"{SOV3_URL}/health"),
                    ("OpenClaw", OPENCLAW_URL),
                    ("Ollama", OLLAMA_URL),
                ]:
                    online = _http_get_status(url) == 200
                    c = COLORS["green"] if online else COLORS["red"]
                    self.root.after(
                        0, lambda n=name, col=c: self.svc_dots[n].config(fg=col)
                    )
                self.root.after(
                    0, lambda: self.svc_dots["JARVIS"].config(fg=COLORS["green"])
                )
            except:
                pass
            time.sleep(5)

    def _start_updates(self):
        threading.Thread(target=self._update_loop, daemon=True).start()

    # ─── ACTIONS ───
    def _voice(self):
        self.jarvis_state = "listening"
        self.char_status.config(text="● Listening...", fg=COLORS["cyan"])
        self._draw_char()
        subprocess.Popen(
            [
                "/Users/nicholas/clawd/sovereign-temple/jarvis-env/bin/python3",
                "/Users/nicholas/clawd/sovereign-temple/voice_pipeline/jarvis_compass.py",
            ]
        )

    def _flyeye(self, event=None):
        self.fly_eye_active = not self.fly_eye_active
        if self.fly_eye_active:
            self.character_mood = "alert"
            self._draw_char()
            self.char_status.config(text="● Fly Eye: ACTIVE", fg=COLORS["orange"])
            # Capture screen
            subprocess.Popen(
                [
                    "/Users/nicholas/clawd/sovereign-temple/jarvis-env/bin/python3",
                    "/Users/nicholas/clawd/sovereign-temple/voice_pipeline/jarvis_flyeye.py",
                    "screen",
                ]
            )
        else:
            self.character_mood = "neutral"
            self._draw_char()
            self.char_status.config(text="● Idle", fg=COLORS["dim"])

    def _council(self):
        self.jarvis_state = "thinking"
        self.char_status.config(text="● Council deliberating...", fg=COLORS["purple"])
        self._draw_char()

    def _chat(self):
        pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MEOKOverlay().run()
