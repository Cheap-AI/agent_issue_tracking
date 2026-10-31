import os
import unittest
from unittest.mock import MagicMock, patch

from backend.core import llm
from backend.services import exa_service


class ExaServiceTests(unittest.TestCase):
    def test_not_configured_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(exa_service.is_configured())
            with self.assertRaises(RuntimeError):
                exa_service.search("anything")

    def test_search_maps_results_to_tavily_shape(self):
        fake = MagicMock()
        fake.json.return_value = {
            "results": [{"title": "T", "url": "https://x.test", "highlights": ["part one", "part two"], "publishedDate": "2026-01-01"}]
        }
        with patch.dict(os.environ, {"EXA_API_KEY": "k"}), patch.object(exa_service.requests, "post", return_value=fake) as post:
            results = exa_service.search("q", max_results=3)
        self.assertEqual(
            results, [{"title": "T", "url": "https://x.test", "content": "part one\npart two", "published_date": "2026-01-01"}]
        )
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["numResults"], 3)
        self.assertEqual(body["contents"], {"highlights": True})
        self.assertEqual(post.call_args.kwargs["headers"]["x-api-key"], "k")


class BulkModelTests(unittest.TestCase):
    def test_openai_fallback_without_gemini_key(self):
        llm.get_openai_client.cache_clear()
        with patch.dict(os.environ, {"OPENAI_JUDGE_MODEL": "gpt-x", "OPENAI_API_KEY": "dummy"}, clear=True):
            self.assertFalse(llm.use_gemini())
            self.assertEqual(llm.bulk_model("OPENAI_JUDGE_MODEL", "gpt-4o-mini"), "gpt-x")
            self.assertIs(llm.get_bulk_client(), llm.get_openai_client())

    def test_gemini_model_when_key_set(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k"}, clear=True):
            self.assertEqual(llm.bulk_model("OPENAI_JUDGE_MODEL", "gpt-4o-mini"), llm.GEMINI_DEFAULT_MODEL)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GEMINI_MODEL": "gemini-x"}, clear=True):
            self.assertEqual(llm.bulk_model("OPENAI_JUDGE_MODEL", "gpt-4o-mini"), "gemini-x")


if __name__ == "__main__":
    unittest.main()
