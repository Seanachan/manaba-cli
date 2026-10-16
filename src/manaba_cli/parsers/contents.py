"""Course contents (コンテンツ).

``course_{id}_page`` lists content folders; a folder ``page_{content}`` lists its pages
(``page_{content}_{page}``) and each page has a title, author line, optional publish
window, text and attachments.
"""

import re
from datetime import datetime

from manaba_cli.errors import ParseError
from manaba_cli.models import Content, ContentPage, Page
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

_CONTENT_HREF = re.compile(r"^page_(\w+)$")
_VERSION = re.compile(r"Version\s*[\d.]+|[\d.]+\s*版", re.IGNORECASE)
_WINDOW_SEPARATOR = re.compile(r"[～~]")


def contents_list_ref(course_id: int) -> str:
    return f"course_{course_id}_page"


def parse_contents_list(page: Page) -> list[Content]:
    root = parse_html(page.html)
    table = root.css_first("table.contentslist")
    if table is None:
        if root.css_first("div.pagebody") is None:
            raise ParseError("This is not a manaba course page.")
        return []  # no contents in this course
    return [content for row in table.css("tr") if (content := _parse_row(row, page))]


def parse_content_page_urls(page: Page) -> list[str]:
    """URLs of the pages in a content folder, in the folder's order."""
    page_list = require(parse_html(page.html), "ul.contentslist", "content page list")
    return [page.absolute(link.attributes["href"] or "") for link in page_list.css("li a[href]")]


def parse_content_page(page: Page) -> ContentPage:
    root = parse_html(page.html)
    attachments = extract_attachments(root, page)
    author_line = inline_text(root.css_first("div.articleauthor"))
    publish_start, publish_end = _publish_window(inline_text(root.css_first("div.pagelimitview")))
    # A page outside its publish window is shown without its article text.
    article = root.css_first("div.articletext")
    return ContentPage(
        title=inline_text(require(root, "h1.pagetitle", "content page title")),
        author=_author_name(author_line),
        updated_at=parse_datetime(author_line),
        publish_start=publish_start,
        publish_end=publish_end,
        url=page.url,
        text=block_text(article),
        links=parse_links(article, page),
        attachments=attachments,
    )


def _parse_row(row: Node, page: Page) -> Content | None:
    about = row.css_first("td.about-contents")
    link = about.css_first("a[href]") if about else None
    match = _CONTENT_HREF.match(link.attributes["href"] or "") if link else None
    if about is None or link is None or match is None:
        return None
    return Content(
        id=match[1],
        title=inline_text(link),
        description=inline_text(about.css_first("span")) or None,
        updated_at=parse_datetime(inline_text(row.css_first("td.info-contents"))),
        url=page.absolute(link.attributes["href"] or ""),
    )


def _author_name(author_line: str) -> str | None:
    """Name from "<name> - Version 1.2 (date)" (English) or "<date> - <name> - 1.2版" (Japanese)."""
    for part in author_line.split(" - "):
        part = part.strip()
        if part and not _VERSION.search(part) and parse_datetime(part) is None:
            return part
    return None


def _publish_window(text: str) -> tuple[datetime | None, datetime | None]:
    """(start, end) of "<start> ～ <end>"; either side may be missing."""
    parts = _WINDOW_SEPARATOR.split(text, maxsplit=1)
    if len(parts) == 1:
        return parse_datetime(text), None
    return parse_datetime(parts[0]), parse_datetime(parts[1])
