"""Test isolation: no real keychain, no real config, no manaba environment variables.

Tests also never need network or Chrome: HTTP goes through httpx.MockTransport and
the browser login is not exercised.
"""

from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest

from tests.support import MemoryKeyring


@pytest.fixture(autouse=True)
def memory_keyring() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.delenv("MANABA_BASE_URL", raising=False)
    monkeypatch.delenv("MANABA_USERNAME", raising=False)
