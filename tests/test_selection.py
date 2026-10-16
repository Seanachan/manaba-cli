from datetime import datetime

from manaba_cli.models import SubmissionStatus, Task, TaskKind, TaskStatus
from manaba_cli.selection import is_pending, select_tasks
from manaba_cli.timeutil import JST

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=JST)


def _task(
    task_id: int,
    *,
    status: TaskStatus | None = TaskStatus.OPEN,
    my_status: SubmissionStatus | None = SubmissionStatus.UNSUBMITTED,
    deadline: datetime | None = None,
) -> Task:
    return Task(
        course_id=1,
        course_name="Course",
        kind=TaskKind.REPORT,
        id=task_id,
        title=f"task {task_id}",
        status=status,
        my_status=my_status,
        status_raw="",
        start=None,
        deadline=deadline,
        url=f"https://manaba.example.ac.jp/ct/course_1_report_{task_id}",
    )


def test_pending_means_open_and_not_done() -> None:
    assert is_pending(_task(1))
    assert is_pending(_task(2, my_status=SubmissionStatus.UNPASSED))
    assert is_pending(_task(3, status=TaskStatus.UPCOMING, my_status=None))
    assert not is_pending(_task(4, my_status=SubmissionStatus.SUBMITTED))
    assert not is_pending(_task(5, my_status=SubmissionStatus.PASSED))
    assert not is_pending(_task(6, status=TaskStatus.CLOSED))


def test_unknown_status_counts_as_pending() -> None:
    assert is_pending(_task(1, status=None, my_status=None))


def test_select_sorts_by_deadline_with_undated_last() -> None:
    tasks = [
        _task(1),
        _task(2, deadline=datetime(2026, 10, 20, tzinfo=JST)),
        _task(3, deadline=datetime(2026, 10, 18, tzinfo=JST)),
        _task(4, my_status=SubmissionStatus.SUBMITTED, deadline=datetime(2026, 10, 17, tzinfo=JST)),
    ]

    pending = select_tasks(tasks, include_done=False, within_days=None, now=NOW)
    everything = select_tasks(tasks, include_done=True, within_days=None, now=NOW)

    assert [t.id for t in pending] == [3, 2, 1]
    assert [t.id for t in everything] == [4, 3, 2, 1]


def test_within_days_keeps_only_dated_tasks_inside_the_window() -> None:
    tasks = [
        _task(1),
        _task(2, deadline=datetime(2026, 10, 18, tzinfo=JST)),
        _task(3, deadline=datetime(2026, 10, 30, tzinfo=JST)),
    ]

    selected = select_tasks(tasks, include_done=False, within_days=3, now=NOW)

    assert [t.id for t in selected] == [2]
