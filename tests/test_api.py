import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.main as main_module
from backend.core.issue import create_issue


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["STORAGE_ROOT"] = str(Path(self.temp_dir.name) / "storage")
        create_issue("Seed issue", "A starter issue for testing.")
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_create_issue_and_list_it(self) -> None:
        response = self.client.post(
            "/api/issues",
            json={"title": "New issue", "summary": "A freshly created issue."},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["issue"]["title"], "New issue")
        self.assertEqual(payload["issue"]["summary"], "A freshly created issue.")

        list_response = self.client.get("/api/issues")
        self.assertEqual(list_response.status_code, 200)
        issues = list_response.json()["issues"]
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[-1]["title"], "New issue")

    def test_get_single_issue_not_found(self) -> None:
        response = self.client.get("/api/issues/iss-9999")
        self.assertEqual(response.status_code, 404)

    def test_research_endpoint_with_mocked_search_service(self) -> None:
        fake_results = [
            {"title": "Fake Title", "url": "https://example.com/a", "content": "Fake content A"},
        ]
        with patch.object(main_module.search_service, "is_configured", return_value=True), \
                patch.object(main_module.search_service, "search", return_value=fake_results):
            response = self.client.post("/api/agent/research", json={"topic": "mock topic"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["sources"], ["https://example.com/a"])

    def test_research_endpoint_not_configured(self) -> None:
        with patch.object(main_module.search_service, "is_configured", return_value=False):
            response = self.client.post("/api/agent/research", json={"topic": "no key topic"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
