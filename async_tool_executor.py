#!/usr/bin/env python3
"""
Async Tool Executor - Parallel MCP tool execution
Dramatically speeds up multi-tool calls
"""

import asyncio
import aiohttp
import threading
from typing import List, Dict, Any, Optional, Callable
import json
import time


class AsyncToolExecutor:
    """
    Execute multiple MCP tools in parallel
    Use for tool calling where multiple tools can run simultaneously
    """

    def __init__(self, max_concurrent: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session: Optional[aiohttp.ClientSession] = None
        self._thread_local = threading.local()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=20),
            )
        return self._session

    async def execute_tool(self, url: str, method: str, params: Dict) -> Dict:
        """Execute a single tool call"""
        async with self._semaphore:
            session = await self._get_session()
            try:
                async with session.post(url, json=params) as resp:
                    return await resp.json()
            except Exception as e:
                return {"error": str(e)}

    async def execute_parallel(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute multiple tool calls in parallel"""
        tasks = []
        for call in tool_calls:
            task = self.execute_tool(
                call["url"], call.get("method", "tools/call"), call["params"]
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append(
                    {"error": str(result), "tool": tool_calls[i].get("name", "unknown")}
                )
            else:
                formatted_results.append(result)

        return formatted_results

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# Sync wrapper for non-async code
class ParallelToolRunner:
    """Run MCP tools in parallel from sync code"""

    _executor: Optional[AsyncToolExecutor] = None

    @classmethod
    def get_executor(cls) -> AsyncToolExecutor:
        if cls._executor is None:
            cls._executor = AsyncToolExecutor(max_concurrent=10)
        return cls._executor

    @classmethod
    def run_parallel(cls, tool_calls: List[Dict]) -> List[Dict]:
        """Run tools in parallel (sync wrapper)"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(cls.get_executor().execute_parallel(tool_calls))


async def test_parallel():
    """Test parallel tool execution"""
    executor = AsyncToolExecutor()

    # Example: Call memory, calendar, and web search in parallel
    tool_calls = [
        {
            "url": "http://localhost:3101/mcp",
            "method": "tools/call",
            "params": {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "query_memories",
                    "arguments": {"query": "recent conversations", "limit": 3},
                },
            },
            "name": "memory",
        },
        {
            "url": "http://localhost:3101/mcp",
            "method": "tools/call",
            "params": {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "get_consciousness_state", "arguments": {}},
            },
            "name": "consciousness",
        },
    ]

    print("Testing parallel tool execution...")
    t0 = time.time()
    results = await executor.execute_parallel(tool_calls)
    elapsed = time.time() - t0

    print(f"Parallel execution: {elapsed:.3f}s for {len(results)} tools")
    print(f"Results: {len(results)} tools responded")

    await executor.close()
    return results


if __name__ == "__main__":
    asyncio.run(test_parallel())
