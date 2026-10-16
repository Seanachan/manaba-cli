from datetime import datetime

import pytest

from manaba_cli.errors import ParseError
from manaba_cli.models import Page, SubmissionStatus, Task, TaskKind, TaskStatus
from manaba_cli.parsers.status import parse_submission_status, parse_task_status
from manaba_cli.parsers.tasks import parse_task_list
from manaba_cli.timeutil import JST
from tests.support import BASE, fixture


def _page(name: str) -> Page:
    return Page(url=f"{BASE}/ct/course_1001_query", html=fixture(name))


def test_parses_queries_and_drills() -> None:
    tasks = parse_task_list(_page("course_query.html"))

    assert tasks[0] == Task(
        course_id=1001,
        course_name=None,
        kind=TaskKind.QUERY,
        id=2001,
        title="【Unit 2　Writing】Particles",
        status=TaskStatus.OPEN,
        my_status=SubmissionStatus.SUBMITTED,
        status_raw="In progress / Submitted",
        start=datetime(2026, 10, 14, 0, 0, tzinfo=JST),
        deadline=datetime(2026, 10, 20, 12, 15, tzinfo=JST),
        url=f"{BASE}/ct/course_1001_query_2001",
    )
    assert [(t.kind, t.id, t.status, t.my_status) for t in tasks] == [
        (TaskKind.QUERY, 2001, TaskStatus.OPEN, SubmissionStatus.SUBMITTED),
        (TaskKind.DRILL, 2002, TaskStatus.OPEN, SubmissionStatus.UNSUBMITTED),
        (TaskKind.DRILL, 2003, TaskStatus.OPEN, SubmissionStatus.PASSED),
        (TaskKind.QUERY, 2004, TaskStatus.CLOSED, SubmissionStatus.SUBMITTED),
        (TaskKind.QUERY, 2005, TaskStatus.UPCOMING, None),
    ]


def test_missing_deadline_is_none() -> None:
    drill = parse_task_list(_page("course_query.html"))[1]

    assert drill.deadline is None
    assert drill.start == datetime(2026, 4, 1, tzinfo=JST)


def test_empty_list_page_gives_no_tasks() -> None:
    assert parse_task_list(_page("course_survey_empty.html")) == []


def test_non_course_page_is_a_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_task_list(Page(url=f"{BASE}/ct/home", html="<html><body></body></html>"))


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("In progress", TaskStatus.OPEN),
        ("受付中", TaskStatus.OPEN),
        ("Closed", TaskStatus.CLOSED),
        ("受付終了", TaskStatus.CLOSED),
        ("受付開始待ち", TaskStatus.UPCOMING),
        ("Something new", None),
    ],
)
def test_task_status_words(line: str, expected: TaskStatus | None) -> None:
    assert parse_task_status(line) is expected


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["Not submitted"], SubmissionStatus.UNSUBMITTED),
        (["未提出"], SubmissionStatus.UNSUBMITTED),
        (["まだ提出していません"], SubmissionStatus.UNSUBMITTED),
        (["Submitted", "(1 files)"], SubmissionStatus.SUBMITTED),
        (["提出済み"], SubmissionStatus.SUBMITTED),
        (["Submitted", "Passed"], SubmissionStatus.PASSED),
        (["合格済み"], SubmissionStatus.PASSED),
        (["未合格"], SubmissionStatus.UNPASSED),
        ([], None),
    ],
)
def test_submission_status_words(lines: list[str], expected: SubmissionStatus | None) -> None:
    assert parse_submission_status(lines) is expected
