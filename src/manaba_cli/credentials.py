"""Password storage in the OS keychain (macOS Keychain via ``keyring``).

The password never touches disk or logs; only the username is kept in config.
"""

import keyring

KEYRING_SERVICE = "manaba-cli"


def get_password(username: str) -> str | None:
    return keyring.get_password(KEYRING_SERVICE, username)


def set_password(username: str, password: str) -> None:
    keyring.set_password(KEYRING_SERVICE, username, password)
