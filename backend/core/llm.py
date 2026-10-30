"""Shared LLM helpers: one Langfuse-wrapped OpenAI client and prompt loading."""
import os
from functools import lru_cache
from pathlib import Path

from langfuse.openai import OpenAI


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Return the process-wide OpenAI client (traced by Langfuse)."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_prompt(path: Path, fallback: str) -> str:
    """Read a prompt file, or return the fallback text if it doesn't exist."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback
