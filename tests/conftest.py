"""Shared pytest fixtures for DB-backed tests.

Tests run against a real Postgres database. There is only ONE database for this project
(no separate test instance) and no automatic truncation/reset anymore - a prior autouse
TRUNCATE fixture here wiped real production data. DB-backed tests are now opt-in only:

1. Set TEST_DATABASE_URL (falls back to DATABASE_URL) before running pytest, e.g.:

       $env:TEST_DATABASE_URL = "postgresql://postgres:...@aws-1-us-west-2.pooler.supabase.com:5432/postgres"

2. Set ALLOW_DB_TESTS=1 to acknowledge tests will read/write real data. Without it, every test
   in this suite is skipped - nothing touches the database by accident.

Tests must clean up any rows they create themselves (e.g. delete_issue in tearDown); there is
no global reset between tests.
"""
import os

from dotenv import load_dotenv

load_dotenv()

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")

import pytest
from sqlalchemy.engine import make_url

from backend.core.db import Base, engine
from backend.models import db_models  # noqa: F401  (ensures models are registered on Base.metadata)

ALLOW_DB_TESTS = os.environ.get("ALLOW_DB_TESTS") == "1"


def pytest_collection_modifyitems(config, items):
    if ALLOW_DB_TESTS:
        return
    skip_db = pytest.mark.skip(
        reason="DB-backed tests are skipped unless ALLOW_DB_TESTS=1 is set (guards the shared "
        "database from accidental writes - see tests/conftest.py)."
    )
    for item in items:
        item.add_marker(skip_db)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    if not ALLOW_DB_TESTS:
        yield
        return
    host = make_url(os.environ["DATABASE_URL"]).host
    print(f"\n[conftest] DB-backed tests enabled, targeting host: {host}")
    Base.metadata.create_all(engine)
    yield
