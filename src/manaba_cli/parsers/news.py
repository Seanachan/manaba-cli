"""Course news (コースニュース): ``course_{id}_news`` list and ``course_{id}_news_{nid}`` pages."""

import re

from manaba_cli.errors import ParseError
from manaba_cli.models import NewsArticle, NewsItem, Page
from manaba_cli.parsers.dom import (
    Node,
    block_text,
    extract_attachments,
    inline_text,
    parse_html,
    parse_links,
    require,
)
from manaba_cli.timeutil import parse_datetime

# manaba offers 5-50 per page in its UI; one large page avoids paging through results.
NEWS_PAGE_LENGTH = 100

_NEWS_HREF = re.compile(r"course_(\d+)_news_(\d+)")


def news_list_ref(course_id: int) -> str:
    return f"course_{course_id}_news?start=1&pagelen={NEWS_PAGE_LENGTH}"


def news_article_ref(course_id: int, news_id: int) -> str:
    return f"course_{course_id}_news_{news_id}"


def parse_news_list(page: Page) -> list[NewsItem]:
    root = parse_html(page.html)
    table = root.css_first("table.stdlist")
    if table is None:
        if root.css_first("div.pagebody") is None:
            raise ParseError("This is not a manaba course page.")
        return []  # no news in this course
    return [item for row in table.css("tr") if (item := _parse_row(row, page)) is not None]


def parse_news_article(page: Page) -> NewsArticle:
    match = _NEWS_HREF.search(page.url)
    if match is None:
        raise ParseError(f"{page.url} is not a course news page.")
    root = parse_html(page.html)
    attachments = extract_attachments(root, page)
    body = root.css_first("div.msg-text")
    return NewsArticle(
        course_id=int(match[1]),
        course_name=inline_text(root.css_first("a#coursename")) or None,
        id=int(match[2]),
        title=inline_text(require(root, "h2.msg-subject", "news title")),
        author=_author(root.css_first("div.msg-info")),
        posted_at=parse_datetime(inline_text(root.css_first("span.msg-date"))),
        url=page.url,
        body=block_text(body),
        links=parse_links(body, page),
        attachments=attachments,
    )


def _parse_row(row: Node, page: Page) -> NewsItem | None:
    cells = row.css("td")
    link = cells[0].css_first("a[href]") if len(cells) >= 3 else None
    match = _NEWS_HREF.search(link.attributes["href"] or "") if link else None
    if link is None or match is None:
        return None  # header row
    return NewsItem(
        course_id=int(match[1]),
        course_name=None,
        id=int(match[2]),
        title=inline_text(link),
        author=inline_text(cells[1]) or None,
        posted_at=parse_datetime(inline_text(cells[2])),
        unread="unread" in (cells[0].attributes.get("class") or "").split(),
        url=page.absolute(link.attributes["href"] or ""),
    )


def _author(info: Node | None) -> str | None:
    """Poster's name: a profile link when present, else the text after the caption."""
    if info is None:
        return None
    profile_link = info.css_first('a[href="#"]')
    if profile_link is not None:
        return inline_text(profile_link) or None
    caption = inline_text(info.css_first("span.msg-info-caption"))
    return inline_text(info).removeprefix(caption).strip() or None
