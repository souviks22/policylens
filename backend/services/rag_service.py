"""
rag_service.py — ChromaDB-backed RAG for PolicyLens.

Two collections are used:
  • "regulatory_kb"       — global, shared by all users
  • "user_kb_{safe_uid}"  — personal, one per user

Text is chunked at ~800 chars with a 120-char overlap so that important
sentences near chunk boundaries are not lost.

All ChromaDB calls are synchronous (PersistentClient), so every public
method that touches Chroma runs inside asyncio's default thread-pool
executor via `_run`.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from functools import partial
from typing import List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings

from services.embeddings import EmbeddingService
from config import get_settings


# ── Constants ───────────────────────────────────────────────────────────────────
GLOBAL_COLLECTION = "regulatory_kb"
CHUNK_SIZE   = 800    # target characters per chunk
CHUNK_OVERLAP = 120   # overlap between consecutive chunks
MIN_CHUNK_LEN = 80    # discard chunks shorter than this


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _safe_collection_name(user_id: str) -> str:
    """ChromaDB collection names must be [a-zA-Z0-9_-] and 3-63 chars."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)
    name = f"user_kb_{safe}"
    # Truncate to 63 chars (ChromaDB limit)
    return name[:63]


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split `text` into overlapping character-level chunks.
    Splits preferentially at paragraph / sentence boundaries.
    """
    text = text.strip()
    if not text:
        return []

    # Prefer splitting at double newlines (paragraphs)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # If a single paragraph is longer than chunk_size, split it further
            if len(para) > chunk_size:
                sub_chunks = _split_long_para(para, chunk_size, overlap)
                # Keep the last sub-chunk as the new `current` for overlap
                chunks.extend(sub_chunks[:-1])
                current = sub_chunks[-1] if sub_chunks else ""
            else:
                current = para

    if current and len(current) >= MIN_CHUNK_LEN:
        chunks.append(current)

    # Filter out tiny chunks
    return [c for c in chunks if len(c) >= MIN_CHUNK_LEN]


def _split_long_para(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split a single long paragraph into overlapping slices."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ── Singleton helpers (re-use the same ChromaDB client across requests) ──────────

_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        settings = get_settings()

        if settings.environment == "production":
            chroma_client = chromadb.CloudClient(
                api_key=settings.chroma_api_key,
                tenant=settings.chroma_tenant_id,
                database=settings.chroma_database_name
            )
        elif settings.environment == "development":
            chroma_client = chromadb.PersistentClient(
                path=settings.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            chroma_client = None

        emb_svc = EmbeddingService(
            base_url=settings.openai_embedding_base_url,
            api_key=settings.openai_embedding_api_key,
            model=settings.openai_embedding_model,
        )
        _rag_service = RAGService(
            chroma_client=chroma_client,
            embedding_service=emb_svc,
        )
    return _rag_service

    
# ── RAG Service ─────────────────────────────────────────────────────────────────

class RAGService:
    """
    Manages two kinds of ChromaDB collections:
        1. Global regulatory knowledge base (shared by all users).
        2. Per-user personal knowledge bases.

    Embeddings are produced by the shared EmbeddingService (OpenAI) and
    stored as raw float lists in Chroma.
    """

    def __init__(self, chroma_client: chromadb.ClientAPI, embedding_service: EmbeddingService):
        if chroma_client is None:
            raise ValueError("ChromaDB client is not configured. RAG features will be unavailable.")
        self._chroma = chroma_client
        self._emb = embedding_service

    # ── Collection helpers ──────────────────────────────────────────────────────

    def _global_col(self) -> chromadb.Collection:
        return self._chroma.get_or_create_collection(GLOBAL_COLLECTION)

    def _user_col(self, user_id: str) -> chromadb.Collection:
        return self._chroma.get_or_create_collection(_safe_collection_name(user_id))

    async def _run(self, fn, *args, **kwargs):
        """Run a synchronous function in the thread-pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    # ── Indexing ─────────────────────────────────────────────────────────────────

    async def add_document(
        self,
        doc_id: str,
        filename: str,
        text: str,
        scope: str,          # "global" | "personal"
        user_id: Optional[str] = None,
    ) -> int:
        """
        Chunk `text`, embed the chunks, and upsert them into the appropriate
        ChromaDB collection.

        Returns the number of chunks indexed.
        """
        chunks = _chunk_text(text)
        if not chunks:
            return 0

        # Embed all chunks in one (batched) call
        embeddings = await self._emb.embed_texts(chunks)

        ids        = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas  = [
            {
                "source_doc_id":   doc_id,
                "source_doc_name": filename,
                "scope":           scope,
                "user_id":         user_id or "",
                "chunk_index":     i,
            }
            for i in range(len(chunks))
        ]

        def _upsert():
            col = self._global_col() if scope == "global" else self._user_col(user_id)
            col.upsert(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        await self._run(_upsert)
        return len(chunks)

    # ── Deletion ─────────────────────────────────────────────────────────────────

    async def delete_document(
        self,
        doc_id: str,
        scope: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Remove all chunks belonging to `doc_id` from the appropriate collection."""

        def _delete():
            col = self._global_col() if scope == "global" else self._user_col(user_id)
            # Query all chunk IDs for this document
            results = col.get(where={"source_doc_id": doc_id})
            if results and results.get("ids"):
                col.delete(ids=results["ids"])

        await self._run(_delete)

    # ── Retrieval ─────────────────────────────────────────────────────────────────

    async def query(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        n_results: int = 5,
        score_threshold: float = 0.35,
    ) -> List[dict]:
        """
        Retrieve the most relevant chunks from:
          • global regulatory KB (always)
          • user's personal KB (if user_id provided)

        Returns a deduplicated, score-sorted list of chunk dicts:
          {source_doc_id, source_doc_name, scope, chunk_index, text, score}
        """
        if not query_text.strip():
            return []

        query_embedding = await self._emb.embed_single(query_text)

        hits: List[dict] = []

        # ── Global KB ──
        hits += await self._query_collection(
            col_fn=self._global_col,
            query_embedding=query_embedding,
            n_results=n_results,
            score_threshold=score_threshold,
        )

        # ── Personal KB ──
        if user_id:
            hits += await self._query_collection(
                col_fn=lambda: self._user_col(user_id),
                query_embedding=query_embedding,
                n_results=n_results,
                score_threshold=score_threshold,
            )

        # Deduplicate by chunk ID, keep highest score
        seen: dict[str, dict] = {}
        for h in hits:
            cid = h["chunk_id"]
            if cid not in seen or h["score"] > seen[cid]["score"]:
                seen[cid] = h

        # Sort by score descending and cap total results
        sorted_hits = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return sorted_hits[: n_results * 2]  # return up to 2× n_results across both collections

    async def _query_collection(
        self,
        col_fn,
        query_embedding: List[float],
        n_results: int,
        score_threshold: float,
    ) -> List[dict]:
        """Query a single collection and return formatted hits."""

        def _q():
            col = col_fn()
            # Check if the collection has any items first
            count = col.count()
            if count == 0:
                return None
            actual_n = min(n_results, count)
            return col.query(
                query_embeddings=[query_embedding],
                n_results=actual_n,
                include=["documents", "metadatas", "distances"],
            )

        results = await self._run(_q)
        if not results:
            return []

        hits = []
        docs      = results.get("documents",  [[]])[0]
        metas     = results.get("metadatas",  [[]])[0]
        distances = results.get("distances",  [[]])[0]
        ids_      = results.get("ids",        [[]])[0]

        for doc_text, meta, dist, cid in zip(docs, metas, distances, ids_):
            # ChromaDB returns L2 distance; convert to cosine-like score
            # For normalised vectors: cosine_sim ≈ 1 - dist/2
            score = max(0.0, 1.0 - dist / 2.0)
            if score < score_threshold:
                continue
            hits.append({
                "chunk_id":        cid,
                "source_doc_id":   meta.get("source_doc_id", ""),
                "source_doc_name": meta.get("source_doc_name", ""),
                "scope":           meta.get("scope", "global"),
                "user_id":         meta.get("user_id", ""),
                "chunk_index":     meta.get("chunk_index", 0),
                "text":            doc_text,
                "score":           round(score, 4),
            })

        return hits

    # ── Utility ───────────────────────────────────────────────────────────────────

    def format_context_for_prompt(
        self,
        hits: List[dict],
        max_chars: int = 6000,
    ) -> str:
        """
        Format retrieved chunks into a compact string suitable for LLM injection.
        Returns empty string when `hits` is empty.
        """
        if not hits:
            return ""

        lines = ["=== REGULATORY KNOWLEDGE BASE CONTEXT ===",
                 "The following excerpts are from authoritative regulatory and compliance",
                 "reference documents. Use them to ground your analysis.\n"]

        total_chars = sum(len(l) + 1 for l in lines)

        for i, hit in enumerate(hits, 1):
            header = (
                f"[{i}] Source: {hit['source_doc_name']} "
                f"({'Global KB' if hit['scope'] == 'global' else 'Company KB'}) "
                f"| Relevance: {hit['score']:.2f}"
            )
            body   = hit["text"].strip()
            entry  = f"{header}\n{body}\n"

            if total_chars + len(entry) > max_chars:
                # Add truncated entry
                remaining = max_chars - total_chars - len(header) - 5
                if remaining > 100:
                    lines.append(f"{header}\n{body[:remaining]}…\n")
                break

            lines.append(entry)
            total_chars += len(entry)

        lines.append("=== END KNOWLEDGE BASE CONTEXT ===")
        return "\n".join(lines)

    async def collection_stats(self, user_id: Optional[str] = None) -> dict:
        """Return chunk counts for global and personal collections."""

        def _stats():
            g_count = self._global_col().count()
            p_count = self._user_col(user_id).count() if user_id else 0
            return {"global_chunks": g_count, "personal_chunks": p_count}

        return await self._run(_stats)


# Health check for ChromaDB

async def chroma_db_is_healthy():
    """Check whether chroma database is reachable by running stats.

    Returns a dict: {"ok": bool, "error": str|None}
    """
    try:
        rag = get_rag_service()
        await rag.collection_stats()
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}