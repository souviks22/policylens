import json
import uuid
import re
from typing import List, Optional
from openai import AsyncOpenAI
from models.schemas import (
    SemanticChange, ChangeType, ImpactLevel,
    ComparisonSummary, DiffChunk
)
import tiktoken


class SemanticAnalyzer:
    """
    Uses OpenAI to perform semantic comparison and impact analysis.
    Classifies changes and explains business/compliance implications.
    """

    def __init__(self, base_url: str, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            try:
                self._encoder = tiktoken.encoding_for_model("gpt-4o")
            except Exception:
                self._encoder = tiktoken.get_encoding("cl100k_base")
        return self._encoder

    def _count_tokens(self, text: str) -> int:
        enc = self._get_encoder()
        return len(enc.encode(text))

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        enc = self._get_encoder()
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return enc.decode(tokens[:max_tokens]) + "\n[... truncated ...]"

    async def analyze_changes(
        self,
        diff_chunks: List[DiffChunk],
        doc1_text: str,
        doc2_text: str,
        doc1_name: str,
        doc2_name: str,
    ) -> List[SemanticChange]:
        """
        Analyze diff chunks semantically and return enriched SemanticChange objects.
        Batches chunks to stay within token limits.
        """
        if not diff_chunks:
            return []

        # Limit to most significant chunks (avoid huge payloads)
        significant_chunks = self._prioritize_chunks(diff_chunks, max_chunks=25)

        # Build a compact diff description
        diff_description = self._build_diff_description(significant_chunks)

        prompt = f"""You are a senior legal and compliance analyst specializing in policy document review.

You are comparing two policy documents:
- Document A (Legacy): "{doc1_name}"
- Document B (Updated): "{doc2_name}"

Below are the detected textual differences between the two documents:

---DIFFERENCES---
{diff_description}
---END DIFFERENCES---

For each meaningful difference, provide a structured semantic analysis. Return a JSON array where each element has:
{{
  "id": "<unique string>",
  "change_type": "<addition|deletion|modification|regulatory_update>",
  "summary": "<one-line summary of what changed>",
  "old_content": "<original text or null>",
  "new_content": "<new text or null>",
  "section": "<section/area of the document>",
  "business_impact": "<how this affects business operations>",
  "compliance_impact": "<how this affects regulatory compliance>",
  "regulatory_impact": "<specific regulations or standards affected, e.g. GDPR, SOX, HIPAA>",
  "impact_level": "<high|medium|low|none>",
  "explanation": "<detailed plain-language explanation of why this change matters>",
  "recommendations": ["<action item 1>", "<action item 2>"]
}}

Focus on:
1. Changes that affect legal obligations, penalties, or liability
2. Changes to data handling, privacy, or security requirements
3. Changes to reporting or audit requirements
4. Changes to employee/stakeholder rights or responsibilities
5. Changes to timelines, deadlines, or enforcement mechanisms

Return ONLY the JSON array, no other text."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000,
            )
            raw = response.choices[0].message.content or "{}"
            parsed = json.loads(raw)

            # Handle both {"changes": [...]} and direct array
            if isinstance(parsed, dict):
                items = parsed.get("changes", parsed.get("items", list(parsed.values())[0] if parsed else []))
            else:
                items = parsed

            return self._parse_semantic_changes(items, diff_chunks)

        except Exception as e:
            # Fallback: return basic semantic changes from diff chunks
            return self._fallback_semantic_changes(diff_chunks, str(e))

    async def generate_executive_summary(
        self,
        semantic_changes: List[SemanticChange],
        doc1_name: str,
        doc2_name: str,
        similarity_ratio: float,
    ) -> ComparisonSummary:
        """Generate an executive-level summary of all changes."""

        changes_text = "\n".join([
            f"- [{c.change_type.value.upper()}] {c.summary} (Impact: {c.impact_level.value})"
            for c in semantic_changes[:30]
        ])

        additions = sum(1 for c in semantic_changes if c.change_type == ChangeType.ADDITION)
        deletions = sum(1 for c in semantic_changes if c.change_type == ChangeType.DELETION)
        modifications = sum(1 for c in semantic_changes if c.change_type == ChangeType.MODIFICATION)
        regulatory = sum(1 for c in semantic_changes if c.change_type == ChangeType.REGULATORY)

        prompt = f"""You are a Chief Compliance Officer reviewing a policy document revision.

Documents compared:
- Legacy: "{doc1_name}"
- Updated: "{doc2_name}"
- Overall similarity: {similarity_ratio * 100:.1f}%

Changes detected:
{changes_text if changes_text else "No significant changes detected."}

Provide an executive summary in JSON format:
{{
  "executive_summary": "<2-3 paragraph executive summary of the changes and their significance>",
  "overall_impact_level": "<high|medium|low|none>",
  "key_changes": ["<top 5 most important changes as bullet points>"],
  "risk_areas": ["<areas of elevated risk or concern>"],
  "compliance_flags": ["<specific compliance issues requiring immediate attention>"]
}}

Return ONLY valid JSON, no other text."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)

            overall_impact_str = data.get("overall_impact_level", "medium").lower()
            try:
                overall_impact = ImpactLevel(overall_impact_str)
            except ValueError:
                overall_impact = ImpactLevel.MEDIUM

            return ComparisonSummary(
                total_changes=len(semantic_changes),
                additions=additions,
                deletions=deletions,
                modifications=modifications,
                regulatory_updates=regulatory,
                overall_impact_level=overall_impact,
                executive_summary=data.get("executive_summary", "Analysis complete."),
                key_changes=data.get("key_changes", []),
                risk_areas=data.get("risk_areas", []),
                compliance_flags=data.get("compliance_flags", []),
            )

        except Exception:
            return ComparisonSummary(
                total_changes=len(semantic_changes),
                additions=additions,
                deletions=deletions,
                modifications=modifications,
                regulatory_updates=regulatory,
                overall_impact_level=ImpactLevel.MEDIUM,
                executive_summary=f"Comparison of '{doc1_name}' and '{doc2_name}' complete. "
                                  f"{len(semantic_changes)} changes detected with {similarity_ratio*100:.1f}% similarity.",
                key_changes=[c.summary for c in semantic_changes[:5]],
                risk_areas=[],
                compliance_flags=[],
            )

    def _prioritize_chunks(self, chunks: List[DiffChunk], max_chunks: int) -> List[DiffChunk]:
        """Select most significant chunks. Prefer longer / non-trivial changes."""
        def chunk_score(c: DiffChunk) -> int:
            text = (c.old_text or "") + (c.new_text or "")
            return len(text)

        sorted_chunks = sorted(chunks, key=chunk_score, reverse=True)
        return sorted_chunks[:max_chunks]

    def _build_diff_description(self, chunks: List[DiffChunk]) -> str:
        parts = []
        for i, chunk in enumerate(chunks, 1):
            ctype = chunk.type.value.upper()
            if chunk.type == ChangeType.ADDITION:
                parts.append(f"[{i}] {ctype}\nADDED: {chunk.new_text}")
            elif chunk.type == ChangeType.DELETION:
                parts.append(f"[{i}] {ctype}\nREMOVED: {chunk.old_text}")
            elif chunk.type in (ChangeType.MODIFICATION, ChangeType.REGULATORY):
                parts.append(
                    f"[{i}] {ctype}\n"
                    f"BEFORE: {chunk.old_text}\n"
                    f"AFTER: {chunk.new_text}"
                )
        return "\n\n".join(parts)

    def _parse_semantic_changes(
        self, items: list, original_chunks: List[DiffChunk]
    ) -> List[SemanticChange]:
        changes = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                change_type_str = item.get("change_type", "modification").lower().replace(" ", "_")
                try:
                    change_type = ChangeType(change_type_str)
                except ValueError:
                    change_type = ChangeType.MODIFICATION

                impact_str = item.get("impact_level", "medium").lower()
                try:
                    impact = ImpactLevel(impact_str)
                except ValueError:
                    impact = ImpactLevel.MEDIUM

                regulatory_impact_list = item.get("regulatory_impact", [])
                try:
                    regulatory_impact = ", ".join(regulatory_impact_list)
                except Exception:
                    regulatory_impact = ""

                changes.append(SemanticChange(
                    id=item.get("id", str(uuid.uuid4())),
                    change_type=change_type,
                    summary=item.get("summary", "Change detected"),
                    old_content=item.get("old_content"),
                    new_content=item.get("new_content"),
                    section=item.get("section", "General"),
                    business_impact=item.get("business_impact", ""),
                    compliance_impact=item.get("compliance_impact", ""),
                    regulatory_impact=regulatory_impact,
                    impact_level=impact,
                    explanation=item.get("explanation", ""),
                    recommendations=item.get("recommendations", []),
                ))
            except Exception:
                continue
        return changes

    def _fallback_semantic_changes(self, chunks: List[DiffChunk], error: str) -> List[SemanticChange]:
        changes = []
        for chunk in chunks[:20]:
            changes.append(SemanticChange(
                id=str(uuid.uuid4()),
                change_type=chunk.type,
                summary=f"{chunk.type.value.title()} in {chunk.section or 'document'}",
                old_content=chunk.old_text,
                new_content=chunk.new_text,
                section=chunk.section or "General",
                business_impact="Manual review required.",
                compliance_impact="Manual review required.",
                regulatory_impact="Unknown",
                impact_level=ImpactLevel.MEDIUM,
                explanation=f"Text change detected. AI analysis unavailable: {error[:100]}",
                recommendations=["Review this change manually with a compliance officer."],
            ))
        return changes
