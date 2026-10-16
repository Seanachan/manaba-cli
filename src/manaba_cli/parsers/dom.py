"""Small helpers over selectolax shared by all parsers."""

import re
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser, LexborNode

from manaba_cli.errors import ParseError
from manaba_cli.models import Attachment
from manaba_cli.timeutil import parse_datetime
from manaba_cli.urls import CT_PREFIX

Node = LexborNode

# Collapses ASCII whitespace and NBSP but keeps U+3000, which Japanese titles use on purpose.
_SPACES = re.compile(r"[ \t\r\n\f\v\xa0]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_BLOCK_BOUNDARY = "\x00"
_BLOCK_BOUNDARIES = re.compile(r" *\x00[\x00 ]*")
_SKIPPED_TAGS = frozenset({"script", "style", "noscript", "template", "-comment"})
_BLOCK_TAGS = frozenset(
    {"address", "article", "blockquote", "dd", "div", "dl", "dt", "h1", "h2", "h3", "h4", "h5",
     "h6", "hr", "li", "ol", "p", "pre", "section", "table", "tr", "ul"}
)  # fmt: skip
_ATTACHMENT_LABEL = re.compile(r"^(?P<name>.*?)\s+-\s+(?P<when>\d{4}-\d{2}-\d{2}\s+[\d:]+)\s*$")


def parse_html(html: str) -> LexborHTMLParser:
    return LexborHTMLParser(html)


def inline_text(node: Node | None) -> str:
    """Text of ``node`` on one line with runs of whitespace collapsed."""
    if node is None:
        return ""
    return _SPACES.sub(" ", node.text(separator=" ")).strip()


def block_text(node: Node | None) -> str:
    """Readable multi-line text: a line per block element, <br> kept, scripts dropped.

    HTML source newlines are plain whitespace; only <br> and block boundaries break lines.
    Consecutive block boundaries collapse into one line break; at most one blank line remains.
    """
    if node is None:
        return ""
    parts: list[str] = []
    _collect_text(node, parts)
    text = _BLOCK_BOUNDARIES.sub("\n", "".join(parts))
    lines = (line.strip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def text_lines(node: Node | None) -> list[str]:
    """Non-empty lines of ``node``'s text, e.g. the stacked lines of a status cell."""
    return [line for line in block_text(node).split("\n") if line]


def require(root: LexborHTMLParser | Node, selector: str, what: str) -> Node:
    node = root.css_first(selector)
    if node is None:
        raise ParseError(f"Could not find {what} ({selector}).")
    return node


def absolute_url(base_url: str, href: str) -> str:
    return urljoin(base_url + CT_PREFIX, href)


def parse_attachments(root: LexborHTMLParser | Node, base_url: str) -> tuple[Attachment, ...]:
    """Inline attachments, labelled ``<file name> - <uploaded at>``."""
    attachments = []
    for link in root.css("div.inlineattachment div.inlineaf-description a[href]"):
        label = inline_text(link)
        match = _ATTACHMENT_LABEL.match(label)
        name = match["name"] if match else label
        uploaded_at = parse_datetime(match["when"]) if match else None
        url = absolute_url(base_url, link.attributes["href"] or "")
        attachments.append(Attachment(name=name, uploaded_at=uploaded_at, url=url))
    return tuple(attachments)


def _collect_text(node: Node, parts: list[str]) -> None:
    for child in node.iter(include_text=True):
        tag = child.tag
        if tag == "-text":
            parts.append(_SPACES.sub(" ", child.text(deep=False)))
        elif tag == "br":
            parts.append("\n")
        elif tag in _SKIPPED_TAGS:
            continue
        elif tag in _BLOCK_TAGS:
            parts.append(_BLOCK_BOUNDARY)
            _collect_text(child, parts)
            parts.append(_BLOCK_BOUNDARY)
        else:
            _collect_text(child, parts)
