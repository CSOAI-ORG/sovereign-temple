#!/usr/bin/env python3
"""
JARVIS Batch Processor - Process multiple items
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class BatchProcessor:
    """Process items in batches"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers

    def process_items(self, items: List[Any], process_fn: callable) -> List[Dict]:
        """Process items in parallel"""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_fn, item): item for item in items}

            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    results.append(
                        {"item": item, "result": result, "status": "success"}
                    )
                except Exception as e:
                    results.append({"item": item, "error": str(e), "status": "failed"})

        return results

    def process_chat_batch(self, messages: List[str]) -> List[Dict]:
        """Process multiple chat messages"""
        import httpx

        def process_message(msg: str) -> str:
            r = httpx.post(
                "http://localhost:3200/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "ask_sovereign", "arguments": {"message": msg}},
                    "id": "batch",
                },
                timeout=60,
            )
            data = r.json()
            return json.loads(data["result"]["content"][0]["text"])["response"]

        return self.process_items(messages, process_message)

    def process_files(self, file_paths: List[str]) -> List[Dict]:
        """Process multiple files"""
        import importlib.util

        def process_file(path: str) -> Dict:
            spec = importlib.util.spec_from_file_location(
                "jarvis_doc",
                "/Users/nicholas/clawd/sovereign-temple/jarvis_document.py",
            )
            jarvis_doc = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(jarvis_doc)

            result = jarvis_doc.process_document(path)
            return result

        return self.process_items(file_paths, process_file)

    def add_to_vector_store(self, texts: List[str]) -> List[Dict]:
        """Add multiple texts to vector store"""
        import importlib.util

        def add_text(text: str) -> Dict:
            spec = importlib.util.spec_from_file_location(
                "jarvis_vec", "/Users/nicholas/clawd/sovereign-temple/jarvis_vector.py"
            )
            jarvis_vec = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(jarvis_vec)

            return jarvis_vec.add_knowledge(text, "batch")

        return self.process_items(texts, add_text)

    async def process_async(self, items: List[Any], process_fn: callable) -> List[Dict]:
        """Process items asynchronously"""
        tasks = [
            asyncio.create_task(asyncio.to_thread(process_fn, item)) for item in items
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            {"item": items[i], "result": r if not isinstance(r, Exception) else str(r)}
            for i, r in enumerate(results)
        ]


# Global processor
batch = BatchProcessor()


def process_batch_messages(messages: List[str]) -> List[Dict]:
    return batch.process_chat_batch(messages)


def process_batch_files(files: List[str]) -> List[Dict]:
    return batch.process_files(files)


if __name__ == "__main__":
    print("Batch Processor ready")

    # Test batch processing
    messages = ["Hello JARVIS", "What time is it?", "Tell me a joke"]

    results = process_batch_messages(messages)
    print(f"Processed {len(results)} messages")
    for r in results:
        print(f"  - {r.get('status')}")
