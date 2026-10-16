"""Persistence of the browser storage state (cookies) captured after SSO login.

The file is Playwright's ``storage_state`` JSON, written with mode 0600. It keeps
the IdP cookies too, so a later re-login can often complete without a password.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from manaba_cli.config import ensure_private_dir

StorageState = dict[str, Any]


def save_state(path: Path, state: StorageState) -> None:
    ensure_private_dir(path.parent)
    temp_path = path.with_suffix(".tmp")
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    if hasattr(os, "fchmod"):  # POSIX only; also tightens a leftover temp file
        os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(state, file)
    os.replace(temp_path, path)


def load_state(path: Path) -> StorageState | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def to_httpx_cookies(state: StorageState) -> httpx.Cookies:
    jar = httpx.Cookies()
    for cookie in state.get("cookies", []):
        jar.set(cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"])
    return jar


def earliest_expiry(state: StorageState, host: str) -> datetime | None:
    """Earliest expiry of persistent cookies sent to ``host``; None if only session cookies."""
    expiries = [
        cookie["expires"]
        for cookie in state.get("cookies", [])
        if _matches_host(cookie["domain"], host) and cookie.get("expires", -1) > 0
    ]
    if not expiries:
        return None
    return datetime.fromtimestamp(min(expiries), tz=UTC)


def _matches_host(cookie_domain: str, host: str) -> bool:
    domain = cookie_domain.lstrip(".")
    return host == domain or host.endswith("." + domain)
