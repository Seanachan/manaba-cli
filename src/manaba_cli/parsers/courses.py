"""My courses list: ``/ct/home_course`` in List view."""

import re

from manaba_cli.errors import ParseError
from manaba_cli.models import Course, CourseFlags, Page
from manaba_cli.parsers.dom import Node, inline_text, parse_html, require

COURSE_LIST_PAGE = "home_course"

_COURSE_HREF = re.compile(r"^course_(\d+)$")

# Each flag is an <img> whose file name contains the key and ends in on/off.
_FLAG_ICONS = {
    "unread_news": "coursenews",
    "unsubmitted_tasks": "coursedeadline",
    "new_grades": "coursegrad",
    "unread_threads": "coursethread",
    "individual_messages": "individual",
}


def parse_courses(page: Page) -> list[Course]:
    root = parse_html(page.html)
    if root.css_first("div.mycourses-body") is None:
        raise ParseError("This is not the My Courses page.")
    table = root.css_first("div.mycourses-body table.courselist")
    if table is None:
        raise ParseError(
            "Course list table not found. manaba-cli reads the List view: switch "
            "My Courses to 'List' once in the browser."
        )
    return [_parse_row(row, page) for row in table.css("tr.courselist-c, tr.courselist-r")]


def _parse_row(row: Node, page: Page) -> Course:
    link = require(row, "span.courselist-title a[href]", "course link")
    href = link.attributes["href"] or ""
    match = _COURSE_HREF.match(href)
    if match is None:
        raise ParseError(f"Unexpected course link {href!r}.")
    cells = row.css("td")
    return Course(
        id=int(match[1]),
        name=link.attributes.get("title") or inline_text(link),
        year=_int_or_none(_cell_text(cells, 1)),
        period=_cell_text(cells, 2) or None,
        teacher=_cell_text(cells, 3) or None,
        url=page.absolute(href),
        flags=_parse_flags(row),
    )


def _parse_flags(row: Node) -> CourseFlags:
    lit = {
        flag
        for img in row.css("div.course-card-status img[src]")
        for flag, icon in _FLAG_ICONS.items()
        if icon in (src := img.attributes["src"] or "") and src.endswith("on.png")
    }
    return CourseFlags(**{flag: flag in lit for flag in _FLAG_ICONS})


def _cell_text(cells: list[Node], index: int) -> str:
    return inline_text(cells[index]) if index < len(cells) else ""


def _int_or_none(text: str) -> int | None:
    return int(text) if text.isdigit() else None
