"""Agentic pipeline: discover+research -> judge -> summarize+rank -> judge -> human review -> persist.

Orchestrates the draft-mode agents (backend/agents/discover_research, summarize_rank, judge)
as a LangGraph StateGraph with bounded retry loops and an interrupt()-based human-in-the-loop
gate. Nothing is written to the database until a human approves via resume(). See
backend/workflows/update_issue.py / discover_issue.py for the existing Langfuse conventions
this reuses (propagate_attributes + start_as_current_observation).

Checkpointing: in-memory (InMemorySaver). This means pending runs are lost on process
restart - acceptable for now, a durable (Postgres) checkpointer is a deliberate future step.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Literal, TypedDict

from langfuse import get_client, propagate_attributes
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.agents.discover_research.agent import discover_and_research
from backend.agents.judge.agent import judge_research, judge_summary
from backend.agents.ranking.agent import upsert_tracked_issue
from backend.agents.summarize_rank.agent import summarize_and_rank
from backend.core.issue import create_issue
from backend.core.knowledge import update_component
from backend.workflows.collect_events import save_events_to_db

langfuse = get_client()

MAX_RESEARCH_RETRIES = 2
MAX_SUMMARY_RETRIES = 2


class PipelineState(TypedDict, total=False):
    thread_id: str
    topic: str
    instruction: str
    memory_context: str

    research_draft: dict[str, Any] | None
    research_feedback: str
    research_retries: int
    research_approved: bool

    summary_draft: dict[str, Any] | None
    summary_feedback: str
    summary_retries: int
    summary_approved: bool

    human_decision: str | None
    persisted_issue_id: str | None
    status: str


# Wraps a node's work in one Langfuse span, scoped to the pipeline's thread so retries/resumes share a trace lineage.
@contextmanager
def _node_span(name: str, thread_id: str, **span_input: Any) -> Iterator[Any]:
    with propagate_attributes(session_id=f"agentic-pipeline-{thread_id}", tags=["agentic_pipeline", name]):
        with langfuse.start_as_current_observation(as_type="span", name=name, input=span_input) as span:
            try:
                yield span
            except Exception as exc:
                span.update(level="ERROR", status_message=str(exc))
                raise


def discover_research_node(state: PipelineState) -> dict[str, Any]:
    with _node_span("discover_research", state["thread_id"], topic=state.get("topic", "")) as span:
        result = discover_and_research(
            topic=state.get("topic", ""),
            instruction=state.get("instruction", ""),
            memory_context=state.get("memory_context", ""),
            judge_feedback=state.get("research_feedback", ""),
        )
        span.update(output={"candidate": result.get("candidate"), "iterations": result.get("iterations")})
    return {"research_draft": result}


def judge_research_node(state: PipelineState) -> dict[str, Any]:
    draft = state["research_draft"] or {}
    with _node_span("judge_research", state["thread_id"]) as span:
        verdict = judge_research(draft.get("candidate") or {}, draft.get("research_content", ""), draft.get("events", []))
        span.update(output=verdict)
        span.score(name="research_quality", value=verdict["score"] / 10, data_type="NUMERIC", comment=verdict["feedback"])

    if verdict["approved"]:
        return {"research_approved": True, "research_feedback": ""}
    return {
        "research_approved": False,
        "research_feedback": verdict["feedback"],
        "research_retries": state.get("research_retries", 0) + 1,
    }


def route_after_judge_research(state: PipelineState) -> Literal["summarize_rank", "discover_research", "rejected"]:
    if state.get("research_approved"):
        return "summarize_rank"
    if state.get("research_retries", 0) < MAX_RESEARCH_RETRIES and state["research_draft"].get("candidate"):
        return "discover_research"
    return "rejected"


def summarize_rank_node(state: PipelineState) -> dict[str, Any]:
    draft = state["research_draft"] or {}
    with _node_span("summarize_rank", state["thread_id"]) as span:
        result = summarize_and_rank(
            candidate=draft.get("candidate") or {},
            research_content=draft.get("research_content", ""),
            events=draft.get("events", []),
            judge_feedback=state.get("summary_feedback", ""),
        )
        span.update(output={"overall_score": result.get("overall_score")})
    return {"summary_draft": result}


def judge_summary_node(state: PipelineState) -> dict[str, Any]:
    draft = state["research_draft"] or {}
    summary = state["summary_draft"] or {}
    with _node_span("judge_summary", state["thread_id"]) as span:
        verdict = judge_summary(
            candidate=draft.get("candidate") or {},
            research_content=draft.get("research_content", ""),
            summary=summary.get("summary", ""),
            dimension_scores=summary.get("dimension_scores", {}),
        )
        span.update(output=verdict)
        span.score(name="summary_quality", value=verdict["score"] / 10, data_type="NUMERIC", comment=verdict["feedback"])

    if verdict["approved"]:
        return {"summary_approved": True, "summary_feedback": ""}
    return {
        "summary_approved": False,
        "summary_feedback": verdict["feedback"],
        "summary_retries": state.get("summary_retries", 0) + 1,
    }


def route_after_judge_summary(state: PipelineState) -> Literal["human_review", "summarize_rank", "rejected"]:
    if state.get("summary_approved"):
        return "human_review"
    if state.get("summary_retries", 0) < MAX_SUMMARY_RETRIES:
        return "summarize_rank"
    return "rejected"


def human_review_node(state: PipelineState) -> dict[str, Any]:
    draft = state["research_draft"] or {}
    summary = state["summary_draft"] or {}
    decision = interrupt(
        {
            "candidate": draft.get("candidate"),
            "summary": summary.get("summary"),
            "dimension_scores": summary.get("dimension_scores"),
            "overall_score": summary.get("overall_score"),
        }
    )
    return {"human_decision": decision.get("decision")}


def route_after_human_review(state: PipelineState) -> Literal["persist", "rejected"]:
    return "persist" if state.get("human_decision") == "approve" else "rejected"


# Only node that writes to the database - runs after human approval.
def persist_node(state: PipelineState) -> dict[str, Any]:
    candidate = (state["research_draft"] or {}).get("candidate") or {}
    summary_draft = state["summary_draft"] or {}
    events = (state["research_draft"] or {}).get("events", [])

    with _node_span("persist", state["thread_id"], decision=candidate.get("decision")) as span:
        if candidate.get("decision") == "merge":
            issue_id = candidate["issue_id"]
            update_component(issue_id, "research", candidate.get("additional_info", ""))
        else:
            issue = create_issue(
                title=candidate.get("title", ""),
                summary=summary_draft.get("summary", ""),
                why=candidate.get("why", ""),
                tags=candidate.get("tags", []),
            )
            issue_id = issue["id"]
            update_component(issue_id, "research", candidate.get("research_dossier", ""))

        if events:
            save_events_to_db(issue_id, events)

        upsert_tracked_issue(issue_id, summary_draft.get("dimension_scores", {}), summary_draft.get("overall_score", 0.0))
        span.update(output={"issue_id": issue_id})

    return {"persisted_issue_id": issue_id, "status": "persisted"}


def rejected_node(state: PipelineState) -> dict[str, Any]:
    return {"status": "rejected"}


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("discover_research", discover_research_node)
    graph.add_node("judge_research", judge_research_node)
    graph.add_node("summarize_rank", summarize_rank_node)
    graph.add_node("judge_summary", judge_summary_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("persist", persist_node)
    graph.add_node("rejected", rejected_node)

    graph.add_edge(START, "discover_research")
    graph.add_edge("discover_research", "judge_research")
    graph.add_conditional_edges("judge_research", route_after_judge_research)
    graph.add_edge("summarize_rank", "judge_summary")
    graph.add_conditional_edges("judge_summary", route_after_judge_summary)
    graph.add_conditional_edges("human_review", route_after_human_review)
    graph.add_edge("persist", END)
    graph.add_edge("rejected", END)

    return graph.compile(checkpointer=InMemorySaver())


# Single process-wide instance so the in-memory checkpointer survives across requests.
pipeline_app = build_graph()


def start_pipeline(thread_id: str, topic: str = "", instruction: str = "", memory_context: str = "") -> dict[str, Any]:
    """Start a new run. Returns the state after it pauses at human_review (or ends rejected)."""
    config = {"configurable": {"thread_id": thread_id}}
    result = pipeline_app.invoke(
        {"thread_id": thread_id, "topic": topic, "instruction": instruction, "memory_context": memory_context},
        config=config,
    )
    return _summarize(thread_id, result, result.get("__interrupt__", ()))


def resume_pipeline(thread_id: str, decision: str, feedback: str = "") -> dict[str, Any]:
    """Resume a paused run with a human decision ('approve' | 'reject')."""
    config = {"configurable": {"thread_id": thread_id}}
    result = pipeline_app.invoke(Command(resume={"decision": decision, "feedback": feedback}), config=config)
    return _summarize(thread_id, result, result.get("__interrupt__", ()))


def get_pipeline_state(thread_id: str) -> dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = pipeline_app.get_state(config)
    return _summarize(thread_id, snapshot.values, snapshot.interrupts)


def _summarize(thread_id: str, state: dict[str, Any], interrupts: tuple[Any, ...] = ()) -> dict[str, Any]:
    pending = interrupts[0].value if interrupts else None
    return {
        "thread_id": thread_id,
        "status": state.get("status", "pending_review" if pending else "running"),
        "pending_review": pending,
        "persisted_issue_id": state.get("persisted_issue_id"),
    }

