#!/usr/bin/env python3
"""
JARVIS Vector Store - RAG with ChromaDB
Add semantic search to JARVIS
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional

try:
    import chromadb

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class JARVISVectorStore:
    """Vector store for RAG"""

    def __init__(
        self,
        persist_dir: str = "/Users/nicholas/clawd/sovereign-temple-live/vector-store",
    ):
        self.persist_dir = persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        if CHROMA_AVAILABLE:
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                "jarvis-knowledge", metadata={"description": "JARVIS knowledge base"}
            )
        else:
            self.client = None
            self.collection = None

    def add_documents(
        self, documents: List[str], ids: List[str] = None, metadata: List[Dict] = None
    ):
        """Add documents to vector store"""
        if not CHROMA_AVAILABLE:
            return {"error": "ChromaDB not installed"}

        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        if metadata is None:
            metadata = [{}] * len(documents)

        self.collection.add(documents=documents, ids=ids, metadatas=metadata)

        return {"added": len(documents)}

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search"""
        if not CHROMA_AVAILABLE:
            return [{"error": "ChromaDB not available"}]

        results = self.collection.query(query_texts=[query], n_results=top_k)

        return [
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            }
            for i in range(len(results["ids"][0]))
        ]

    def delete(self, ids: List[str]):
        """Delete documents"""
        if self.collection:
            self.collection.delete(ids=ids)
            return {"deleted": len(ids)}
        return {"error": "Not available"}


# Global instance
vector_store = JARVISVectorStore()


def add_knowledge(text: str, source: str = "user") -> dict:
    """Add knowledge to vector store"""
    import uuid

    return vector_store.add_documents(
        documents=[text], ids=[str(uuid.uuid4())], metadata=[{"source": source}]
    )


def search_knowledge(query: str, top_k: int = 5) -> List[Dict]:
    """Search knowledge base"""
    return vector_store.search(query, top_k)


if __name__ == "__main__":
    print("Testing vector store...")

    add_knowledge("JARVIS is a sovereign AI assistant", "system")
    add_knowledge("User likes pizza and coffee", "user")
    add_knowledge("MEOK is an AI OS with consciousness", "system")

    results = search_knowledge("What is JARVIS?")
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - {r.get('document', r)}")
