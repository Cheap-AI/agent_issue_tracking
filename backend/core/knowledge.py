from backend.core import versioning
from backend.core.issue import COMPONENTS


def update_component(issue_id: str, component: str, new_content: str) -> int:
    """Save new_content as the next immutable version of a knowledge component
    (research/summary/timeline/sources/questions). Returns the new version number."""
    if component not in COMPONENTS:
        raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
    return versioning.save_version(issue_id, component, new_content)


def read_current(issue_id: str, component: str) -> tuple[int, str] | None:
    """Return (version_number, content) for the current (latest) version of a component, or None."""
    return versioning.get_current_version(issue_id, component)


def read_history(issue_id: str, component: str) -> list[int]:
    """Return all version numbers stored for a component, ascending."""
    return versioning.list_versions(issue_id, component)
