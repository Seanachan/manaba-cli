"""A course's task lists: ``course_{id}_query`` (quizzes and drills), ``_report``, ``_survey``."""

import logging
import re

from manaba_cli.errors import ParseError
from manaba_cli.models import Page, Task, TaskKind
from manaba_cli.parsers.dom import Node, inline_text, parse_html, text_lines
from manaba_cli.parsers.status import parse_submission_status, parse_task_status
from manaba_cli.timeutil import parse_datetime

# The query list holds both 小テスト (query) and ドリル (drill) items.
TASK_LIST_PAGES = ("query", "report", "survey")

_TASK_HREF = re.compile(r"course_(\d+)_(query|drill|report|survey)_(\d+)")

log = logging.getLogger(__name__)


def task_list_ref(course_id: int, list_page: str) -> str:
    return f"course_{course_id}_{list_page}"


def parse_task_list(page: Page) -> list[Task]:
    root = parse_html(page.html)
    table = root.css_first("table.stdlist")
    if table is None:
        if root.css_first("div.pagebody") is None:
            raise ParseError("This is not a manaba course page.")
        return []  # manaba shows "No ... is defined in this course" instead of a table.
    return [task for row in table.css("tr") if (task := _parse_row(row, page)) is not None]


def _parse_row(row: Node, page: Page) -> Task | None:
    link = row.css_first("h3 a[href]")
    if link is None:
        return None  # header row
    href = link.attributes["href"] or ""
    match = _TASK_HREF.search(href)
    cells = row.css("td")
    if match is None or len(cells) < 4:
        log.warning("Skipping unrecognised task row %r on %s", href, page.url)
        return None

    status_cell, start_cell, end_cell = cells[-3:]
    status_lines = text_lines(status_cell)
    return Task(
        course_id=int(match[1]),
        course_name=None,
        kind=TaskKind(match[2]),
        id=int(match[3]),
        title=inline_text(link),
        status=parse_task_status(status_lines[0]) if status_lines else None,
        my_status=parse_submission_status(status_lines[1:]),
        status_raw=" / ".join(status_lines),
        start=parse_datetime(inline_text(start_cell)),
        deadline=parse_datetime(inline_text(end_cell)),
        url=page.absolute(href),
    )
