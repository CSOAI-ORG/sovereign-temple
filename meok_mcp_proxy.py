#!/usr/bin/env python3
"""
MEOK MCP Proxy — resurrects port 3102 by forwarding to SOV3 MCP (3101).
Lightweight, no state, no model file conflicts.
"""
import os, sys
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="MEOK MCP Proxy", version="2.0.0")

UPSTREAM = os.environ.get("SOV3_MCP_URL", "http://localhost:3101")

@app.get("/health")
@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{UPSTREAM}/health")
            data = r.json()
            data["proxied_by"] = "meok_mcp_proxy"
            data["meok_mcp_port"] = 3102
            return JSONResponse(content=data, status_code=r.status_code)
    except Exception as exc:
        return JSONResponse(
            content={"status": "degraded", "upstream": UPSTREAM, "error": str(exc), "meok_mcp_port": 3102},
            status_code=503
        )

@app.post("/mcp")
@app.post("/api/mcp")
async def mcp_proxy(request: Request):
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{UPSTREAM}/mcp",
                content=body,
                headers={"content-type": request.headers.get("content-type", "application/json")}
            )
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
        return JSONResponse(
            content={"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Upstream error: {exc}"}, "id": None},
            status_code=502
        )

if __name__ == "__main__":
    import uvicorn
    _port = int(os.environ.get("PORT", 3102))
    _host = os.environ.get("HOST", "0.0.0.0")
    print(f"🌉 MEOK MCP Proxy starting on {_host}:{_port} → {UPSTREAM}")
    uvicorn.run(app, host=_host, port=_port)
