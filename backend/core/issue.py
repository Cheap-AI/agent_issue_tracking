import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMPONENTS = ("research", "summary", "timeline", "sources", "questions")


def _storage_root() -> Path:
    return Path(os.environ.get("STORAGE_ROOT", "storage"))


def _issues_root() -> Path:
    return _storage_root() / "issues"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue_dir(issue_id: str) -> Path:
    return _issues_root() / issue_id


def _meta_path(issue_id: str) -> Path:
    return issue_dir(issue_id) / "meta.json"


def _next_issue_id() -> str:
    issues_root = _issues_root()
    issues_root.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in issues_root.iterdir():
        if path.is_dir() and path.name.startswith("iss-"):
            try:
                numbers.append(int(path.name.split("-", 1)[1]))
            except ValueError:
                continue
    next_number = max(numbers, default=0) + 1
    return f"iss-{next_number:04d}"


def create_issue(title: str, summary: str) -> dict[str, Any]:
    """Create a new issue folder with meta.json and the 5 knowledge component subfolders."""
    new_id = _next_issue_id()
    new_dir = issue_dir(new_id)
    new_dir.mkdir(parents=True, exist_ok=True)
    for component in COMPONENTS:
        (new_dir / component).mkdir(exist_ok=True)

    meta = {
        "id": new_id,
        "title": title.strip(),
        "summary": summary.strip(),
        "is_active": True,
        "created_at": _utcnow_iso(),
    }
    _meta_path(new_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def list_issues() -> list[dict[str, Any]]:
    """List all issues (reads meta.json from every issue folder), ordered by id."""
    issues_root = _issues_root()
    if not issues_root.exists():
        return []

    issues = []
    for path in sorted(issues_root.iterdir()):
        if not path.is_dir():
            continue
        meta_path = path / "meta.json"
        if meta_path.exists():
            issues.append(json.loads(meta_path.read_text(encoding="utf-8")))
    return issues


def get_issue(issue_id: str) -> dict[str, Any] | None:
    """Return an issue's meta.json contents, or None if it doesn't exist."""
    meta_path = _meta_path(issue_id)
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))
