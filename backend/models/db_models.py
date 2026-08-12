"""SQLAlchemy ORM models mapping to the Supabase Postgres schema.

Tables:
- issues: issue metadata (replaces meta.json files)
- components: versioned knowledge components (replaces v001.md, v002.md, ... files)
- component_embeddings: vector embeddings for RAG semantic search
- events: discrete timeline events with dates
- tracked_issues: curated top-N issues leaderboard
- global_docs: shared rubric/ranking/taxonomy documents (replaces storage/global/*.md)
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base

COMPONENTS = ("research", "summary", "timeline", "sources", "questions")

# Generates the numeric part of "iss-0001" style issue IDs atomically.
issue_id_seq = Sequence("issue_id_seq", start=1, metadata=Base.metadata)


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    why: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    components: Mapped[list["Component"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["ComponentEmbedding"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    tracked_issue: Mapped["TrackedIssue"] = relationship(
        back_populates="issue", uselist=False, cascade="all, delete-orphan"
    )


class Component(Base):
    __tablename__ = "components"
    __table_args__ = (
        UniqueConstraint("issue_id", "component_type", "version", name="uq_component_version"),
        CheckConstraint(
            "component_type IN ('research', 'summary', 'timeline', 'sources', 'questions')",
            name="ck_component_type",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    component_type: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    issue: Mapped["Issue"] = relationship(back_populates="components")
    embeddings: Mapped[list["ComponentEmbedding"]] = relationship(
        back_populates="component", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="component", cascade="all, delete-orphan"
    )


class GlobalDoc(Base):
    __tablename__ = "global_docs"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ComponentEmbedding(Base):
    """Vector embeddings for semantic search via pgvector.
    
    Each row represents one chunk of a component version.
    Embeddings are generated using OpenAI text-embedding-3-small (1536 dimensions).
    """
    __tablename__ = "component_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    component_type: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)  # Stored as text, cast to vector(1536) in queries
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    component: Mapped["Component"] = relationship(back_populates="embeddings")
    issue: Mapped["Issue"] = relationship(back_populates="embeddings")


class Event(Base):
    """Discrete timeline events associated with issues.
    
    Tracks when events happened (event_date) vs when we learned about them (discovered_at).
    Can be manually created or extracted by agents from component updates.
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Nullable if date unknown
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_urls: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    component_id: Mapped[int | None] = mapped_column(
        ForeignKey("components.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    issue: Mapped["Issue"] = relationship(back_populates="events")
    component: Mapped["Component"] = relationship(back_populates="events")


class TrackedIssue(Base):
    """Curated top-N issues leaderboard.
    
    Managed by the curation agent. Issues are scored on multiple dimensions
    (severity, impact, scale, recency) and ranked. Top N are kept active.
    """
    __tablename__ = "tracked_issues"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issue_id: Mapped[str] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    dimension_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example: {"severity": 8, "impact": 7, "scale": 9, "recency": 6}
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    issue: Mapped["Issue"] = relationship(back_populates="tracked_issue")


class IssueEmbedding(Base):
    """Vector embeddings of issues for fast duplicate detection.
    
    One row per issue, embedding built from title + summary + why.
    Used by discovery agent for semantic deduplication before creating new issues.
    """
    __tablename__ = "issue_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issue_id: Mapped[str] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    embedding: Mapped[str] = mapped_column(Text, nullable=False)  # Stored as text, cast to vector(1536) in queries
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DiscoveryReport(Base):
    """Discovery agent run reports stored in Postgres.
    
    Replaces JSON file storage (storage/discovery_reports/*.json).
    Each report captures metadata, API usage, findings, and proposed duplicates.
    """
    __tablename__ = "discovery_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    target_count: Mapped[int] = mapped_column(nullable=False)
    actual_created: Mapped[int] = mapped_column(nullable=False)
    iterations: Mapped[int] = mapped_column(nullable=False)
    review_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_usage: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    findings: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    proposed_duplicates: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default="")  # Changed to Text for narrative summaries
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chunks: Mapped[list["DiscoveryReportChunk"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class DiscoveryReportChunk(Base):
    """Chunked and embedded discovery reports for semantic memory recall.
    
    Discovery agent can query past reports to recall effective strategies,
    avoid repeating failed approaches, and learn from past runs.
    """
    __tablename__ = "discovery_report_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("discovery_reports.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)  # Stored as text, cast to vector(1536) in queries
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report: Mapped["DiscoveryReport"] = relationship(back_populates="chunks")
