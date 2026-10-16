from pathlib import Path

import httpx
import pytest

from manaba_cli.config import Config, Paths
from manaba_cli.cookie_store import save_state
from manaba_cli.errors import InvalidUrlError, NotFoundError, NotLoggedInError
from manaba_cli.session import ManabaSession

BASE = "https://manaba.example.ac.jp"
IDP_LOGIN = "https://idp.example.ac.jp/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
VALID_COOKIE = "valid"


def _state(session_value: str) -> dict:
    cookie = {"name": "sessionid", "value": session_value, "domain": "manaba.example.ac.jp"}
    return {"cookies": [{**cookie, "path": "/", "expires": -1}], "origins": []}


def _fake_manaba(request: httpx.Request) -> httpx.Response:
    """Serves pages to a valid session cookie and redirects everyone else to the IdP."""
    if request.url.host != "manaba.example.ac.jp":
        return httpx.Response(200, text="<form>IdP login</form>")
    if f"sessionid={VALID_COOKIE}" not in request.headers.get("cookie", ""):
        return httpx.Response(302, headers={"Location": IDP_LOGIN})
    if request.url.path == "/ct/missing":
        return httpx.Response(404)
    return httpx.Response(200, text=f"page {request.url.path}")


@pytest.fixture
def config(tmp_path: Path) -> Config:
    paths = Paths(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache")
    return Config(base_url=BASE, username="s0000000", paths=paths)


def _session(config: Config, relogin=None) -> ManabaSession:
    return ManabaSession(config, relogin=relogin, transport=httpx.MockTransport(_fake_manaba))


def test_get_with_valid_cookies(config: Config) -> None:
    save_state(config.paths.cookies_file, _state(VALID_COOKIE))

    page = _session(config).get("course_1_news")

    assert page.html == "page /ct/course_1_news"
    assert page.url == f"{BASE}/ct/course_1_news"


def test_expired_session_relogs_in_once(config: Config) -> None:
    save_state(config.paths.cookies_file, _state("expired"))
    calls: list[int] = []

    def relogin() -> None:
        calls.append(1)
        save_state(config.paths.cookies_file, _state(VALID_COOKIE))

    session = _session(config, relogin)

    assert session.get("home").html == "page /ct/home"
    assert session.get("course_1_news").html == "page /ct/course_1_news"
    assert calls == [1]


def test_failed_relogin_is_not_retried(config: Config) -> None:
    calls: list[int] = []

    def relogin() -> None:
        calls.append(1)

    session = _session(config, relogin)

    for _ in range(2):
        with pytest.raises(NotLoggedInError):
            session.get("home")
    assert calls == [1]


def test_without_relogin_reports_not_logged_in(config: Config) -> None:
    with pytest.raises(NotLoggedInError):
        _session(config).get("home")


def test_is_logged_in_does_not_relogin(config: Config) -> None:
    def relogin() -> None:
        raise AssertionError("must not be called")

    assert _session(config, relogin).is_logged_in() is False


def test_missing_page_raises_not_found(config: Config) -> None:
    save_state(config.paths.cookies_file, _state(VALID_COOKIE))

    with pytest.raises(NotFoundError):
        _session(config).get("missing")


def test_rejects_urls_outside_manaba(config: Config) -> None:
    with pytest.raises(InvalidUrlError):
        _session(config).get("https://evil.example.com/ct/home")


def test_session_exposes_no_write_methods() -> None:
    write_methods = {"post", "put", "patch", "delete"}

    assert write_methods.isdisjoint(name.lower() for name in dir(ManabaSession))
