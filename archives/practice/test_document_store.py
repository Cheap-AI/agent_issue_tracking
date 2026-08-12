import tempfile
import unittest
from pathlib import Path

from document_store import add_document, init_db, list_documents, search_documents


class DocumentStoreTests(unittest.TestCase):
    def test_init_db_and_store_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            init_db(db_path)
            doc_id = add_document("Test Doc", "hello world", db_path)
            docs = list_documents(db_path)

            self.assertEqual(doc_id, 1)
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0]["title"], "Test Doc")
            self.assertEqual(docs[0]["content"], "hello world")

    def test_search_documents_matches_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "search.db"
            init_db(db_path)
            add_document("Python Notes", "python is fun", db_path)
            add_document("API Guide", "fastapi helps build apis", db_path)

            results = search_documents("python", db_path)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Python Notes")


if __name__ == "__main__":
    unittest.main()
