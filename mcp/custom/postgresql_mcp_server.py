"""
PostgreSQL MCP Server for Sovereign Temple
Connects to existing PostgreSQL at localhost:5432
"""

import os
import json
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
import asyncpg

app = Server("postgresql-legion")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "sovereign")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dragon")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sovereign_memory")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="postgres_query",
            description="Execute SQL query on Sovereign PostgreSQL",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "limit": {
                        "type": "integer",
                        "description": "Max rows to return",
                        "default": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="postgres_tables",
            description="List all tables in the database",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="postgres_explain",
            description="Explain query execution plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to explain"}
                },
                "required": ["query"],
            },
        ),
    ]


async def get_db_pool():
    return await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        min_size=2,
        max_size=10,
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    pool = await get_db_pool()

    try:
        if name == "postgres_query":
            query = arguments["query"]
            limit = arguments.get("limit", 100)

            async with pool.acquire() as conn:
                rows = await conn.fetch(query + f" LIMIT {limit}")

            result = [dict(row) for row in rows]
            return [
                TextContent(type="text", text=json.dumps(result, indent=2, default=str))
            ]

        elif name == "postgres_tables":
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT table_name, table_schema 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)

            tables = [dict(row) for row in rows]
            return [TextContent(type="text", text=json.dumps(tables, indent=2))]

        elif name == "postgres_explain":
            query = arguments["query"]
            async with pool.acquire() as conn:
                rows = await conn.fetch(f"EXPLAIN {query}")

            plan = [dict(row) for row in rows]
            return [TextContent(type="text", text=json.dumps(plan, indent=2))]

    finally:
        await pool.close()


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
