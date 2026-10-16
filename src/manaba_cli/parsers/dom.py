"""Small helpers over selectolax shared by all parsers."""

import re

from selectolax.lexbor import LexborHTMLParser, LexborNode

from manaba_cli.errors import ParseError
from manaba_cli.models import Attachment, Link, Page
from manaba_cli.timeutil import parse_datetime

Node = LexborNode

# Collapses ASCII whitespace and NBSP but keeps U+3000, which Japanese titles use on purpose.
_SPACES = re.compile(r"[ \t\r\n\f\v\xa0]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_BLOCK_BOUNDARY = "\x00"
# Like browsers, a <br> right before a block boundary adds no extra line.
_BLOCK_BOUNDARIES = re.compile(r" *\n? *\x00[\x00 ]*")
_SKIPPED_TAGS = frozenset({"script", "style", "noscript", "template", "-comment"})
_FORM_FIELD_TAGS = frozenset({"input", "select", "textarea"})
_VALUE_INPUT_TYPES = frozenset({"text", "number", "email", "url", "tel", "search"})
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


def parse_links(node: Node | None, page: Page) -> tuple[Link, ...]:
    """Distinct hyperlinks inside ``node`` in document order, without in-page/script links."""
    if node is None:
        return ()
    links: dict[str, Link] = {}
    for anchor in node.css("a[href]"):
        href = (anchor.attributes["href"] or "").strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        url = page.absolute(href)
        links.setdefault(url, Link(text=inline_text(anchor) or url, url=url))
    return tuple(links.values())


def extract_attachments(root: LexborHTMLParser | Node, page: Page) -> tuple[Attachment, ...]:
    """Parse inline attachments (``<file name> - <uploaded at>``) and remove them from the tree.

    Call it before reading the article text or links, so those do not repeat the files.
    """
    attachments = []
    for box in root.css("div.inlineattachment"):
        link = box.css_first("div.inlineaf-description a[href]")
        if link is not None:
            attachments.append(_attachment(link, page))
        box.decompose()
    return tuple(attachments)


def _attachment(link: Node, page: Page) -> Attachment:
    label = inline_text(link)
    match = _ATTACHMENT_LABEL.match(label)
    return Attachment(
        name=match["name"] if match else label,
        uploaded_at=parse_datetime(match["when"]) if match else None,
        url=page.absolute(link.attributes["href"] or ""),
    )


def _collect_text(node: Node, parts: list[str]) -> None:
    for child in node.iter(include_text=True):
        tag = child.tag
        if tag == "-text":
            parts.append(_SPACES.sub(" ", child.text(deep=False)))
        elif tag == "br":
            parts.append("\n")
        elif tag in _SKIPPED_TAGS:
            continue
        elif tag in _FORM_FIELD_TAGS:
            parts.append(_form_field_text(child))
        elif tag in _BLOCK_TAGS:
            parts.append(_BLOCK_BOUNDARY)
            _collect_text(child, parts)
            parts.append(_BLOCK_BOUNDARY)
        else:
            _collect_text(child, parts)


def _form_field_text(field: Node) -> str:
    """Quiz results show answers in form fields: ``(x)``/``( )`` for choices, ``[value]``."""
    if field.tag == "select":
        return f"[{inline_text(field.css_first('option[selected]'))}]"
    if field.tag == "textarea":
        return f"[{field.text()}]"
    input_type = (field.attributes.get("type") or "text").lower()
    if input_type in ("radio", "checkbox"):
        return "(x) " if "checked" in field.attributes else "( ) "
    if input_type in _VALUE_INPUT_TYPES:
        return f"[{field.attributes.get('value') or ''}]"
    return ""  # hidden fields and buttons carry no readable content
