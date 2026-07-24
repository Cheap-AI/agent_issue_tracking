"""Refresh an existing issue's research with new findings.

Not implemented yet — no researcher agent exists (see backend/agents/researcher).
This will eventually:
1. Read the issue's current research version (backend.core.knowledge.read_current).
2. Ask the researcher agent to produce an updated version.
3. Save the result as a new immutable research version (backend.core.knowledge.update_component).
"""


def update_issue(issue_id: str) -> None:
    raise NotImplementedError("update_issue is not implemented yet (no researcher agent).")
