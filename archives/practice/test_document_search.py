import tempfile
import unittest
from pathlib import Path

from document_search import load_text, find_matches


class DocumentSearchTests(unittest.TestCase):
    def test_load_text_reads_file_contents(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write("alpha beta\ngamma\n")
            path = Path(handle.name)

        try:
            self.assertEqual(load_text(path), "alpha beta\ngamma\n")
        finally:
            path.unlink(missing_ok=True)

    def test_find_matches_is_case_insensitive(self) -> None:
        text = "Python is great. python coding is fun."
        self.assertEqual(find_matches(text, ["python", "fun"]), ["python", "fun"])


if __name__ == "__main__":
    unittest.main()
