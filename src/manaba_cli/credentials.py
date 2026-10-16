"""Password storage in the OS keychain (macOS Keychain via ``keyring``).

The password never touches disk or logs; only the username is kept in config.
"""

from dataclasses import dataclass

import keyring

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
    password = keyring.get_password(KEYRING_SERVICE, username)
    if password is None:
        return None
    return Credentials(username=username, password=password)


def store_password(username: str, password: str) -> None:
    keyring.set_password(KEYRING_SERVICE, username, password)
