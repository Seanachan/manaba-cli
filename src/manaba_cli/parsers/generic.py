"""Any manaba page as title, main text and links, for ``manaba show``."""

from selectolax.lexbor import LexborHTMLParser

from manaba_cli.models import Page, PageDump
from manaba_cli.parsers.dom import Node, block_text, inline_text, parse_html, parse_links

# Most specific first: the main column of course pages (wide and narrow layouts), content
# pages, news articles; the whole page body as the last resort.
_MAIN_CONTENT = (
    "div.contentbody-l",
    "div.contentbody-s",
    "div.contentbody-left",
    "div.articlebody",
    "div.groupnews_frame",
    "div.pagebody",
    "body",
)
_TITLE = ("h1.pagetitle", "h2.msg-subject", "tr.title", "h1", "title")


def parse_generic_page(page: Page) -> PageDump:
    root = parse_html(page.html)
    main = _first_match(root, _MAIN_CONTENT)
    return PageDump(
        url=page.url,
        title=inline_text(_first_match(root, _TITLE)),
        text=block_text(main),
        links=parse_links(main, page),
    )


def _first_match(root: LexborHTMLParser, selectors: tuple[str, ...]) -> Node | None:
    return next((node for s in selectors if (node := root.css_first(s)) is not None), None)
