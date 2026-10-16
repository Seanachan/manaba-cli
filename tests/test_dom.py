from datetime import datetime

import pytest

from manaba_cli.errors import ParseError
from manaba_cli.models import Attachment, Link, Page
from manaba_cli.parsers.dom import (
    block_text,
    extract_attachments,
    inline_text,
    parse_html,
    parse_links,
    require,
    text_lines,
)
from manaba_cli.timeutil import JST

BASE = "https://manaba.example.ac.jp"


def _node(html: str):
    return parse_html(html).css_first("div")


def test_inline_text_collapses_whitespace_but_keeps_ideographic_space() -> None:
    node = _node("<div>\n  【Unit 1　Review】&nbsp;語彙\n  <b>bold</b> </div>")

    assert inline_text(node) == "【Unit 1　Review】 語彙 bold"


def test_block_text_breaks_lines_at_br_and_blocks_and_drops_scripts() -> None:
    node = _node(
        "<div>first <b>bold</b>\n tail<br>second<p>para</p>"
        "<script>var x = 1;</script>\n  <ul>\n <li>a</li>\n <li>b</li></ul></div>"
    )

    assert block_text(node) == "first bold tail\nsecond\npara\na\nb"


def test_block_text_keeps_one_blank_line_from_consecutive_br() -> None:
    assert block_text(_node("<div>a<br><br><br><br>b</div>")) == "a\n\nb"


def test_block_text_ignores_br_at_the_end_of_a_block() -> None:
    assert block_text(_node("<div><p>line<br></p>next<br><div>block</div></div>")) == (
        "line\nnext\nblock"
    )


def test_block_text_shows_answers_held_in_form_fields() -> None:
    node = _node(
        "<div><ol>"
        '<li><input type="radio" disabled value="1">A</li>'
        '<li><input type="radio" disabled value="2" checked>B</li></ol>'
        'Fill: <input type="text" readonly value="に"> / '
        '<input type="text" value=""> <input type="hidden" value="secret">'
        "<select><option>x</option><option selected>y</option></select>"
        "<textarea>essay</textarea><input type='submit' value='Post'></div>"
    )

    assert block_text(node) == "( ) A\n(x) B\nFill: [に] / [] [y][essay]"


def test_text_lines_skips_blank_lines() -> None:
    node = _node("<div>\n In progress<br>\n <strong> Submitted </strong>\n</div>")

    assert text_lines(node) == ["In progress", "Submitted"]


def test_missing_nodes_give_empty_text() -> None:
    assert inline_text(None) == ""
    assert block_text(None) == ""


def test_require_raises_parse_error() -> None:
    with pytest.raises(ParseError, match="course list"):
        require(parse_html("<p></p>"), "table.courselist", "course list")


def test_extract_attachments_parses_and_removes_them() -> None:
    html = """
    <div class="inlineattachment"><div class="inlineaf-description">
      <a href="page_1c2_3_4/notes.docx?view=full"><br>notes.docx - 2026-04-14 13:30:13</a>
    </div></div>
    <div class="inlineattachment"><div class="inlineaf-description">
      <a href="page_1c2_3_5/odd.pdf">odd.pdf</a>
    </div></div>
    """

    page = Page(url=f"{BASE}/ct/page_1c2_3", html=html)

    root = parse_html(html)

    assert extract_attachments(root, page) == (
        Attachment(
            name="notes.docx",
            uploaded_at=datetime(2026, 4, 14, 13, 30, 13, tzinfo=JST),
            url=f"{BASE}/ct/page_1c2_3_4/notes.docx?view=full",
        ),
        Attachment(name="odd.pdf", uploaded_at=None, url=f"{BASE}/ct/page_1c2_3_5/odd.pdf"),
    )
    assert root.css_first("div.inlineattachment") is None


def test_parse_links_dedupes_and_skips_in_page_links() -> None:
    node = _node(
        '<div><a href="course_1_news_2">News</a> <a href="#top">Top</a>'
        '<a href="javascript:void(0)">JS</a> <a href="https://example.com/doc">Doc</a>'
        '<a href="course_1_news_2">again</a><a href="https://example.com/x"></a></div>'
    )
    page = Page(url=f"{BASE}/ct/course_1", html="")

    assert parse_links(node, page) == (
        Link(text="News", url=f"{BASE}/ct/course_1_news_2"),
        Link(text="Doc", url="https://example.com/doc"),
        Link(text="https://example.com/x", url="https://example.com/x"),
    )
