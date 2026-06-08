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


class SectionEmbeddingRecord(Base):
    __tablename__ = "section_embeddings"

    id              = Column(String, primary_key=True, index=True)
    document_id     = Column(String, ForeignKey("documents.id"), nullable=False)
    section_heading = Column(String, nullable=True)
    section_index   = Column(Integer, nullable=False)
    content         = Column(Text, nullable=False)
    embedding       = Column(JSON, nullable=False)
    created_at      = Column(DateTime, default=func.now())
