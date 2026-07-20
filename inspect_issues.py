import sqlite3
from pathlib import Path


def main() -> None:
    db_path = Path("issues.db")
    if not db_path.exists():
        print("No issues database found at issues.db")
        return

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, title, summary FROM issues ORDER BY id").fetchall()
    conn.close()

    if not rows:
        print("No issues found.")
        return

    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Summary: {row[2]}")
        print("-" * 40)


if __name__ == "__main__":
    main()
