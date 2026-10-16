import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manaba_cli.cookie_store import earliest_expiry, load_state, save_state, to_httpx_cookies

HOST = "manaba.example.ac.jp"

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")


def _cookie(name: str, value: str, domain: str, expires: int) -> dict:
    return {"name": name, "value": value, "domain": domain, "path": "/", "expires": expires}


STATE = {
    "cookies": [
        _cookie("sessionid", "a", HOST, -1),
        _cookie("remember", "b", HOST, 2_000_000_000),
        _cookie("wide", "c", ".example.ac.jp", 1_900_000_000),
        _cookie("idp", "d", "idp.example.ac.jp", 1_000),
    ],
    "origins": [],
}


def test_save_state_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "config" / "cookies.json"

    save_state(path, STATE)

    assert load_state(path) == STATE


@posix_only
def test_save_state_is_private(tmp_path: Path) -> None:
    path = tmp_path / "config" / "cookies.json"

    save_state(path, STATE)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@posix_only
def test_save_state_tightens_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "cookies.json"
    path.write_text("{}")
    path.chmod(0o644)

    save_state(path, STATE)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_load_state_missing_file(tmp_path: Path) -> None:
    assert load_state(tmp_path / "absent.json") is None


def test_to_httpx_cookies_keeps_domains() -> None:
    jar = to_httpx_cookies(STATE)

    assert jar.get("sessionid", domain=HOST) == "a"
    assert jar.get("idp", domain="idp.example.ac.jp") == "d"


def test_earliest_expiry_ignores_session_and_foreign_cookies() -> None:
    expiry = earliest_expiry(STATE, HOST)

    assert expiry == datetime.fromtimestamp(1_900_000_000, tz=UTC)


def test_earliest_expiry_none_when_only_session_cookies() -> None:
    state = {"cookies": [STATE["cookies"][0]]}

    assert earliest_expiry(state, HOST) is None
