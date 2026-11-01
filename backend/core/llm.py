"""Shared LLM helpers: Langfuse-wrapped OpenAI-compatible clients and prompt loading.

Two providers share the OpenAI SDK (so Langfuse tracing works for both):
- OpenAI: chat (streamed tool calls) and embeddings (pgvector dimensions depend on it).
- Gemini via Google's OpenAI-compatible endpoint: the "bulk" agents (discovery, research,
  judge, ranking, summarize_rank, events). Used when GEMINI_API_KEY is set, otherwise these
  agents fall back to OpenAI so nothing breaks without a Gemini key.
"""
import json
import os
from functools import lru_cache
from pathlib import Path

from langfuse.openai import OpenAI

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_DEFAULT_MODEL = "gemini-3.5-flash-lite"  # full Flash models think for ~1 min per call on the free tier


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Return the process-wide OpenAI client (traced by Langfuse)."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@lru_cache(maxsize=1)
def _get_gemini_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("GEMINI_API_KEY"), base_url=GEMINI_BASE_URL)


def use_gemini() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def get_bulk_client() -> OpenAI:
    """Client for the bulk (non-chat) agents: Gemini if configured, else OpenAI."""
    return _get_gemini_client() if use_gemini() else get_openai_client()


def bulk_model(openai_env_var: str, openai_default: str) -> str:
    """Model name for a bulk agent. With Gemini, GEMINI_MODEL applies to all of them;
    otherwise the agent's own OpenAI env var / default is used."""
    if use_gemini():
        return os.getenv("GEMINI_MODEL", GEMINI_DEFAULT_MODEL)
    return os.getenv(openai_env_var, openai_default)


def load_prompt(path: Path, fallback: str) -> str:
    """Read a prompt file, or return the fallback text if it doesn't exist."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


_TRUNCATED = "...[truncated]"


def _shorten(value, max_field_chars: int):
    if isinstance(value, str):
        return value if len(value) <= max_field_chars else value[:max_field_chars] + _TRUNCATED
    if isinstance(value, list):
        return [_shorten(v, max_field_chars) for v in value]
    if isinstance(value, dict):
        return {k: _shorten(v, max_field_chars) for k, v in value.items()}
    return value


def tool_message_content(result, max_field_chars: int = 700, max_total_chars: int = 12000) -> str:
    """Serialize a tool result for the model, bounding its size.

    Tool results are re-sent on every later model call, so large search snippets or reports
    multiply cost. Long string fields are cut to `max_field_chars`, and the whole JSON to
    `max_total_chars`. Only the model-facing copy is trimmed: spans and stored traces keep the full result.
    """
    text = json.dumps(_shorten(result, max_field_chars))
    if len(text) > max_total_chars:
        text = text[:max_total_chars] + _TRUNCATED
    return text
