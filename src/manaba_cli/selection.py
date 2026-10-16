"""Which records a listing shows, and in what order."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from manaba_cli.models import NewsItem, SubmissionStatus, Task, TaskStatus

_DONE = frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.PASSED})
_UNDATED = datetime.min.replace(tzinfo=UTC)


def is_pending(task: Task) -> bool:
    """Not closed and not done yet. Unknown statuses count as pending, to be safe."""
    return task.status is not TaskStatus.CLOSED and task.my_status not in _DONE


def select_tasks(
    tasks: Iterable[Task],
    *,
    include_done: bool,
    within_days: int | None,
    now: datetime,
) -> list[Task]:
    """Pending tasks (or all), optionally only those due within ``within_days``, soonest first."""
    selected = [task for task in tasks if include_done or is_pending(task)]
    if within_days is not None:
        horizon = now + timedelta(days=within_days)
        selected = [task for task in selected if task.deadline and task.deadline <= horizon]
    return sorted(selected, key=_by_deadline)


def select_news(
    items: Iterable[NewsItem], *, since: datetime | None, limit: int | None
) -> list[NewsItem]:
    """Newest first, optionally only items posted at or after ``since``, at most ``limit``."""
    selected = [item for item in items if since is None or (item.posted_at or _UNDATED) >= since]
    selected.sort(key=lambda item: item.posted_at or _UNDATED, reverse=True)
    return selected if limit is None else selected[:limit]


def _by_deadline(task: Task) -> tuple[bool, float, int, int]:
    """Soonest deadline first; tasks without a deadline last; ties broken by course and id."""
    deadline = task.deadline.timestamp() if task.deadline else 0.0
    return (task.deadline is None, deadline, task.course_id, task.id)
