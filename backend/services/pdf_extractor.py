import pdfplumber
import re
from typing import Tuple, List
from io import BytesIO


class PDFExtractor:
    """Extracts and structures text content from PDF documents."""

    def extract_text(self, file_bytes: bytes) -> Tuple[str, int, List[str]]:
        """
        Extract text from PDF bytes.
        Returns: (full_text, page_count, detected_sections)
        """
        full_text_parts = []
        page_count = 0

        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text_parts.append(text.strip())

        full_text = "\n\n".join(full_text_parts)
        full_text = self._clean_text(full_text)
        sections = self._detect_sections(full_text)

        return full_text, page_count, sections

    def _clean_text(self, text: str) -> str:
        """Clean extracted text: normalize whitespace, fix common artifacts."""
        # Normalize unicode dashes and quotes
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')

        # Remove excessive whitespace within lines
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line).strip()
            cleaned_lines.append(line)

        # Collapse more than 2 consecutive blank lines
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # If the text looks like one giant line (poor PDF extraction),
        # insert paragraph breaks at sentence boundaries so diff can be granular.
        lines = text.split("\n")
        avg_line_len = sum(len(l) for l in lines) / max(len(lines), 1)
        if avg_line_len > 200:
            text = self._insert_sentence_breaks(text)

        return text.strip()

    def _insert_sentence_breaks(self, text: str) -> str:
        """Insert double newlines between sentences for poorly-structured PDFs."""
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return "\n\n".join(s.strip() for s in sentences if s.strip())

    def _detect_sections(self, text: str) -> List[str]:
        """
        Detect section headings in the document.
        Looks for numbered sections, ALL CAPS headings, or Title Case short lines.
        """
        sections = []
        lines = text.split("\n")

        heading_patterns = [
            r"^(\d+\.[\d\.]*)\s+[A-Z]",          # 1. or 1.1. numbered
            r"^(SECTION|ARTICLE|CHAPTER)\s+\w",   # SECTION X
            r"^([A-Z][A-Z\s]{5,50})$",            # ALL CAPS lines
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,6})$",  # Title Case short
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue
            for pattern in heading_patterns:
                if re.match(pattern, line) and len(line) < 120:
                    sections.append(line)
                    break

        # Deduplicate while preserving order
        seen = set()
        unique_sections = []
        for s in sections:
            if s not in seen:
                seen.add(s)
                unique_sections.append(s)

        return unique_sections[:50]  # cap at 50 sections

    def get_word_count(self, text: str) -> int:
        return len(text.split())

    def get_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (double newline separated)."""
        paragraphs = re.split(r"\n\n+", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def get_sentences(self, text: str) -> List[str]:
        """Split text into sentences for granular comparison."""
        return self._split_sentences(text)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return [s.strip() for s in sentences if s.strip() and len(s) > 10]