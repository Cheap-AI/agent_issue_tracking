import importlib
import os
import tempfile
import unittest
from pathlib import Path


class DatabasePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "issues.db"
        os.environ["ISSUE_DB_PATH"] = str(self.db_path)
        import api.database as database_module

        importlib.reload(database_module)
        self.database_module = database_module
        self.database_module.init_db()

    def tearDown(self) -> None:
        try:
            conn = self.database_module.get_connection()
            conn.close()
        except Exception:
            pass
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_create_and_list_issues_persist(self) -> None:
        created = self.database_module.create_issue("Seed", "Persisted issue")
        self.assertEqual(created["title"], "Seed")

        listed = self.database_module.list_issues()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["title"], "Seed")

        reloaded = importlib.reload(self.database_module)
        listed_again = reloaded.list_issues()
        self.assertEqual(len(listed_again), 1)
        self.assertEqual(listed_again[0]["summary"], "Persisted issue")
