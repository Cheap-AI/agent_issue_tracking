import os
import tempfile
import unittest
from pathlib import Path

from backend.core import knowledge
from backend.core.issue import create_issue, get_issue, list_issues


class IssueStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["STORAGE_ROOT"] = str(Path(self.temp_dir.name) / "storage")

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_create_issue_creates_folders_and_meta(self) -> None:
        issue = create_issue("Test issue", "A test summary.")
        self.assertTrue(issue["id"].startswith("iss-"))
        self.assertEqual(issue["title"], "Test issue")

        storage_root = Path(os.environ["STORAGE_ROOT"])
        issue_dir = storage_root / "issues" / issue["id"]
        self.assertTrue(issue_dir.is_dir())
        for component in ("research", "summary", "timeline", "sources", "questions"):
            self.assertTrue((issue_dir / component).is_dir())
        self.assertTrue((issue_dir / "meta.json").is_file())

    def test_list_and_get_issue(self) -> None:
        created = create_issue("Another issue", "Another summary.")

        issues = list_issues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], created["id"])

        fetched = get_issue(created["id"])
        self.assertEqual(fetched["title"], "Another issue")

        self.assertIsNone(get_issue("iss-9999"))

    def test_sequential_ids(self) -> None:
        first = create_issue("First", "s1")
        second = create_issue("Second", "s2")
        self.assertEqual(first["id"], "iss-0001")
        self.assertEqual(second["id"], "iss-0002")

    def test_versioning_save_and_read_current(self) -> None:
        issue = create_issue("Versioned issue", "s")

        v1 = knowledge.update_component(issue["id"], "research", "First research note.")
        self.assertEqual(v1, 1)

        v2 = knowledge.update_component(issue["id"], "research", "Second research note.")
        self.assertEqual(v2, 2)

        current = knowledge.read_current(issue["id"], "research")
        self.assertEqual(current, (2, "Second research note."))

        history = knowledge.read_history(issue["id"], "research")
        self.assertEqual(history, [1, 2])

    def test_versioning_unknown_component_rejected(self) -> None:
        issue = create_issue("Bad component issue", "s")
        with self.assertRaises(ValueError):
            knowledge.update_component(issue["id"], "not_a_component", "content")


if __name__ == "__main__":
    unittest.main()
