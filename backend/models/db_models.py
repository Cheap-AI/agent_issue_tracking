"""SQLAlchemy ORM models mapping to the Supabase Postgres schema.

Tables:
- issues: issue metadata (replaces meta.json files)
- components: versioned knowledge components (replaces v001.md, v002.md, ... files)
- global_docs: shared rubric/ranking/taxonomy documents (replaces storage/global/*.md)
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
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
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    components: Mapped[list["Component"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
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


class GlobalDoc(Base):
    __tablename__ = "global_docs"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
