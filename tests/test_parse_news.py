from datetime import datetime

import pytest

from manaba_cli.errors import ParseError
from manaba_cli.models import Attachment, NewsArticle, NewsItem, Page
from manaba_cli.parsers.news import parse_news_article, parse_news_list
from manaba_cli.timeutil import JST
from tests.support import BASE, fixture


def test_parses_news_list_with_unread_flag() -> None:
    page = Page(
        url=f"{BASE}/ct/course_1001_news?start=1&pagelen=100", html=fixture("course_news.html")
    )

    items = parse_news_list(page)

    assert items == [
        NewsItem(
            course_id=1001,
            course_name=None,
            id=3001,
            title="Homework and listening task",
            author="Teacher　A",
            posted_at=datetime(2026, 10, 16, tzinfo=JST),
            unread=True,
            url=f"{BASE}/ct/course_1001_news_3001",
        ),
        NewsItem(
            course_id=1001,
            course_name=None,
            id=3002,
            title="Dropping the course",
            author="Teacher　A",
            posted_at=datetime(2026, 10, 9, tzinfo=JST),
            unread=False,
            url=f"{BASE}/ct/course_1001_news_3002",
        ),
    ]


def test_course_without_news_gives_empty_list() -> None:
    page = Page(url=f"{BASE}/ct/course_1001_news", html="<div class='pagebody'>No news</div>")

    assert parse_news_list(page) == []


def test_parses_news_article() -> None:
    page = Page(url=f"{BASE}/ct/course_1001_news_3002", html=fixture("course_news_article.html"))

    assert parse_news_article(page) == NewsArticle(
        course_id=1001,
        course_name="Sample Speaking",
        id=3002,
        title="Dropping the course",
        author="Teacher　A",
        posted_at=datetime(2026, 10, 9, tzinfo=JST),
        url=f"{BASE}/ct/course_1001_news_3002",
        body="If you drop this course, remove it from manaba yourself.\n\nDetails:\nReport page",
        attachments=(
            Attachment(
                name="handout.pdf",
                uploaded_at=datetime(2026, 10, 8, 17, 23, tzinfo=JST),
                url=f"{BASE}/ct/course_1001_news_3002_5001/handout.pdf?view=full",
            ),
        ),
    )


def test_article_parser_rejects_other_pages() -> None:
    with pytest.raises(ParseError):
        parse_news_article(Page(url=f"{BASE}/ct/course_1001_report_1", html="<html></html>"))
