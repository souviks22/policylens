from __future__ import annotations

import asyncio
import math
from typing import List, Tuple

import numpy as np
from openai import AsyncOpenAI

MAX_BATCH = 64          # OpenAI max per call
MAX_CHARS = 6000        # chars per chunk before truncation


class EmbeddingService:
    """
    Wraps OpenAI text-embedding-3-small.
    All public methods are async-safe and batch-aware.
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    # ── Public API ──────────────────────────────────────────────────────────────

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings, batching as needed. Returns List[embedding]."""
        if not texts:
            return []

        sanitised = [self._sanitise(t) for t in texts]
        batches = [sanitised[i : i + MAX_BATCH] for i in range(0, len(sanitised), MAX_BATCH)]

        results: List[List[float]] = []
        for batch in batches:
            resp = await self._client.embeddings.create(model=self._model, input=batch)
            # Sort by index to maintain order
            ordered = sorted(resp.data, key=lambda d: d.index)
            results.extend([d.embedding for d in ordered])

        return results

    async def embed_single(self, text: str) -> List[float]:
        """Embed one string."""
        embs = await self.embed_texts([text])
        return embs[0]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity ∈ [-1, 1] between two embedding vectors."""
        va = np.array(a, dtype=np.float32)
        vb = np.array(b, dtype=np.float32)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom < 1e-9:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def similarity_matrix(
        self,
        embeddings_a: List[List[float]],
        embeddings_b: List[List[float]],
    ) -> List[List[float]]:
        """
        Compute (n × m) cosine similarity matrix.
        Returns list of n rows, each with m float values.
        """
        if not embeddings_a or not embeddings_b:
            return []

        A = np.array(embeddings_a, dtype=np.float32)
        B = np.array(embeddings_b, dtype=np.float32)

        # Normalise rows
        A_norms = np.linalg.norm(A, axis=1, keepdims=True)
        B_norms = np.linalg.norm(B, axis=1, keepdims=True)
        A_norms = np.where(A_norms < 1e-9, 1.0, A_norms)
        B_norms = np.where(B_norms < 1e-9, 1.0, B_norms)

        A_normed = A / A_norms
        B_normed = B / B_norms

        sim = A_normed @ B_normed.T          # (n, m)
        return sim.tolist()

    def top_k_similar(
        self,
        query_embedding: List[float],
        corpus_embeddings: List[List[float]],
        k: int = 5,
        threshold: float = 0.60,
    ) -> List[Tuple[int, float]]:
        """
        Return list of (index, score) for the top-k most similar corpus entries
        above `threshold`, sorted descending.
        """
        scores = [
            (i, self.cosine_similarity(query_embedding, emb))
            for i, emb in enumerate(corpus_embeddings)
        ]
        scores = [(i, s) for i, s in scores if s >= threshold]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _sanitise(text: str) -> str:
        """Strip NULs and truncate very long strings before embedding."""
        text = text.replace("\x00", " ")
        return text[:MAX_CHARS] if len(text) > MAX_CHARS else text
