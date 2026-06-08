import difflib
import re
import uuid
from typing import List, Tuple
from models.schemas import DiffChunk, ChangeType


class TextDiffService:
    """
    Performs multi-level text diff:
    - Line-level diff for structural changes
    - Word-level diff for inline modifications
    - Paragraph-level grouping for semantic context
    """

    def compute_line_diff(self, text1: str, text2: str) -> List[DiffChunk]:
        """Compute line-by-line diff between two texts."""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)

        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))

        chunks = self._parse_differ_output(diff)
        return chunks

    def compute_paragraph_diff(self, text1: str, text2: str) -> List[DiffChunk]:
        """
        Compute paragraph-level diff — better for semantic comparison.
        Groups consecutive changes into logical chunks.
        For large modified blocks, falls back to sentence-level diff so
        that a single changed sentence does not flag the whole paragraph.
        """
        paras1 = self._split_paragraphs(text1)
        paras2 = self._split_paragraphs(text2)

        matcher = difflib.SequenceMatcher(None, paras1, paras2, autojunk=False)
        chunks: List[DiffChunk] = []

        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            old_text = "\n\n".join(paras1[i1:i2]).strip() or None
            new_text = "\n\n".join(paras2[j1:j2]).strip() or None

            if opcode == "equal":
                continue
            elif opcode == "insert":
                chunks.append(DiffChunk(
                    id=str(uuid.uuid4()),
                    type=ChangeType.ADDITION,
                    old_text=None,
                    new_text=new_text,
                    section=self._guess_section(new_text or ""),
                    line_start=j1,
                    line_end=j2,
                ))
            elif opcode == "delete":
                chunks.append(DiffChunk(
                    id=str(uuid.uuid4()),
                    type=ChangeType.DELETION,
                    old_text=old_text,
                    new_text=None,
                    section=self._guess_section(old_text or ""),
                    line_start=i1,
                    line_end=i2,
                ))
            elif opcode == "replace":
                # If the block is large, do sentence-level diff for granularity
                if (old_text and len(old_text) > 500) or (new_text and len(new_text) > 500):
                    sentence_chunks = self._compute_sentence_diff(
                        old_text or "", new_text or "",
                        line_offset=i1,
                    )
                    chunks.extend(sentence_chunks)
                else:
                    chunks.append(DiffChunk(
                        id=str(uuid.uuid4()),
                        type=ChangeType.MODIFICATION,
                        old_text=old_text,
                        new_text=new_text,
                        section=self._guess_section(new_text or old_text or ""),
                        line_start=i1,
                        line_end=i2,
                    ))

        return chunks

    def _compute_sentence_diff(self, old_text: str, new_text: str, line_offset: int = 0) -> List[DiffChunk]:
        """Sentence-level diff for large modified paragraphs."""
        old_sents = self._split_sentences(old_text)
        new_sents = self._split_sentences(new_text)

        matcher = difflib.SequenceMatcher(None, old_sents, new_sents, autojunk=False)
        chunks: List[DiffChunk] = []

        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            o_txt = " ".join(old_sents[i1:i2]).strip() or None
            n_txt = " ".join(new_sents[j1:j2]).strip() or None

            if opcode == "equal":
                continue
            elif opcode == "insert":
                chunks.append(DiffChunk(
                    id=str(uuid.uuid4()),
                    type=ChangeType.ADDITION,
                    old_text=None,
                    new_text=n_txt,
                    section=self._guess_section(n_txt or ""),
                    line_start=line_offset + j1,
                    line_end=line_offset + j2,
                ))
            elif opcode == "delete":
                chunks.append(DiffChunk(
                    id=str(uuid.uuid4()),
                    type=ChangeType.DELETION,
                    old_text=o_txt,
                    new_text=None,
                    section=self._guess_section(o_txt or ""),
                    line_start=line_offset + i1,
                    line_end=line_offset + i2,
                ))
            elif opcode == "replace":
                chunks.append(DiffChunk(
                    id=str(uuid.uuid4()),
                    type=ChangeType.MODIFICATION,
                    old_text=o_txt,
                    new_text=n_txt,
                    section=self._guess_section(n_txt or o_txt or ""),
                    line_start=line_offset + i1,
                    line_end=line_offset + i2,
                ))

        return chunks

    def compute_inline_diff(self, old_text: str, new_text: str) -> Tuple[str, str]:
        """
        Compute word-level inline diff for a pair of text chunks.
        Returns HTML-annotated strings with <ins> and <del> tags.
        """
        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)

        old_html_parts = []
        new_html_parts = []

        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            old_segment = " ".join(old_words[i1:i2])
            new_segment = " ".join(new_words[j1:j2])

            if opcode == "equal":
                old_html_parts.append(old_segment)
                new_html_parts.append(new_segment)
            elif opcode == "insert":
                new_html_parts.append(f'<ins>{new_segment}</ins>')
            elif opcode == "delete":
                old_html_parts.append(f'<del>{old_segment}</del>')
            elif opcode == "replace":
                old_html_parts.append(f'<del>{old_segment}</del>')
                new_html_parts.append(f'<ins>{new_segment}</ins>')

        return " ".join(old_html_parts), " ".join(new_html_parts)

    def get_similarity_ratio(self, text1: str, text2: str) -> float:
        """Calculate overall similarity ratio between two texts."""
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return round(matcher.ratio(), 4)

    def compute_unified_diff(self, text1: str, text2: str,
                             file1: str = "Document A",
                             file2: str = "Document B") -> str:
        """Return a unified diff string for display."""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        diff = difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2, lineterm="")
        return "\n".join(list(diff)[:500])  # cap output

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into meaningful paragraphs."""
        parts = re.split(r"\n\s*\n", text)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) > 15]

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return [s.strip() for s in sentences if s.strip() and len(s) > 10]

    def _parse_differ_output(self, diff: List[str]) -> List[DiffChunk]:
        """Parse raw Differ output into structured DiffChunk list."""
        chunks = []
        i = 0
        while i < len(diff):
            line = diff[i]
            prefix = line[:2]
            content = line[2:].rstrip("\n")

            if prefix == "  ":  # unchanged
                i += 1
                continue
            elif prefix == "+ ":
                chunks.append(DiffChunk(
                    id=str(uuid.uuid4()),
                    type=ChangeType.ADDITION,
                    old_text=None,
                    new_text=content,
                    section=self._guess_section(content),
                ))
                i += 1
            elif prefix == "- ":
                # Check if followed by a "+" (modification rather than pure deletion)
                next_lines = diff[i+1:i+3]
                plus_lines = [l for l in next_lines if l.startswith("+ ")]
                if plus_lines:
                    new_content = plus_lines[0][2:].rstrip("\n")
                    chunks.append(DiffChunk(
                        id=str(uuid.uuid4()),
                        type=ChangeType.MODIFICATION,
                        old_text=content,
                        new_text=new_content,
                        section=self._guess_section(content),
                    ))
                    i += 1
                    # Skip the consumed "+" line
                    while i < len(diff) and diff[i].startswith("+ "):
                        i += 1
                else:
                    chunks.append(DiffChunk(
                        id=str(uuid.uuid4()),
                        type=ChangeType.DELETION,
                        old_text=content,
                        new_text=None,
                        section=self._guess_section(content),
                    ))
                    i += 1
            else:
                i += 1

        return chunks

    def _guess_section(self, text: str) -> str:
        """Try to identify what section a chunk belongs to."""
        if not text:
            return "General"
        # Look for heading-like first line
        first_line = text.split("\n")[0].strip()
        if len(first_line) < 80 and (
            first_line.isupper() or
            re.match(r"^\d+[\.\)]\s+\w", first_line) or
            re.match(r"^(Section|Article|Chapter)\s+", first_line, re.I)
        ):
            return first_line
        return "General"