import pytest

from manaba_cli.errors import ParseError
from manaba_cli.models import Course, CourseFlags, Page
from manaba_cli.parsers.courses import parse_courses
from tests.support import BASE, fixture


def _page(html: str) -> Page:
    return Page(url=f"{BASE}/ct/home_course", html=html)


def test_parses_courses_from_list_view() -> None:
    courses = parse_courses(_page(fixture("home_course.html")))

    assert courses == [
        Course(
            id=1001,
            name="Sample Grammar",
            year=2026,
            period="Autumn AB Tue. 3",
            teacher="Teacher A",
            url=f"{BASE}/ct/course_1001",
            flags=CourseFlags(
                unread_news=True,
                unsubmitted_tasks=True,
                new_grades=False,
                unread_threads=False,
                individual_messages=False,
            ),
        ),
        Course(
            id=1002,
            name="Orientation for Students",
            year=2024,
            period=None,
            teacher="Student Office",
            url=f"{BASE}/ct/course_1002",
            flags=CourseFlags(
                unread_news=False,
                unsubmitted_tasks=False,
                new_grades=True,
                unread_threads=True,
                individual_messages=True,
            ),
        ),
    ]


def test_thumbnail_view_asks_for_list_view() -> None:
    html = '<div class="mycourses-body"><div class="coursecard"></div></div>'

    with pytest.raises(ParseError, match="List"):
        parse_courses(_page(html))


def test_other_page_is_a_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_courses(_page("<html><body>login</body></html>"))
