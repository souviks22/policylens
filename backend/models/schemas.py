from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum
from datetime import datetime


class ChangeType(str, Enum):
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    REGULATORY = "regulatory_update"
    UNCHANGED = "unchanged"


class ImpactLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class DiffChunk(BaseModel):
    id: str
    type: ChangeType
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    section: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class SemanticChange(BaseModel):
    id: str
    change_type: ChangeType
    summary: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    section: Optional[str] = None
    business_impact: str
    compliance_impact: str
    regulatory_impact: str
    impact_level: ImpactLevel
    explanation: str
    recommendations: List[str] = Field(default_factory=list)


class DocumentStats(BaseModel):
    total_pages: int
    total_words: int
    total_characters: int
    sections_detected: List[str]


class ComparisonSummary(BaseModel):
    total_changes: int
    additions: int
    deletions: int
    modifications: int
    regulatory_updates: int
    overall_impact_level: ImpactLevel
    executive_summary: str
    key_changes: List[str]
    risk_areas: List[str]
    compliance_flags: List[str]


class SectionMatch(BaseModel):
    id: str
    doc1_section: Optional[str] = None
    doc2_section: Optional[str] = None
    doc1_content: Optional[str] = None
    doc2_content: Optional[str] = None
    similarity_score: float
    match_type: str   # "unchanged" | "modified" | "added" | "deleted"
    doc1_index: Optional[int] = None
    doc2_index: Optional[int] = None


class ClauseSimilarity(BaseModel):
    """A single clause from doc1 matched to top-k clauses from doc2."""
    doc1_clause: str
    doc1_section: Optional[str] = None
    matches: List[dict]   # [{clause, section, score}]


class SectionAnalysis(BaseModel):
    matches: List[SectionMatch]
    similarity_matrix: List[List[float]]
    doc1_section_labels: List[str]
    doc2_section_labels: List[str]
    overall_structural_similarity: float
    semantic_clone_pairs: List[List[str]]  # [[h1, h2], ...]


class AnnotationCreate(BaseModel):
    comparison_id: str
    change_id: str
    change_type: Optional[str] = "semantic"   # "semantic"|"diff"|"section"
    author: Optional[str] = "Reviewer"
    text: str


class AnnotationResponse(BaseModel):
    id: str
    comparison_id: str
    change_id: str
    change_type: Optional[str]
    author: str
    text: str
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ComparisonListItem(BaseModel):
    id: str
    doc1_name: str
    doc2_name: str
    total_changes: int
    additions: int
    deletions: int
    modifications: int
    overall_impact: str
    structural_similarity: float
    created_at: datetime

    class Config:
        from_attributes = True


class ComparisonResult(BaseModel):
    comparison_id: str
    doc1_name: str
    doc2_name: str
    doc1_stats: DocumentStats
    doc2_stats: DocumentStats
    diff_chunks: List[DiffChunk]
    semantic_changes: List[SemanticChange]
    summary: ComparisonSummary
    doc1_content: str
    doc2_content: str
    doc1_sections: List[str]
    doc2_sections: List[str]
    section_analysis: Optional[SectionAnalysis] = None
    text_similarity_ratio: float = 0.0


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    pages: int
    word_count: int
    status: str = "processed"


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
