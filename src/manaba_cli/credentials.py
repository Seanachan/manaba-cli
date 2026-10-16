"""Password storage in the OS keychain via ``keyring``.

macOS Keychain and Windows Credential Locker work out of the box; Linux needs a
Secret Service provider such as GNOME Keyring or KWallet. The password never touches
disk or logs; only the username is kept in config.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import keyring
from keyring.errors import KeyringError

from manaba_cli.errors import ManabaError

KEYRING_SERVICE = "manaba-cli"


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str

    def __repr__(self) -> str:
        return f"Credentials(username={self.username!r}, password=***)"


def load_credentials(username: str | None) -> Credentials | None:
    if not username:
        return None
    with _keyring_errors():
        password = keyring.get_password(KEYRING_SERVICE, username)
    if password is None:
        return None
    return Credentials(username=username, password=password)


def store_password(username: str, password: str) -> None:
    with _keyring_errors():
        keyring.set_password(KEYRING_SERVICE, username, password)


@contextmanager
def _keyring_errors() -> Iterator[None]:
    try:
        yield
    except KeyringError as error:
        raise ManabaError(
            f"The system keyring is not usable ({error}). On Linux, install and unlock a "
            "Secret Service provider such as GNOME Keyring or KWallet."
        ) from None
