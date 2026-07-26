import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("documents.db")


def init_db(db_path: str | Path = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_document(title: str, content: str, db_path: str | Path = DB_PATH) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO documents (title, content) VALUES (?, ?)",
            (title, content),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def list_documents(db_path: str | Path = DB_PATH) -> list[dict[str, object]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, content FROM documents ORDER BY id"
        ).fetchall()
        return [{"id": row[0], "title": row[1], "content": row[2]} for row in rows]
    finally:
        conn.close()


def search_documents(query: str, db_path: str | Path = DB_PATH) -> list[dict[str, object]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, content FROM documents WHERE lower(title) LIKE ? OR lower(content) LIKE ? ORDER BY id",
            (f"%{query.lower()}%", f"%{query.lower()}%"),
        ).fetchall()
        return [{"id": row[0], "title": row[1], "content": row[2]} for row in rows]
    finally:
        conn.close()
