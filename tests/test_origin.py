"""Pure-logic tests for origin estimation (no database, no LLM)."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from backend.services import origin
from backend.services.origin import earliest_event_year, validate_origin

pytestmark = pytest.mark.no_db


def test_unknown_is_a_valid_answer():
    out = validate_origin({"origin_year": None, "origin_precision": "unknown", "origin_confidence": "high", "origin_basis": "no evidence"})
    assert out["origin_year"] is None and out["origin_precision"] == "unknown"
    assert out["origin_confidence"] == "low"
    assert out["origin_basis"] == "no evidence"


def test_bad_enums_and_garbage_fall_back_to_unknown():
    assert validate_origin({"origin_year": 1990, "origin_precision": "sometime"})["origin_precision"] == "unknown"
    assert validate_origin({"origin_year": "abc", "origin_precision": "year"})["origin_year"] is None
    assert validate_origin(None)["origin_precision"] == "unknown"


def test_year_outside_sane_range_is_rejected():
    assert validate_origin({"origin_year": date.today().year + 5, "origin_precision": "year"})["origin_year"] is None
    assert validate_origin({"origin_year": -99999, "origin_precision": "era"})["origin_year"] is None


def test_year_is_rounded_down_to_precision_and_bad_confidence_becomes_low():
    dec = validate_origin({"origin_year": 1947, "origin_precision": "decade", "origin_confidence": "medium"})
    assert dec["origin_year"] == 1940 and dec["origin_confidence"] == "medium"
    cen = validate_origin({"origin_year": 1873, "origin_precision": "century", "origin_confidence": "??"})
    assert cen["origin_year"] == 1800 and cen["origin_confidence"] == "low"
    assert validate_origin({"origin_year": -44, "origin_precision": "century"})["origin_year"] == -100


def test_estimate_later_than_earliest_event_is_moved_back_and_confidence_capped():
    out = validate_origin(
        {"origin_year": 2020, "origin_precision": "year", "origin_confidence": "high", "origin_basis": "news"},
        earliest_event=2015,
    )
    assert out["origin_year"] == 2015
    assert out["origin_confidence"] == "medium"
    assert "earliest recorded event" in out["origin_basis"]


def test_estimate_earlier_than_earliest_event_is_kept():
    out = validate_origin({"origin_year": 1948, "origin_precision": "year", "origin_confidence": "high"}, earliest_event=2015)
    assert out["origin_year"] == 1948 and out["origin_confidence"] == "high"


def test_earliest_event_year_reads_db_and_draft_shapes():
    events = [{"event_date": "2019-03-01"}, {"date": "2012-01-05"}, {"event_date": None}, {"date": "unknown"}]
    assert earliest_event_year(events) == 2012
    assert earliest_event_year([]) is None and earliest_event_year(None) is None


def test_estimate_origin_returns_none_when_llm_fails_so_columns_stay_null():
    with patch.object(origin, "get_bulk_client", side_effect=RuntimeError("no key")):
        assert origin.estimate_origin("t", "s") is None


def test_estimate_origin_validates_model_output():
    reply = MagicMock()
    reply.choices = [MagicMock(message=MagicMock(content='{"origin_year": 2024, "origin_precision": "year", "origin_confidence": "high", "origin_basis": "x"}'))]
    client = MagicMock()
    client.chat.completions.create.return_value = reply
    with patch.object(origin, "get_bulk_client", return_value=client):
        out = origin.estimate_origin("t", "s", events=[{"event_date": "2021-06-01"}])
    assert out["origin_year"] == 2021
