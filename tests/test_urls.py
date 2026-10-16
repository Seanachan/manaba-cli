import pytest

from manaba_cli.errors import InvalidUrlError
from manaba_cli.urls import is_authenticated_page, redact, resolve

BASE = "https://manaba.example.ac.jp"


@pytest.mark.parametrize(
    "ref",
    [
        "course_100_report",
        "/ct/course_100_report",
        "https://manaba.example.ac.jp/ct/course_100_report",
    ],
)
def test_resolve_accepts_page_name_path_and_url(ref: str) -> None:
    assert resolve(BASE, ref) == f"{BASE}/ct/course_100_report"


@pytest.mark.parametrize(
    "ref",
    [
        "https://evil.example.com/ct/home",
        "//evil.example.com/ct/home",
        "http://manaba.example.ac.jp/ct/home",
    ],
)
def test_resolve_rejects_other_sites(ref: str) -> None:
    with pytest.raises(InvalidUrlError):
        resolve(BASE, ref)


@pytest.mark.parametrize(
    "ref",
    [
        "logout?lang=en",
        "home_lang_ja",
        "home_favoritecourse_100_set_course__",
        "home_course?chglistformat=thumbnail",
        f"{BASE}/ct/home?chglistformat=list",
    ],
)
def test_resolve_rejects_state_changing_links(ref: str) -> None:
    with pytest.raises(InvalidUrlError, match="read-only"):
        resolve(BASE, ref)


def test_resolve_allows_paging_parameters() -> None:
    url = resolve(BASE, "course_100_news?start=1&pagelen=50")

    assert url == f"{BASE}/ct/course_100_news?start=1&pagelen=50"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"{BASE}/ct/home", True),
        (f"{BASE}/ct/course_100_news", True),
        (f"{BASE}/ct/login", False),
        ("https://idp.example.ac.jp/idp/profile/SAML2/Redirect/SSO?execution=e1s1", False),
        (f"{BASE}/", False),
    ],
)
def test_is_authenticated_page(url: str, expected: bool) -> None:
    assert is_authenticated_page(url, BASE) is expected


def test_redact_drops_query() -> None:
    assert (
        redact("https://idp.example.ac.jp/SSO?SAMLRequest=abc#x") == "https://idp.example.ac.jp/SSO"
    )
