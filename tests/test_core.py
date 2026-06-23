from agent_trend_analysis.core import trend_mean


def test_trend_mean_basic():
    assert trend_mean([1, 2, 3]) == 2.0


def test_trend_mean_empty():
    import pytest

    with pytest.raises(ValueError):
        trend_mean([])
