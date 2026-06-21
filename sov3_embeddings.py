#!/usr/bin/env python3
"""
SOV3 embeddings — one decoupled, sovereign-first embedding client.

Lifted from the Odysseus pattern (github.com/pewdiepie-archdaemon/odysseus,
src/embeddings.py): a single client shared by RAG + every memory module, with a
fallback chain so a down embedder DEGRADES instead of stalling startup.

Resolution order (sovereign-first, CPU-only by default — respects the no-local-GPU rule):
  1. HTTP API — only if EMBEDDING_URL is set (OpenAI-compatible /v1/embeddings:
     Ollama on the VM, vLLM, llama.cpp). Off by default so we never poke local GPU.
  2. fastembed (ONNX, ~50MB, CPU) — zero-config local fallback.
  3. deterministic hash vectors — last resort so callers NEVER crash (non-semantic;
     logged loudly).

Returns plain lists (Chroma-ready, no numpy dependency).

Why this matters for SOV3: today the 12 memory modules lean on Chroma's default
embedder with no shared, swappable client. This gives one place to swap models,
keeps embeddings local (on-brand for the SEAL/sovereignty story), and fast-fails
a dead endpoint instead of hanging.
"""
from __future__ import annotations
import os, math, logging, hashlib
from typing import List, Optional

logger = logging.getLogger("sov3.embeddings")
_DEFAULT_DIM = 384  # all-MiniLM-L6-v2


class EmbeddingClient:
    def __init__(self, url: Optional[str] = None, model: Optional[str] = None):
        # EMBEDDING_URL unset => skip HTTP entirely (no local-GPU poke).
        self.url = url if url is not None else os.getenv("EMBEDDING_URL")
        self.model = model or os.getenv("EMBEDDING_MODEL", "all-minilm:l6-v2")
        self._fastembed = None
        self._dim: Optional[int] = None
        self.last_mode: Optional[str] = None

    def _http(self, texts: List[str]) -> List[List[float]]:
        import httpx
        with httpx.Client(timeout=httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=3.0)) as c:
            r = c.post(self.url, json={"model": self.model, "input": texts})
            r.raise_for_status()
            return [d["embedding"] for d in r.json()["data"]]

    def _fast(self, texts: List[str]) -> List[List[float]]:
        if self._fastembed is None:
            from fastembed import TextEmbedding
            self._fastembed = TextEmbedding(
                model_name=os.getenv("FASTEMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            )
        return [list(map(float, v)) for v in self._fastembed.embed(texts)]

    def _hash(self, texts: List[str]) -> List[List[float]]:
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            buf = (h * (_DEFAULT_DIM // len(h) + 1))[:_DEFAULT_DIM]
            out.append([(b - 128) / 128.0 for b in buf])
        return out

    @staticmethod
    def _normalize(vecs: List[List[float]]) -> List[List[float]]:
        out = []
        for v in vecs:
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

    def encode(self, texts, normalize_embeddings: bool = True) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []
        if self.url:
            try:
                self.last_mode = "http"
                v = self._http(texts)
                return self._normalize(v) if normalize_embeddings else v
            except Exception as e:
                logger.warning("embed HTTP (%s) failed: %s — falling back to fastembed", self.url, e)
        try:
            self.last_mode = "fastembed"
            v = self._fast(texts)
            return self._normalize(v) if normalize_embeddings else v
        except Exception as e:
            logger.warning("fastembed unavailable (%s) — using NON-SEMANTIC hash fallback", e)
        self.last_mode = "hash"
        v = self._hash(texts)
        return self._normalize(v) if normalize_embeddings else v

    def get_sentence_embedding_dimension(self) -> int:
        if self._dim is None:
            self._dim = len(self.encode(["dimension probe"])[0])
            logger.info("embedding dim=%d via %s", self._dim, self.last_mode)
        return self._dim


_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """Process-wide singleton — share this across all SOV3 memory modules."""
    global _client
    if _client is None:
        _client = EmbeddingClient()
    return _client


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    c = get_embedding_client()
    vs = c.encode(["the malamutes are in the polytunnel", "compliance attestation"])
    print(f"mode={c.last_mode} dim={len(vs[0])} n={len(vs)} norm0={sum(x*x for x in vs[0])**0.5:.3f}")
