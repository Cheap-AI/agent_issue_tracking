import unittest

from fastapi.testclient import TestClient

import api.index as api_module
from api.index import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        api_module.issues_db.clear()
        api_module.issues_db.extend(
            [
                {
                    "id": 1,
                    "title": "Seed issue",
                    "summary": "A starter issue for testing.",
                }
            ]
        )
        self.client = TestClient(app)

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
