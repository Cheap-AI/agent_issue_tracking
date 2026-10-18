"""In-memory background job tracking (single-process only, lost on restart).

Used by the chat agent's trigger_discovery tool so a long-running discover_issue()
call doesn't block the chat turn; a later turn can poll the job by id.
"""
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_job(target_fn: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> str:
    """Start target_fn in a daemon thread, return a job_id to poll via get_job()."""
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "running",
            "started_at": _utcnow_iso(),
            "finished_at": None,
            "result": None,
            "error": None,
        }

    def _run() -> None:
        try:
            result = target_fn(*args, **kwargs)
            with _LOCK:
                _JOBS[job_id].update(status="done", finished_at=_utcnow_iso(), result=result)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the polling caller
            with _LOCK:
                _JOBS[job_id].update(status="failed", finished_at=_utcnow_iso(), error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return the current status dict for a job, or None if job_id is unknown."""
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job is not None else None
