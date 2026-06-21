#!/usr/bin/env python3
"""
Research Visualization - HTML Dashboard for Jarvis Research
Shows: models thinking, simulations running, data analysis in real-time
Legion OS inspired UI with Three.js visualizations
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Dict, List, Optional


class ResearchVisualizer:
    """Real-time research visualization with Legion OS aesthetics"""

    def __init__(self, port: int = 8765):
        self.port = port
        self.events = []
        self.models = {}
        self.simulations = {}
        self.findings = []
        self.server = None
        self.max_events = 50
        self.start_time = time.time()

    def add_event(self, event_type: str, message: str, data: Dict = None):
        """Add an event to display"""
        event = {
            "type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": time.time(),
        }
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

    def add_model(self, model: str, status: str, thinking: str = ""):
        """Update model status"""
        self.models[model] = {
            "status": status,
            "thinking": thinking,
            "updated": time.time(),
        }
        self.add_event("model", f"{model}: {status}", {"thinking": thinking[:100]})

    def add_simulation(self, name: str, progress: int, result: str = ""):
        """Update simulation"""
        self.simulations[name] = {
            "progress": progress,
            "result": result,
            "updated": time.time(),
        }
        if progress >= 100:
            self.add_event(
                "complete", f"Simulation complete: {name}", {"result": result[:200]}
            )
        else:
            self.add_event("sim", f"{name}: {progress}%")

    def add_finding(self, text: str, category: str = "insight"):
        """Add a finding"""
        self.findings.append(
            {
                "text": text,
                "category": category,
                "timestamp": time.time(),
            }
        )
        self.add_event("finding", f"[{category}] {text[:50]}...")

    def get_stats(self) -> dict:
        uptime = int(time.time() - self.start_time)
        active_models = sum(
            1 for m in self.models.values() if m["status"] in ["thinking", "active"]
        )
        running_sims = sum(1 for s in self.simulations.values() if s["progress"] < 100)
        return {
            "uptime": uptime,
            "active_models": active_models,
            "total_models": len(self.models),
            "simulations": running_sims,
            "findings": len(self.findings),
            "events": len(self.events),
        }

    def get_html(self) -> str:
        stats = self.get_stats()
        uptime_mins = stats["uptime"] // 60
        uptime_secs = stats["uptime"] % 60

        recent = self.events[-15:]
        events_html = ""
        for e in reversed(recent):
            icon = {
                "model": "🧠",
                "sim": "⚡",
                "complete": "✅",
                "finding": "💡",
                "error": "❌",
            }.get(e["type"], "📌")
            ts = time.strftime("%H:%M:%S", time.localtime(e["timestamp"]))
            events_html += f'<div class="log-line {e["type"]}"><span class="ts">{ts}</span> <span class="icon">{icon}</span> {e["message"]}</div>'

        models_html = ""
        for name, info in self.models.items():
            status = info["status"]
            status_class = (
                "thinking"
                if status == "thinking"
                else "active"
                if status == "active"
                else "idle"
            )
            status_icon = (
                "💭" if status == "thinking" else "⚡" if status == "active" else "💤"
            )
            bar_width = (
                100 if status == "complete" else 75 if status == "thinking" else 25
            )
            models_html += f"""
            <div class="model-card {status_class}">
                <div class="model-header">
                    <span class="model-icon">{status_icon}</span>
                    <span class="model-name">{name}</span>
                    <span class="model-status">{status.upper()}</span>
                </div>
                <div class="model-think">{info.get("thinking", "Idle")[:120]}</div>
                <div class="model-bar"><div class="bar-fill" style="width:{bar_width}%"></div></div>
            </div>"""

        sims_html = ""
        for name, info in self.simulations.items():
            progress = info["progress"]
            status_class = "running" if progress < 100 else "complete"
            bar_color = (
                "linear-gradient(90deg, #f59e0b, #fbbf24)"
                if progress < 100
                else "linear-gradient(90deg, #10b981, #34d399)"
            )
            sims_html += f"""
            <div class="sim-card {status_class}">
                <div class="sim-header">
                    <span class="sim-name">{name}</span>
                    <span class="sim-pct">{progress}%</span>
                </div>
                <div class="sim-bar"><div class="bar-fill" style="width:{progress}%;background:{bar_color}"></div></div>
                <div class="sim-result">{info.get("result", "Running...")[:100]}</div>
            </div>"""

        findings_html = ""
        for f in reversed(self.findings[-8:]):
            cat = f["category"]
            icon = {"insight": "💡", "data": "📊", "theory": "🔬", "warning": "⚠️"}.get(
                cat, "📌"
            )
            findings_html += f'<div class="finding-card {cat}"><span class="fi">{icon}</span><span class="ft">{f["text"][:180]}</span></div>'

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="2">
    <title>JARVIS Research Nexus</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --bg: #0a0b14;
            --surface: #0f1219;
            --surface-2: #141820;
            --surface-3: #1a1f2a;
            --gold: #d4a853;
            --gold-dim: #8a7035;
            --cyan: #22d3ee;
            --green: #10b981;
            --orange: #f59e0b;
            --purple: #a78bfa;
            --red: #ef4444;
            --text: #e2e8f0;
            --text-dim: #64748b;
            --border: rgba(212,168,83,0.15);
            --font-mono: 'JetBrains Mono', monospace;
            --font-sans: 'Space Grotesk', sans-serif;
        }}
        
        body {{
            font-family: var(--font-sans);
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: 
                radial-gradient(ellipse 80% 50% at 20% -20%, rgba(212,168,83,0.06) 0%, transparent 50%),
                radial-gradient(ellipse 60% 40% at 80% 100%, rgba(34,211,238,0.04) 0%, transparent 40%);
            pointer-events: none;
            z-index: 0;
        }}
        
        .container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto 1fr 1fr;
            gap: 16px;
            padding: 16px;
            min-height: 100vh;
            position: relative;
            z-index: 1;
        }}
        
        /* Header */
        .header {{
            grid-column: 1 / -1;
            background: linear-gradient(180deg, var(--surface) 0%, rgba(15,18,25,0.95) 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(12px);
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .logo-icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--gold) 0%, var(--gold-dim) 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 0 24px rgba(212,168,83,0.3);
        }}
        
        .logo-text {{
            font-family: var(--font-mono);
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 2px;
            color: var(--gold);
        }}
        
        .stats-row {{
            display: flex;
            gap: 24px;
        }}
        
        .stat-box {{
            text-align: center;
        }}
        
        .stat-num {{
            font-family: var(--font-mono);
            font-size: 24px;
            font-weight: 700;
            color: var(--cyan);
        }}
        
        .stat-label {{
            font-size: 11px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .uptime {{
            font-family: var(--font-mono);
            font-size: 13px;
            color: var(--text-dim);
        }}
        
        /* Panels */
        .panel {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            overflow: hidden;
        }}
        
        .panel-title {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .panel-title::before {{
            content: '';
            width: 8px;
            height: 8px;
            background: var(--gold);
            border-radius: 2px;
        }}
        
        /* Models */
        .model-card {{
            background: var(--surface-2);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 3px solid var(--text-dim);
            transition: all 0.2s;
        }}
        
        .model-card.thinking {{ border-left-color: var(--orange); }}
        .model-card.active {{ border-left-color: var(--green); }}
        .model-card.idle {{ border-left-color: var(--text-dim); }}
        
        .model-card:hover {{ transform: translateX(4px); background: var(--surface-3); }}
        
        .model-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        
        .model-icon {{ font-size: 14px; }}
        
        .model-name {{
            font-family: var(--font-mono);
            font-weight: 600;
            font-size: 13px;
            color: var(--cyan);
        }}
        
        .model-status {{
            margin-left: auto;
            font-size: 10px;
            padding: 2px 8px;
            background: var(--surface-3);
            border-radius: 4px;
            color: var(--text-dim);
        }}
        
        .model-think {{
            font-size: 12px;
            color: var(--text-dim);
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        
        .model-bar, .sim-bar {{
            height: 4px;
            background: var(--surface-3);
            border-radius: 2px;
            overflow: hidden;
        }}
        
        .bar-fill {{
            height: 100%;
            border-radius: 2px;
            transition: width 0.5s ease;
            background: linear-gradient(90deg, var(--gold), var(--cyan));
        }}
        
        /* Simulations */
        .sim-card {{
            background: var(--surface-2);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }}
        
        .sim-card.running .sim-pct {{ color: var(--orange); }}
        .sim-card.complete .sim-pct {{ color: var(--green); }}
        
        .sim-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        
        .sim-name {{ font-weight: 600; font-size: 13px; }}
        .sim-pct {{ font-family: var(--font-mono); font-size: 14px; font-weight: 600; }}
        .sim-result {{ font-size: 11px; color: var(--text-dim); margin-top: 8px; }}
        
        /* Findings */
        .finding-card {{
            background: var(--surface-2);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            display: flex;
            gap: 10px;
            align-items: flex-start;
        }}
        
        .finding-card.insight {{ border-left: 3px solid var(--purple); }}
        .finding-card.theory {{ border-left: 3px solid var(--orange); }}
        .finding-card.data {{ border-left: 3px solid var(--cyan); }}
        .finding-card.warning {{ border-left: 3px solid var(--red); }}
        
        .fi {{ font-size: 16px; flex-shrink: 0; }}
        .ft {{ font-size: 12px; line-height: 1.4; color: var(--text-dim); }}
        
        /* Console */
        .console {{
            grid-column: 1 / -1;
            background: #050508;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            font-family: var(--font-mono);
            font-size: 11px;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .log-line {{
            padding: 4px 0;
            border-bottom: 1px solid rgba(255,255,255,0.03);
        }}
        
        .log-line .ts {{ color: #4a5568; margin-right: 8px; }}
        .log-line.model {{ color: var(--cyan); }}
        .log-line.sim {{ color: var(--orange); }}
        .log-line.complete {{ color: var(--green); }}
        .log-line.finding {{ color: var(--purple); }}
        .log-line.error {{ color: var(--red); }}
        
        /* 3D Canvas */
        #canvas-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.6;
        }}
        
        /* Animations */
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        @keyframes glow {{
            0%, 100% {{ box-shadow: 0 0 20px rgba(212,168,83,0.3); }}
            50% {{ box-shadow: 0 0 40px rgba(212,168,83,0.5); }}
        }}
        
        .logo-icon {{ animation: glow 3s ease-in-out infinite; }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: var(--surface); }}
        ::-webkit-scrollbar-thumb {{ background: var(--surface-3); border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--gold-dim); }}
    </style>
</head>
<body>
    <div id="canvas-container"></div>
    
    <div class="container">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">🧠</div>
                <div class="logo-text">JARVIS RESEARCH NEXUS</div>
            </div>
            
            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-num">{stats["active_models"]}</div>
                    <div class="stat-label">Active</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num">{stats["simulations"]}</div>
                    <div class="stat-label">Simulations</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num">{stats["findings"]}</div>
                    <div class="stat-label">Findings</div>
                </div>
                <div class="stat-box">
                    <div class="uptime">{uptime_mins}m {uptime_secs}s</div>
                    <div class="stat-label">Uptime</div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-title">Neural Activity</div>
            {models_html or '<div style="color:var(--text-dim);font-size:12px;">No models active</div>'}
        </div>
        
        <div class="panel">
            <div class="panel-title">Simulations</div>
            {sims_html or '<div style="color:var(--text-dim);font-size:12px;">No simulations running</div>'}
        </div>
        
        <div class="panel" style="grid-column: 1 / -1;">
            <div class="panel-title">Latest Discoveries</div>
            {findings_html or '<div style="color:var(--text-dim);font-size:12px;">No findings yet</div>'}
        </div>
        
        <div class="console">
            <div class="panel-title" style="margin-bottom:8px;">Event Log</div>
            {events_html or '<div style="color:var(--text-dim);">No events</div>'}
        </div>
    </div>
    
    <script>
        // Three.js background
        let scene, camera, renderer, particles;
        
        function init3D() {{
            const container = document.getElementById('canvas-container');
            
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.z = 30;
            
            renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);
            
            // Particles
            const geometry = new THREE.BufferGeometry();
            const count = 500;
            const positions = new Float32Array(count * 3);
            
            for(let i = 0; i < count * 3; i++) {{
                positions[i] = (Math.random() - 0.5) * 60;
            }}
            
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            
            const material = new THREE.PointsMaterial({{
                size: 0.1,
                color: 0xd4a853,
                transparent: true,
                opacity: 0.6,
            }});
            
            particles = new THREE.Points(geometry, material);
            scene.add(particles);
            
            animate();
        }}
        
        function animate() {{
            requestAnimationFrame(animate);
            
            if(particles) {{
                particles.rotation.x += 0.0003;
                particles.rotation.y += 0.0005;
            }}
            
            renderer.render(scene, camera);
        }}
        
        function onResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}
        
        window.addEventListener('resize', onResize);
        init3D();
    </script>
</body>
</html>"""

    def start_server(self):
        """Start the visualization server"""
        visualizer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(visualizer.get_html().encode())

            def log_message(self, format, *args):
                pass

        def run():
            self.server = HTTPServer(("127.0.0.1", self.port), Handler)
            print(f"🔬 Research Nexus: http://127.0.0.1:{self.port}")
            self.server.serve_forever()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def stop(self):
        """Stop the server"""
        if self.server:
            self.server.shutdown()


_visualizer = None


def get_visualizer(port: int = 8765) -> ResearchVisualizer:
    global _visualizer
    if _visualizer is None:
        _visualizer = ResearchVisualizer(port)
        _visualizer.start_server()
    return _visualizer


if __name__ == "__main__":
    v = get_visualizer()

    print("Testing dashboard...")
    v.add_model(
        "Gemma 4",
        "thinking",
        "Analyzing substrate independence theory - exploring consciousness emergence across neural architectures...",
    )
    v.add_simulation(
        "Quantum Coherence",
        45,
        "Testing field stability in biological neural networks...",
    )
    v.add_finding(
        "Substrate may be independent of physical medium - consciousness persists",
        "theory",
    )
    v.add_model(
        "Nemotron", "active", "Running future-cast simulation on MEOK trajectory..."
    )
    v.add_simulation(
        "Future Trajectory",
        67,
        "Projecting system evolution over next 1000 iterations...",
    )
    v.add_finding(
        "Geometric patterns in neural nets strongly correlate with coherence metrics",
        "insight",
    )
    v.add_model(
        "OpenClaw", "thinking", "Delegating complex reasoning to sub-agent swarm..."
    )
    v.add_simulation("Agent Swarm", 23, "Orchestrating 47 parallel agent threads...")

    print(f"Dashboard running at http://127.0.0.1:{v.port}")
    print("Press Ctrl+C to stop")

    try:
        time.sleep(60)
    except KeyboardInterrupt:
        v.stop()
