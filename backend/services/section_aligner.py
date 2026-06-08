from __future__ import annotations

import re
import uuid
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

from services.embeddings import EmbeddingService


# ── Data structures ─────────────────────────────────────────────────────────────

@dataclass
class DocSection:
    index: int
    heading: str
    content: str
    embedding: Optional[List[float]] = None

    @property
    def full_text(self) -> str:
        parts = []
        if self.heading:
            parts.append(self.heading)
        if self.content:
            parts.append(self.content)
        return "\n".join(parts)


@dataclass
class SectionMatchResult:
    id: str
    doc1_section: Optional[str]        # heading (or None if added)
    doc2_section: Optional[str]        # heading (or None if deleted)
    doc1_content: Optional[str]
    doc2_content: Optional[str]
    similarity_score: float
    match_type: str                    # "unchanged" | "modified" | "added" | "deleted"
    doc1_index: Optional[int] = None
    doc2_index: Optional[int] = None


@dataclass
class SectionAlignmentResult:
    matches: List[SectionMatchResult]
    similarity_matrix: List[List[float]]
    doc1_section_labels: List[str]
    doc2_section_labels: List[str]
    overall_structural_similarity: float
    semantic_clone_pairs: List[Tuple[str, str]]   # (doc1_heading, doc2_heading) near-duplicates


# ── Constants ───────────────────────────────────────────────────────────────────

UNCHANGED_THRESHOLD = 0.96
MODIFIED_THRESHOLD  = 0.72
MIN_SECTION_CHARS   = 80
MAX_SECTIONS        = 40


class SectionAligner:
    """
    High-level pipeline:
    1. Split each document into (heading, body) sections.
    2. Embed every section via text-embedding-3-small.
    3. Build an (n × m) cosine similarity matrix.
    4. Run greedy best-match alignment (O(n·m)).
    5. Classify each match as unchanged / modified / added / deleted.
    6. Detect semantic clone pairs (two sections that mean the same thing).
    """

    def __init__(self, embedding_service: EmbeddingService):
        self._emb = embedding_service

    # ── Public ──────────────────────────────────────────────────────────────────

    async def align(
        self,
        doc1_text: str,
        doc2_text: str,
    ) -> SectionAlignmentResult:

        secs1 = self._split_sections(doc1_text)
        secs2 = self._split_sections(doc2_text)

        # Embed all sections in two batches
        texts1 = [s.full_text for s in secs1]
        texts2 = [s.full_text for s in secs2]

        all_texts = texts1 + texts2
        all_embs  = await self._emb.embed_texts(all_texts)

        embs1 = all_embs[: len(secs1)]
        embs2 = all_embs[len(secs1) :]

        for s, e in zip(secs1, embs1):
            s.embedding = e
        for s, e in zip(secs2, embs2):
            s.embedding = e

        # Similarity matrix
        sim_matrix: List[List[float]] = []
        if embs1 and embs2:
            sim_matrix = self._emb.similarity_matrix(embs1, embs2)

        # Greedy alignment
        matches = self._greedy_align(secs1, secs2, sim_matrix)

        # Overall structural similarity = mean score of matched pairs
        matched_scores = [m.similarity_score for m in matches if m.match_type != "unchanged" or True]
        overall = float(np.mean(matched_scores)) if matched_scores else 0.0

        # Semantic clone detection (very high similarity, potentially duplicate sections)
        clones = self._find_clones(secs1, secs2, sim_matrix)

        labels1 = [s.heading or f"Section {s.index + 1}" for s in secs1]
        labels2 = [s.heading or f"Section {s.index + 1}" for s in secs2]

        return SectionAlignmentResult(
            matches=matches,
            similarity_matrix=sim_matrix,
            doc1_section_labels=labels1,
            doc2_section_labels=labels2,
            overall_structural_similarity=round(overall, 4),
            semantic_clone_pairs=clones,
        )

    # ── Section splitting ────────────────────────────────────────────────────────

    def _split_sections(self, text: str) -> List[DocSection]:
        """Split document text into sections by detected headings."""
        lines = text.split("\n")
        sections: List[DocSection] = []
        current_heading = ""
        current_body_lines: List[str] = []

        def flush(heading: str, body_lines: List[str], idx: int):
            body = "\n".join(body_lines).strip()
            if len(body) >= MIN_SECTION_CHARS or heading:
                sections.append(DocSection(
                    index=idx,
                    heading=heading.strip(),
                    content=body,
                ))

        idx = 0
        for line in lines:
            stripped = line.strip()
            if self._is_heading(stripped):
                flush(current_heading, current_body_lines, idx)
                idx += 1
                current_heading = stripped
                current_body_lines = []
            else:
                current_body_lines.append(line)

        flush(current_heading, current_body_lines, idx)

        # Fallback: if only 1 section, chunk by paragraphs
        if len(sections) <= 1:
            sections = self._chunk_by_paragraphs(text)

        return sections[:MAX_SECTIONS]

    def _is_heading(self, line: str) -> bool:
        if not line or len(line) > 120:
            return False
        patterns = [
            r"^\d+[\.\)]\s+[A-Z]",
            r"^(SECTION|ARTICLE|CHAPTER|PART|SCHEDULE)\s+",
            r"^[A-Z][A-Z\s\-]{4,60}$",
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5}$",
        ]
        for p in patterns:
            if re.match(p, line):
                return True
        return False

    def _chunk_by_paragraphs(self, text: str) -> List[DocSection]:
        paras = re.split(r"\n\s*\n", text)
        paras = [p.strip() for p in paras if len(p.strip()) >= MIN_SECTION_CHARS]
        sections = []
        for i, p in enumerate(paras[:MAX_SECTIONS]):
            first_line = p.split("\n")[0][:80]
            sections.append(DocSection(index=i, heading="", content=p))
        return sections

    # ── Greedy alignment ─────────────────────────────────────────────────────────

    def _greedy_align(
        self,
        secs1: List[DocSection],
        secs2: List[DocSection],
        sim_matrix: List[List[float]],
    ) -> List[SectionMatchResult]:

        if not secs1 and not secs2:
            return []

        n, m = len(secs1), len(secs2)
        mat = np.array(sim_matrix) if sim_matrix else np.zeros((n, m))

        matched1 = set()   # indices in secs1 already matched
        matched2 = set()   # indices in secs2 already matched
        matches:  List[SectionMatchResult] = []

        # Build flat list of (score, i, j) and sort descending
        candidates = [
            (mat[i, j], i, j)
            for i in range(n)
            for j in range(m)
        ]
        candidates.sort(reverse=True)

        for score, i, j in candidates:
            if i in matched1 or j in matched2:
                continue
            if score < MODIFIED_THRESHOLD:
                break   # remaining scores are all below threshold → stop
            matched1.add(i)
            matched2.add(j)

            match_type = (
                "unchanged" if score >= UNCHANGED_THRESHOLD else "modified"
            )
            matches.append(SectionMatchResult(
                id=str(uuid.uuid4()),
                doc1_section=secs1[i].heading or f"Section {i + 1}",
                doc2_section=secs2[j].heading or f"Section {j + 1}",
                doc1_content=secs1[i].content[:800],
                doc2_content=secs2[j].content[:800],
                similarity_score=round(float(score), 4),
                match_type=match_type,
                doc1_index=i,
                doc2_index=j,
            ))

        # Unmatched in doc1 → deleted
        for i in range(n):
            if i not in matched1:
                matches.append(SectionMatchResult(
                    id=str(uuid.uuid4()),
                    doc1_section=secs1[i].heading or f"Section {i + 1}",
                    doc2_section=None,
                    doc1_content=secs1[i].content[:800],
                    doc2_content=None,
                    similarity_score=0.0,
                    match_type="deleted",
                    doc1_index=i,
                    doc2_index=None,
                ))

        # Unmatched in doc2 → added
        for j in range(m):
            if j not in matched2:
                matches.append(SectionMatchResult(
                    id=str(uuid.uuid4()),
                    doc1_section=None,
                    doc2_section=secs2[j].heading or f"Section {j + 1}",
                    doc1_content=None,
                    doc2_content=secs2[j].content[:800],
                    similarity_score=0.0,
                    match_type="added",
                    doc1_index=None,
                    doc2_index=j,
                ))

        # Sort by position so UI can display top-to-bottom
        matches.sort(key=lambda m: (m.doc1_index if m.doc1_index is not None else 999,
                                    m.doc2_index if m.doc2_index is not None else 999))
        return matches

    # ── Clone detection ──────────────────────────────────────────────────────────

    def _find_clones(
        self,
        secs1: List[DocSection],
        secs2: List[DocSection],
        sim_matrix: List[List[float]],
        threshold: float = 0.98,
    ) -> List[Tuple[str, str]]:
        """Find (doc1_heading, doc2_heading) pairs with near-identical content."""
        clones = []
        for i, row in enumerate(sim_matrix):
            for j, score in enumerate(row):
                if score >= threshold:
                    h1 = secs1[i].heading or f"Section {i + 1}"
                    h2 = secs2[j].heading or f"Section {j + 1}"
                    clones.append((h1, h2))
        return clones
