from datetime import datetime

import pytest

from manaba_cli.errors import ParseError
from manaba_cli.models import Attachment, Content, ContentPage, Link, Page
from manaba_cli.parsers.contents import (
    parse_content_page,
    parse_content_page_urls,
    parse_contents_list,
)
from manaba_cli.timeutil import JST
from tests.support import BASE, fixture

FOLDER_URL = f"{BASE}/ct/page_5002c1001"
PAGE_URL = f"{BASE}/ct/page_5002c1001_6001"


def test_parses_contents_list() -> None:
    page = Page(url=f"{BASE}/ct/course_1001_page", html=fixture("course_page.html"))

    assert parse_contents_list(page) == [
        Content(
            id="5001c1001",
            title="Schedule",
            description=None,
            updated_at=datetime(2026, 9, 28, 22, 17, tzinfo=JST),
            url=f"{BASE}/ct/page_5001c1001",
        ),
        Content(
            id="5002c1001",
            title="Class records",
            description="Slides and notes",
            updated_at=datetime(2026, 10, 9, 16, 16, tzinfo=JST),
            url=FOLDER_URL,
        ),
    ]


def test_course_without_contents_gives_empty_list() -> None:
    page = Page(url=f"{BASE}/ct/course_1001_page", html="<div class='pagebody'></div>")

    assert parse_contents_list(page) == []


def test_parses_page_urls_of_a_folder() -> None:
    page = Page(url=FOLDER_URL, html=fixture("content_page.html"))

    assert parse_content_page_urls(page) == [
        f"{BASE}/ct/page_5002c1001_6001",
        f"{BASE}/ct/page_5002c1001_6002",
    ]


def test_parses_content_page() -> None:
    page = Page(url=PAGE_URL, html=fixture("content_page.html"))

    assert parse_content_page(page) == ContentPage(
        title="Orientation",
        author="Teacher　B",
        updated_at=datetime(2026, 10, 2, 11, 30, tzinfo=JST),
        publish_start=datetime(2026, 10, 1, 9, 0, tzinfo=JST),
        publish_end=datetime(2026, 12, 31, 23, 59, tzinfo=JST),
        url=PAGE_URL,
        text="How the class works\nEnter your test result in the shared sheet.\nDeadline: Oct 8",
        links=(Link(text="shared sheet", url="https://docs.example.com/sheet"),),
        attachments=(
            Attachment(
                name="transcript.docx",
                uploaded_at=datetime(2026, 4, 14, 13, 30, 13, tzinfo=JST),
                url=f"{BASE}/ct/page_5002c1001_6001_7001/transcript.docx?view=full",
            ),
        ),
    )


def test_content_page_without_title_is_a_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_content_page(Page(url=PAGE_URL, html="<div class='pagebody'></div>"))


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Teacher B - Version 1.2 (2026-10-02 11:30)", "Teacher B"),
        ("2026-10-02 11:30 - 先生 - 1.2版", "先生"),
        ("", None),
    ],
)
def test_author_line_in_both_languages(line: str, expected: str | None) -> None:
    html = f'<h1 class="pagetitle">Title</h1><div class="articleauthor">{line}</div>'

    assert parse_content_page(Page(url=PAGE_URL, html=html)).author == expected
