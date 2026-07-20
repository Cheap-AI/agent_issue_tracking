import os
import sqlite3
from typing import Any

DB_PATH = os.environ.get("ISSUE_DB_PATH", "issues.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                summary TEXT NOT NULL
            )
            """
        )
        conn.commit()


def list_issues() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, title, summary FROM issues ORDER BY id").fetchall()
        return [dict(row) for row in rows]


def create_issue(title: str, summary: str) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO issues (title, summary) VALUES (?, ?)",
            (title.strip(), summary.strip()),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "title": title.strip(), "summary": summary.strip()}
