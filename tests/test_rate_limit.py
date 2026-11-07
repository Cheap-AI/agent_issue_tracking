"""Unit tests for backend/core/rate_limit.py (no DB or network needed)."""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rate_limit import SlidingWindowLimiter, rate_limit


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_limit_then_blocks():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(clock)
    assert [limiter.check("u", 3, 60) for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.check("u", 3, 60) == 60  # full window until the first hit expires


def test_window_slides_instead_of_resetting():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(clock)
    limiter.check("u", 2, 60)  # t=1000
    clock.now += 30
    limiter.check("u", 2, 60)  # t=1030
    clock.now += 31  # t=1061: first hit expired, second hasn't
    assert limiter.check("u", 2, 60) == 0.0
    assert limiter.check("u", 2, 60) > 0  # window now holds t=1030 and t=1061


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(FakeClock())
    assert limiter.check(("chat", "alice"), 1, 60) == 0.0
    assert limiter.check(("chat", "alice"), 1, 60) > 0
    assert limiter.check(("chat", "bob"), 1, 60) == 0.0
    assert limiter.check(("search", "alice"), 1, 60) == 0.0


def test_dependency_returns_429_with_retry_after():
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="u1", email=None, role="member")

    @app.get("/ping", dependencies=[Depends(rate_limit("test_ping", 2, 60))])
    def ping() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    blocked = client.get("/ping")
    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["Retry-After"]) <= 60
    assert "2 per minute" in blocked.json()["detail"]
