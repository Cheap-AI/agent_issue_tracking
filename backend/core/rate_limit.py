"""Per-user rate limiting as a FastAPI dependency.

Usage on a route (stack several for burst + daily caps):

    @router.post("/api/discovery", dependencies=[Depends(rate_limit("discovery", 5, 3600))])

Algorithm: sliding-window log. For each (limit name, user id) we keep the timestamps of recent
requests; a request is allowed if fewer than `limit` of them fall inside the last `window` seconds.
This is exact (no fixed-window edge bursts) and cheap for the small limits used here.

Limits are tracked in process memory, so they reset on restart and are per server instance. That is
fine for a single Render instance; with several instances (or to survive restarts) swap `_limiter`
for a Redis-backed implementation with the same `check()` signature.
"""
import math
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Hashable

from fastapi import Depends, HTTPException, status

from backend.core.auth import CurrentUser, get_current_user


class SlidingWindowLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[Hashable, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()  # sync endpoints run in a threadpool

    def check(self, key: Hashable, limit: int, window_seconds: float) -> float:
        """Record a hit and return 0.0 if allowed, else the seconds until the next slot frees up."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return hits[0] + window_seconds - now
            hits.append(now)
            return 0.0


_limiter = SlidingWindowLimiter()


def _describe(window_seconds: int) -> str:
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if window_seconds % size == 0:
            count = window_seconds // size
            return unit if count == 1 else f"{count} {unit}s"
    return f"{window_seconds} seconds"


def rate_limit(name: str, limit: int, window_seconds: int):
    """Dependency factory: allow `limit` requests per user per `window_seconds` for the bucket `name`.

    Also enforces login (it depends on get_current_user, which FastAPI evaluates once per request).
    Over the limit -> 429 with a Retry-After header.
    """
    def _dependency(user: CurrentUser = Depends(get_current_user)) -> None:
        retry_after = _limiter.check((name, user.id), limit, window_seconds)
        if retry_after > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} per {_describe(window_seconds)}. Try again later.",
                headers={"Retry-After": str(math.ceil(retry_after))},
            )

    return _dependency
