"""What counts as "to do", and the order tasks are listed in."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from manaba_cli.models import SubmissionStatus, Task, TaskStatus

_DONE = frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.PASSED})


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


def _by_deadline(task: Task) -> tuple[bool, float, int, int]:
    """Soonest deadline first; tasks without a deadline last; ties broken by course and id."""
    deadline = task.deadline.timestamp() if task.deadline else 0.0
    return (task.deadline is None, deadline, task.course_id, task.id)
