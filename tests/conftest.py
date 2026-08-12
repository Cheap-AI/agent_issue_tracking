"""Shared pytest fixtures for DB-backed tests.

Tests run against a real Postgres database. Set TEST_DATABASE_URL (falls back to
DATABASE_URL) before running pytest, e.g.:

    $env:TEST_DATABASE_URL = "postgresql://postgres:...@db.xxx.supabase.co:5432/postgres"
    python -m pytest tests/

Each test gets a clean slate: tables are truncated and issue_id_seq is reset
before every test function.
"""
import os

from dotenv import load_dotenv

load_dotenv()

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")

import pytest
from sqlalchemy import text

from backend.core.db import Base, engine
from backend.models import db_models  # noqa: F401  (ensures models are registered on Base.metadata)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _reset_database():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE issues, components, global_docs RESTART IDENTITY CASCADE"))
        conn.execute(text("ALTER SEQUENCE issue_id_seq RESTART WITH 1"))
    yield
