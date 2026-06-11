"""
chat_service.py  —  Builds a grounded system prompt from a ComparisonResult
and streams the OpenAI response as SSE.
"""
from __future__ import annotations

import json
from typing import List, AsyncIterator

from openai import AsyncOpenAI

from models.schemas import ComparisonResult


# Maximum semantic changes and section matches to include in context.
# GPT-4o has 128K tokens; a full system prompt here is ~8-14K tokens.
MAX_CHANGES  = 30
MAX_SECTIONS = 25


class ChatService:

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model  = model

    # ── Public ──────────────────────────────────────────────────────────────────

    def build_system_prompt(self, result: ComparisonResult) -> str:
        s = result.summary
        sim = round(result.text_similarity_ratio * 100, 1)
        struct = (
            round(result.section_analysis.overall_structural_similarity * 100, 1)
            if result.section_analysis else "N/A"
        )

        lines: List[str] = []

        lines += [
            "You are the Compliance Analysis Assistant for the following document comparison.",
            "You have full knowledge of every finding in this analysis.",
            "Your job: answer questions about this comparison clearly, accurately, and concisely.",
            "",
            "═" * 60,
            "COMPARISON OVERVIEW",
            "═" * 60,
            f"Document A (Legacy):  {result.doc1_name}",
            f"Document B (Updated): {result.doc2_name}",
            f"Overall Impact:       {s.overall_impact_level.value.upper()}",
            f"Text Similarity:      {sim}%",
            f"Structural Similarity:{struct}%",
            f"Total Changes:        {s.total_changes}  "
            f"(+{s.additions} added, -{s.deletions} deleted, ~{s.modifications} modified, "
            f"{s.regulatory_updates} regulatory)",
            "",
        ]

        # Executive summary
        lines += [
            "═" * 60,
            "EXECUTIVE SUMMARY",
            "═" * 60,
            s.executive_summary,
            "",
        ]

        # Key changes
        if s.key_changes:
            lines += ["KEY CHANGES"]
            for kc in s.key_changes:
                lines.append(f"  • {kc}")
            lines.append("")

        # Risk areas
        if s.risk_areas:
            lines += ["RISK AREAS"]
            for ra in s.risk_areas:
                lines.append(f"  ⚠ {ra}")
            lines.append("")

        # Compliance flags
        if s.compliance_flags:
            lines += ["COMPLIANCE FLAGS"]
            for cf in s.compliance_flags:
                lines.append(f"  ⚑ {cf}")
            lines.append("")

        # Semantic changes
        changes = result.semantic_changes[:MAX_CHANGES]
        if changes:
            lines += [
                "═" * 60,
                f"SEMANTIC CHANGES  ({len(result.semantic_changes)} total, showing {len(changes)})",
                "═" * 60,
            ]
            for i, chg in enumerate(changes, 1):
                lines.append(
                    f"\n[{i}] {chg.change_type.value.upper()} | "
                    f"Impact: {chg.impact_level.value.upper()} | "
                    f"Section: {chg.section or 'General'}"
                )
                lines.append(f"    Summary: {chg.summary}")
                if chg.old_content:
                    lines.append(f"    Before: {chg.old_content[:300]}")
                if chg.new_content:
                    lines.append(f"    After:  {chg.new_content[:300]}")
                if chg.explanation:
                    lines.append(f"    Analysis: {chg.explanation[:400]}")
                if chg.business_impact:
                    lines.append(f"    Business: {chg.business_impact[:200]}")
                if chg.compliance_impact:
                    lines.append(f"    Compliance: {chg.compliance_impact[:200]}")
                if chg.regulatory_impact:
                    lines.append(f"    Regulatory: {chg.regulatory_impact[:200]}")
                if chg.recommendations:
                    lines.append(f"    Recommendations: {'; '.join(chg.recommendations[:3])}")
                if chg.regulatory_impact:
                    lines.append(f"    Regulatory refs: {chg.regulatory_impact[:3]}")
            lines.append("")

        # Section analysis
        if result.section_analysis:
            sa = result.section_analysis
            matches = sa.matches[:MAX_SECTIONS]
            lines += [
                "═" * 60,
                f"SECTION ALIGNMENT  ({len(sa.matches)} sections, showing {len(matches)})",
                "═" * 60,
            ]
            for m in matches:
                a = m.doc1_section or "—"
                b = m.doc2_section or "—"
                score = f"{m.similarity_score:.0%}" if m.similarity_score > 0 else ""
                lines.append(
                    f"  [{m.match_type.upper():10}]  {a:35} ↔  {b:35}  {score}"
                )
            if sa.semantic_clone_pairs:
                lines.append("")
                lines.append("  Clone pairs (≥98% similar):")
                for h1, h2 in sa.semantic_clone_pairs:
                    lines.append(f"    {h1}  ↔  {h2}")
            lines.append("")

        # Instructions
        lines += [
            "═" * 60,
            "INSTRUCTIONS",
            "═" * 60,
            "1. You are scoped to this comparison only.",
            "2. Answer questions about: specific changes, their implications, "
            "recommendations, section-level differences, regulatory citations, "
            "risk interpretation, or any finding in this analysis.",
            "3. You MUST NOT contradict the analysis above. "
            "If your reasoning leads to a different conclusion, say the analysis found X "
            "and explain why there may be nuance.",
            "4. If asked something not covered by the analysis, say so clearly "
            "and offer what partial insight you can.",
            "5. For questions completely outside this comparison, "
            "politely redirect the user back to the document comparison.",
            "6. Be precise with change numbers, section names, and impact levels. "
            "Cite the relevant change when answering specific questions.",
            "7. Format answers clearly: use bullet points for lists, "
            "bold key terms, and keep responses concise unless depth is asked for.",
            "8. Keep responses super short. Prefer one concise sentence or at most three bullet points unless the user explicitly asks for more detail.",
            "9. Use markdown formatting in your response: headings, bold, and lists are preferred when helpful.",
        ]

        return "\n".join(lines)

    async def stream(
        self,
        system_prompt: str,
        messages: List[dict],
    ) -> AsyncIterator[str]:
        """
        Call OpenAI with stream=True.
        Yields SSE-formatted strings: 'data: {text}\n\n'
        Sends 'data: [DONE]\n\n' when finished.
        """
        openai_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            role    = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content.strip():
                openai_messages.append({"role": role, "content": content})

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    # Escape newlines inside SSE data field
                    safe = delta.content.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"

        except Exception as exc:
            error_msg = f"Error: {str(exc)[:200]}"
            yield f"data: {error_msg}\n\n"

        finally:
            yield "data: [DONE]\n\n"
