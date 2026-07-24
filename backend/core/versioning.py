import re
from pathlib import Path

from backend.core.issue import issue_dir

_VERSION_RE = re.compile(r"^v(\d+)\.md$")


def _component_dir(issue_id: str, component: str) -> Path:
    return issue_dir(issue_id) / component


def _existing_versions(issue_id: str, component: str) -> list[int]:
    comp_dir = _component_dir(issue_id, component)
    if not comp_dir.exists():
        return []
    versions = []
    for path in comp_dir.iterdir():
        match = _VERSION_RE.match(path.name)
        if match:
            versions.append(int(match.group(1)))
    return sorted(versions)


def save_version(issue_id: str, component: str, content: str) -> int:
    """Write `content` as the next immutable version of a component. Returns the new version number."""
    comp_dir = _component_dir(issue_id, component)
    comp_dir.mkdir(parents=True, exist_ok=True)
    versions = _existing_versions(issue_id, component)
    next_version = (versions[-1] if versions else 0) + 1
    version_path = comp_dir / f"v{next_version:03d}.md"
    version_path.write_text(content, encoding="utf-8")
    return next_version


def get_current_version(issue_id: str, component: str) -> tuple[int, str] | None:
    """Return (version_number, content) for the latest version of a component, or None if none exist."""
    versions = _existing_versions(issue_id, component)
    if not versions:
        return None
    latest = versions[-1]
    content = (_component_dir(issue_id, component) / f"v{latest:03d}.md").read_text(encoding="utf-8")
    return latest, content


def list_versions(issue_id: str, component: str) -> list[int]:
    """Return all existing version numbers for a component, ascending."""
    return _existing_versions(issue_id, component)
