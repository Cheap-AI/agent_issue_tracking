from fastapi import APIRouter, HTTPException

from backend.workflows.monthly_reports import get_latest_monthly_report, list_monthly_report_versions

router = APIRouter()


@router.get("/api/reports/monthly")
def get_monthly_report(year: int, month: int) -> dict[str, object]:
    """Get the latest versioned monthly discovery report for a given (year, month)."""
    report = get_latest_monthly_report(year, month)
    if report is None:
        raise HTTPException(status_code=404, detail="No monthly report found for that year/month")
    return {"report": report}


@router.get("/api/reports/monthly/{year}/{month}/versions")
def get_monthly_report_versions(year: int, month: int) -> dict[str, object]:
    """Get the full version history of the monthly discovery report for a given (year, month)."""
    versions = list_monthly_report_versions(year, month)
    return {"versions": versions, "count": len(versions)}
