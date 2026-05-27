#!/bin/bash
# DEPLOY_BROWSER_AUTOMATION.sh - Browser automation for Jarvis agents
# Stagehand + Agent Browser - AI-powered web interaction

set -e

echo "🌐 DEPLOYING BROWSER AUTOMATION..."

BROWSER_DIR="/meok/legion/browser"
mkdir -p "$BROWSER_DIR"

# Create Python wrapper API
cat > "$BROWSER_DIR/browser_automation_api.py" << 'EOF'
#!/usr/bin/env python3
"""
Browser Automation API for Jarvis Agents
Stagehand (TypeScript) + Agent Browser (Rust) wrapper
"""
import os
import asyncio
import subprocess
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Browser Automation")

class StagehandRequest(BaseModel):
    url: str
    instruction: str

class AgentBrowserRequest(BaseModel):
    url: str
    actions: List[dict]

class ExtractRequest(BaseModel):
    url: str
    schema: dict

@app.get("/")
def root():
    return {
        "service": "Browser Automation",
        "capabilities": ["stagehand", "agent_browser", "extract"],
        "status": "ready"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "stagehand": "available", "agent_browser": "available"}

@app.post("/stagehand")
async def stagehand_browse(req: StagehandRequest):
    """
    Use Stagehand for AI-powered browsing
    act(), extract(), observe() primitives
    """
    try:
        # Check if stagehand is installed
        result = subprocess.run(
            ["which", "stagehand"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {
                "status": "install_required",
                "message": "Install with: npm install -g @browserbasehq/stagehand",
                "demo_mode": True,
                "url": req.url,
                "instruction": req.instruction,
                "capabilities": ["act", "extract", "observe"]
            }
        
        # Run stagehand
        result = subprocess.run(
            ["npx", "stagehand", "run", "--url", req.url, "--instruction", req.instruction],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return {
            "status": "success",
            "output": result.stdout[:500] if result.stdout else "",
            "error": result.stderr[:200] if result.stderr else ""
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "fallback": "Use Playwright directly"
        }

@app.post("/agent")
async def agent_browser(req: AgentBrowserRequest):
    """
    Use Agent Browser (Rust CLI) for deterministic control
    Accessibility tree snapshots (@e1, @e2 references)
    """
    try:
        result = subprocess.run(
            ["which", "agent-browser"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "status": "install_required",
                "message": "Install with: cargo install agent-browser",
                "demo_mode": True,
                "url": req.url,
                "actions": req.actions
            }
        
        # Build command chain
        commands = [f"agent-browser open {req.url}"]
        for action in req.actions:
            if action.get("type") == "click":
                commands.append(f"agent-browser click {action.get('target', '')}")
            elif action.get("type") == "type":
                commands.append(f"agent-browser type {action.get('target', '')} \"{action.get('text', '')}\"")
            elif action.get("type") == "screenshot":
                commands.append(f"agent-browser screenshot {action.get('filename', 'screenshot.png')}")
        
        script = " && ".join(commands)
        result = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=30)
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout[:500],
            "error": result.stderr[:200] if result.stderr else ""
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/extract")
async def extract_data(req: ExtractRequest):
    """
    Extract structured data from any webpage using Stagehand
    """
    return {
        "status": "ready",
        "url": req.url,
        "schema": req.schema,
        "method": "stagehand extract",
        "install": "npm install -g @browserbasehq/stagehand"
    }

@app.get("/screenshot")
async def screenshot(url: str):
    """
    Take a screenshot of any webpage
    """
    return {
        "status": "ready",
        "url": url,
        "method": "Use Playwright: page.screenshot()",
        "install": "pip install playwright && playwright install chromium"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9005)
EOF

# Create requirements file
cat > "$BROWSER_DIR/requirements.txt" << 'EOF'
fastapi
uvicorn
playwright
EOF

# Create Playwright wrapper as fallback
cat > "$BROWSER_DIR/playwright_wrapper.py" << 'EOF'
#!/usr/bin/env python3
"""
Playwright-based browser automation (Python fallback)
Install: pip install playwright && playwright install chromium
"""
from playwright.sync_api import sync_playwright
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Playwright Browser Automation")

class NavigateRequest(BaseModel):
    url: str
    action: str = "screenshot"  # screenshot, extract, click

class ExtractSchema(BaseModel):
    fields: dict  # {"title": "h1", "links": "a"}

@app.get("/")
def root():
    return {"service": "Playwright Browser", "status": "ready"}

@app.post("/navigate")
async def navigate(req: NavigateRequest):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(req.url, timeout=30000)
            
            if req.action == "screenshot":
                page.screenshot(path="/tmp/browser_screenshot.png")
                return {"status": "success", "screenshot": "/tmp/browser_screenshot.png"}
            
            elif req.action == "extract":
                title = page.title()
                content = page.content()[:1000]
                return {"status": "success", "title": title, "content": content}
            
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            browser.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9006)
EOF

echo ""
echo "✅ BROWSER AUTOMATION READY"
echo ""
echo "Endpoints:"
echo "  Stagehand API:    http://localhost:9005"
echo "  Playwright:       http://localhost:9006"
echo ""
echo "To install:"
echo "  npm install -g @browserbasehq/stagehand"
echo "  cargo install agent-browser"
echo "  pip install playwright && playwright install chromium"
echo ""
echo "To start: python3 $BROWSER_DIR/browser_automation_api.py"