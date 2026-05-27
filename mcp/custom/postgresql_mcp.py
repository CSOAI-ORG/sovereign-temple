#!/usr/bin/env python3
"""
PostgreSQL MCP Server for Sovereign Temple
Standalone implementation using JSON-RPC 2.0
Works without external MCP SDK dependency
"""

import os
import sys
import json
import asyncio
import asyncpg
from datetime import datetime

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "sovereign")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dragon")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sovereign_memory")

pool = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        min_size=2,
        max_size=10,
    )


async def close_db():
    if pool:
        await pool.close()


def tool_postgres_query(query: str, limit: int = 100) -> str:
    if not pool:
        return json.dumps({"error": "Database not connected"})

    try:
        query = query.strip()
        if not query.upper().startswith(
            ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")
        ):
            return json.dumps({"error": "Only SELECT queries allowed for safety"})

        query = query + f" LIMIT {limit}"

        async def _run():
            async with pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]

        result = asyncio.get_event_loop().run_until_complete(_run())
        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_postgres_tables() -> str:
    if not pool:
        return json.dumps({"error": "Database not connected"})

    try:

        async def _run():
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT table_name, table_schema 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                return [dict(row) for row in rows]

        result = asyncio.get_event_loop().run_until_complete(_run())
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_request(request: dict) -> dict:
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "postgres_query",
                        "description": "Execute SQL query (SELECT only)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "default": 100},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "postgres_tables",
                        "description": "List all tables in database",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "postgres_query":
            result = tool_postgres_query(args.get("query", ""), args.get("limit", 100))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }

        elif tool_name == "postgres_tables":
            result = tool_postgres_tables()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32600, "message": "Invalid request"},
    }


def main():
    # Initialize database
    asyncio.get_event_loop().run_until_complete(init_db())

    # Read JSON-RPC requests from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(
                json.dumps(
                    {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(e)}}
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
