from manaba_cli.models import Page
from manaba_cli.parsers.account import parse_screen_name
from tests.support import BASE


def test_screen_name_from_header() -> None:
    html = (
        '<span id="screenname"><a onclick="return manaba.userballoon(\'1\', event);" '
        'href="#">STUDENT NAME</a></span>'
    )

    assert parse_screen_name(Page(url=f"{BASE}/ct/home", html=html)) == "STUDENT NAME"


def test_screen_name_missing() -> None:
    assert parse_screen_name(Page(url=f"{BASE}/ct/home", html="<p></p>")) is None
