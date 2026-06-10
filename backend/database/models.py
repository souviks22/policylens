from sqlalchemy import Column, String, Integer, Text, DateTime, Float, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base


class UserRecord(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, index=True)
    username        = Column(String, unique=True, nullable=False, index=True)
    full_name       = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active       = Column(Integer, default=1)   # 1 = active
    created_at      = Column(DateTime, default=datetime.utcnow)

    comparisons = relationship("ComparisonRecord", back_populates="owner", lazy="selectin")
    kb_documents = relationship("KnowledgeBaseDocumentRecord", foreign_keys="KnowledgeBaseDocumentRecord.uploaded_by",back_populates="uploader", lazy="selectin")

class DocumentRecord(Base):
    __tablename__ = "documents"

    id          = Column(String, primary_key=True, index=True)
    filename    = Column(String, nullable=False)
    text        = Column(Text, nullable=False)
    pages       = Column(Integer, default=0)
    word_count  = Column(Integer, default=0)
    char_count  = Column(Integer, default=0)
    sections    = Column(JSON, default=list)
    created_at  = Column(DateTime, default=datetime.utcnow)
    embedding   = Column(JSON, nullable=True)

    comparisons_as_doc1 = relationship("ComparisonRecord", foreign_keys="ComparisonRecord.doc1_id", back_populates="doc1", lazy="selectin")
    comparisons_as_doc2 = relationship("ComparisonRecord", foreign_keys="ComparisonRecord.doc2_id", back_populates="doc2", lazy="selectin")


class ComparisonRecord(Base):
    __tablename__ = "comparisons"

    id                    = Column(String, primary_key=True, index=True)
    user_id               = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    doc1_id               = Column(String, ForeignKey("documents.id"), nullable=False)
    doc2_id               = Column(String, ForeignKey("documents.id"), nullable=False)
    result_json           = Column(Text, nullable=False)
    section_analysis_json = Column(Text, nullable=True)
    total_changes         = Column(Integer, default=0)
    additions             = Column(Integer, default=0)
    deletions             = Column(Integer, default=0)
    modifications         = Column(Integer, default=0)
    overall_impact        = Column(String, default="medium")
    structural_similarity = Column(Float, default=0.0)
    created_at            = Column(DateTime, default=datetime.utcnow)

    owner       = relationship("UserRecord", back_populates="comparisons", lazy="selectin")
    doc1        = relationship("DocumentRecord", foreign_keys=[doc1_id], back_populates="comparisons_as_doc1", lazy="selectin")
    doc2        = relationship("DocumentRecord", foreign_keys=[doc2_id], back_populates="comparisons_as_doc2", lazy="selectin")
    annotations = relationship("AnnotationRecord", back_populates="comparison", cascade="all, delete-orphan", lazy="selectin")


class AnnotationRecord(Base):
    __tablename__ = "annotations"

    id            = Column(String, primary_key=True, index=True)
    comparison_id = Column(String, ForeignKey("comparisons.id"), nullable=False)
    change_id     = Column(String, nullable=False)
    change_type   = Column(String, nullable=True)
    author        = Column(String, default="Reviewer")
    text          = Column(Text, nullable=False)
    resolved      = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)

    comparison = relationship("ComparisonRecord", back_populates="annotations", lazy="selectin")


class KnowledgeBaseDocumentRecord(Base):
    """
    Metadata for each document added to the knowledge base.
    Actual embeddings are stored in ChromaDB (not SQL).

    scope:
        "global"   — available to all users for regulatory grounding
        "personal" — scoped to a single user for company-specific context
    """
    __tablename__ = "kb_documents"

    id          = Column(String, primary_key=True, index=True)
    filename    = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scope       = Column(String, nullable=False, index=True)   # "global" | "personal"
    # uploader / owner
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # For personal docs only; null means global
    user_id     = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    chunk_count = Column(Integer, default=0)
    char_count  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    uploader    = relationship("UserRecord", foreign_keys=[uploaded_by], back_populates="kb_documents", lazy="selectin")
