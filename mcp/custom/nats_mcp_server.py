"""
NATS MCP Server for Sovereign Temple
Connects to NATS message bus for farm sensors and model requests
"""

import os
import json
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from nats.aio.client import Client as NATS

app = Server("nats-legion")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="nats_publish",
            description="Publish message to NATS subject",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "NATS subject (e.g., farm.ph, model.legion)",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message payload (JSON string)",
                    },
                },
                "required": ["subject", "message"],
            },
        ),
        Tool(
            name="nats_subscribe",
            description="Subscribe to NATS subject and receive messages",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "NATS subject to subscribe to",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of messages to receive",
                        "default": 1,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 10,
                    },
                },
                "required": ["subject"],
            },
        ),
        Tool(
            name="nats_broadcast_farm_alert",
            description="Broadcast alert to all farm sensors",
            inputSchema={
                "type": "object",
                "properties": {
                    "pond_id": {"type": "string", "description": "Pond identifier"},
                    "alert_type": {
                        "type": "string",
                        "description": "Alert type: ph, temp, oxygen, critical",
                    },
                    "value": {"type": "number", "description": "Current sensor value"},
                    "message": {"type": "string", "description": "Alert message"},
                },
                "required": ["pond_id", "alert_type", "value"],
            },
        ),
        Tool(
            name="nats_cluster_status",
            description="Get NATS cluster status",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


async def get_nats_client() -> NATS:
    nc = NATS()
    await nc.connect(NATS_URL)
    return nc


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        nc = await get_nats_client()

        try:
            if name == "nats_publish":
                subject = arguments["subject"]
                message = arguments["message"]

                await nc.publish(subject, message.encode())
                await nc.flush()

                return [TextContent(type="text", text=f"✅ Published to {subject}")]

            elif name == "nats_subscribe":
                subject = arguments["subject"]
                count = arguments.get("count", 1)
                timeout = arguments.get("timeout", 10)

                messages = []
                received = 0

                async def handler(msg):
                    nonlocal received
                    messages.append({"subject": msg.subject, "data": msg.data.decode()})
                    received += 1

                sub = await nc.subscribe(subject, cb=handler)
                await nc.flush()

                # Wait for messages or timeout
                start = asyncio.get_event_loop().time()
                while (
                    received < count
                    and (asyncio.get_event_loop().time() - start) < timeout
                ):
                    await asyncio.sleep(0.1)

                await sub.unsubscribe()

                return [TextContent(type="text", text=json.dumps(messages, indent=2))]

            elif name == "nats_broadcast_farm_alert":
                pond_id = arguments["pond_id"]
                alert_type = arguments["alert_type"]
                value = arguments["value"]
                message = arguments.get("message", f"Alert: {alert_type} = {value}")

                alert = {
                    "pond_id": pond_id,
                    "alert_type": alert_type,
                    "value": value,
                    "message": message,
                    "timestamp": asyncio.get_event_loop().time(),
                }

                await nc.publish(f"farm.alerts", json.dumps(alert).encode())
                await nc.publish(f"farm.{pond_id}.alerts", json.dumps(alert).encode())
                await nc.flush()

                return [
                    TextContent(
                        type="text", text=f"✅ Alert broadcast to pond {pond_id}"
                    )
                ]

            elif name == "nats_cluster_status":
                # NATS doesn't have a simple status API in async client
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "connected": True,
                                "url": NATS_URL,
                                "note": "NATS server must be running separately",
                            },
                            indent=2,
                        ),
                    )
                ]

        finally:
            await nc.close()

    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
