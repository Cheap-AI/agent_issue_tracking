"""Telemetry setup: Langfuse client + OpenTelemetry FastAPI instrumentation.

Langfuse v3+ is built on OpenTelemetry. By default it only exports LLM/Langfuse spans, so we
also allow the FastAPI instrumentation scope. HTTP request spans then become the parent of the
agent/LLM/tool spans in the same trace.

Must be imported (setup_langfuse) before any module calls langfuse.get_client().
"""
from fastapi import FastAPI
from langfuse import Langfuse
from langfuse.span_filter import is_default_export_span

HTTP_SCOPE_PREFIX = "opentelemetry.instrumentation.fastapi"
EXCLUDED_URLS = "^.*/$,health"  # root health check + any /health route


def _should_export(span) -> bool:
    scope = span.instrumentation_scope
    if scope is not None and scope.name.startswith(HTTP_SCOPE_PREFIX):
        return True
    return is_default_export_span(span)


def setup_langfuse() -> Langfuse:
    return Langfuse(should_export_span=_should_export)


def instrument_app(app: FastAPI) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    # Drop the per-ASGI-message "http send"/"http receive" spans: a streamed chat reply emits one
    # `send` per chunk, which floods the trace with hundreds of near-empty observations.
    FastAPIInstrumentor.instrument_app(app, excluded_urls=EXCLUDED_URLS, exclude_spans=["send", "receive"])
