"""Regenerate an issue's summary from its current knowledge.

Not implemented yet — no writer agent exists (see backend/agents/writer).
This will eventually:
1. Read the issue's current research/timeline/sources (backend.core.knowledge.read_current).
2. Ask the writer agent to produce an updated summary.
3. Save the result as a new immutable summary version (backend.core.knowledge.update_component).
"""


def update_summary(issue_id: str) -> None:
    raise NotImplementedError("update_summary is not implemented yet (no writer agent).")
