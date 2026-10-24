"""Versioned, per-(year, month) discovery digests.

Each discovery run appends a new immutable version for its (year, month) rather than mutating
a prior report (mirrors backend/core/versioning.py's Component pattern, scoped by (year, month)
instead of (issue_id, component_type)). Every version has two sections:

- overview: factual aggregate of what was found/created this month (issues, API usage, tags).
- big_picture: best-effort cross-report synthesis. Full month-over-month trend analysis is not
  implemented yet - today this just carries forward the prior version's big_picture plus a
  short delta note, per explicit scope decision.
"""
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text

from backend.core.db import get_session
from backend.models.db_models import DiscoveryReport, MonthlyReport
from backend.services.chunking import chunk_text
from backend.services.embedding import generate_embeddings_batch


def _advisory_lock_key(year: int, month: int) -> str:
    return f"monthly_report:{year}:{month}"


def get_next_version(year: int, month: int) -> int:
    """Return the next version number for a (year, month), using an advisory lock to avoid races."""
    with get_session() as session:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": _advisory_lock_key(year, month)},
        )
        current_max = session.execute(
            select(func.max(MonthlyReport.version)).where(
                MonthlyReport.year == year, MonthlyReport.month == month
            )
        ).scalar_one_or_none()
        return (current_max or 0) + 1


def get_latest_monthly_report(year: int, month: int) -> dict[str, Any] | None:
    """Return the latest version of the (year, month) report, or None if none exist."""
    with get_session() as session:
        report = session.execute(
            select(MonthlyReport)
            .where(MonthlyReport.year == year, MonthlyReport.month == month)
            .order_by(MonthlyReport.version.desc())
            .limit(1)
        ).scalar_one_or_none()
        if report is None:
            return None
        return _report_to_dict(report)


def list_monthly_report_versions(year: int, month: int) -> list[dict[str, Any]]:
    """Return all versions of the (year, month) report, oldest first."""
    with get_session() as session:
        reports = session.execute(
            select(MonthlyReport)
            .where(MonthlyReport.year == year, MonthlyReport.month == month)
            .order_by(MonthlyReport.version.asc())
        ).scalars().all()
        return [_report_to_dict(report) for report in reports]


def _report_to_dict(report: MonthlyReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "year": report.year,
        "month": report.month,
        "version": report.version,
        "overview": report.overview,
        "big_picture": report.big_picture,
        "metadata": report.metadata_json,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def _build_overview(year: int, month: int, created_issues: list[dict]) -> tuple[str, dict]:
    """Aggregate all discovery_reports rows created in (year, month) into a factual overview."""
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_end = datetime(next_year, next_month, 1, tzinfo=timezone.utc)

    with get_session() as session:
        rows = session.execute(
            select(DiscoveryReport).where(
                DiscoveryReport.created_at >= month_start,
                DiscoveryReport.created_at < month_end,
            )
        ).scalars().all()

        total_runs = len(rows)
        total_created = sum(row.actual_created for row in rows)
        total_tavily = sum((row.api_usage or {}).get("tavily", {}).get("calls", 0) for row in rows)
        total_perplexity = sum((row.api_usage or {}).get("perplexity", {}).get("calls", 0) for row in rows)

        all_tags: list[str] = []
        for row in rows:
            for finding in row.findings or []:
                all_tags.extend(finding.get("tags", []))
    all_tags.extend(tag for issue in created_issues for tag in issue.get("tags", []))
    top_tags = [tag for tag, _ in Counter(all_tags).most_common(8)]

    metadata = {
        "total_runs": total_runs,
        "total_issues_created": total_created,
        "api_calls": {"tavily": total_tavily, "perplexity": total_perplexity},
        "top_tags": top_tags,
    }

    lines = [
        f"## Monthly Overview: {year}-{month:02d}",
        "",
        f"- Discovery runs this month: {total_runs}",
        f"- Issues created this month: {total_created}",
        f"- API usage: {total_tavily} Tavily calls, {total_perplexity} Perplexity calls",
    ]
    if top_tags:
        lines.append(f"- Common themes: {', '.join(top_tags)}")
    lines.append("")
    if created_issues:
        lines.append("### Issues from this run")
        for issue in created_issues:
            lines.append(f"- {issue.get('title')}: {issue.get('why', '')[:160]}")

    return "\n".join(lines), metadata


def _build_big_picture(year: int, month: int, prior_version: dict[str, Any] | None, overview: str) -> str:
    """Best-effort cross-report synthesis. Full trend analysis across months is out of scope for now."""
    if prior_version is None:
        return (
            f"## Big Picture: {year}-{month:02d}\n\n"
            "This is the first report for this month - no prior version to compare against yet. "
            "Cross-month trend synthesis is not implemented yet; this section currently just "
            "carries forward context between versions within the same month."
        )
    return (
        f"## Big Picture: {year}-{month:02d} (v{prior_version['version'] + 1})\n\n"
        f"{prior_version['big_picture']}\n\n"
        "### What changed since the previous version\n"
        f"{overview}\n\n"
        "(Note: full month-over-month trend synthesis across the issue history is not "
        "implemented yet - this section is best-effort for now.)"
    )


def generate_monthly_report(year: int, month: int, created_issues: list[dict] | None = None) -> dict[str, Any]:
    """Build overview + big_picture content for (year, month) from all discovery_reports in that month."""
    overview, metadata = _build_overview(year, month, created_issues or [])
    prior_version = get_latest_monthly_report(year, month)
    big_picture = _build_big_picture(year, month, prior_version, overview)
    return {"overview": overview, "big_picture": big_picture, "metadata": metadata}


def save_monthly_report(year: int, month: int, overview: str, big_picture: str, metadata: dict) -> int:
    """Insert a new immutable version of the (year, month) report. Returns the new monthly_report id."""
    version = get_next_version(year, month)

    with get_session() as session:
        report = MonthlyReport(
            year=year,
            month=month,
            version=version,
            overview=overview,
            big_picture=big_picture,
            metadata_json=metadata,
        )
        session.add(report)
        session.flush()
        report_id = report.id
        session.commit()

    digest_text = f"{overview}\n\n{big_picture}"
    chunks = chunk_text(digest_text)
    if chunks:
        embeddings = generate_embeddings_batch(chunks)
        # Raw SQL with explicit vector cast - ORM bulk-insert sends embedding as ::TEXT,
        # which Postgres rejects for a vector(1536) column across multi-row batches.
        insert_sql = text(
            """
            INSERT INTO monthly_report_chunks (monthly_report_id, chunk_index, chunk_text, embedding)
            VALUES (:monthly_report_id, :chunk_index, :chunk_text, CAST(:embedding AS vector))
            """
        )
        with get_session() as session:
            for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                session.execute(
                    insert_sql,
                    {
                        "monthly_report_id": report_id,
                        "chunk_index": chunk_index,
                        "chunk_text": chunk,
                        "embedding": embedding_str,
                    },
                )
            session.commit()

    return report_id
