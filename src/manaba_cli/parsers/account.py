"""The logged-in user, from the header of ``/ct/home``."""

from manaba_cli.models import Page
from manaba_cli.parsers.dom import inline_text, parse_html


def parse_screen_name(page: Page) -> str | None:
    return inline_text(parse_html(page.html).css_first("#screenname")) or None
