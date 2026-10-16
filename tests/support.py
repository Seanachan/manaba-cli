from pathlib import Path

from keyring.backend import KeyringBackend

BASE = "https://manaba.example.ac.jp"

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    """Anonymized manaba HTML: structure copied from the live site, all data fake."""
    return (FIXTURES / name).read_text(encoding="utf-8")


class MemoryKeyring(KeyringBackend):
    """In-process stand-in for the OS keychain."""

    priority = 1

    def __init__(self) -> None:
        super().__init__()
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.passwords[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.passwords.pop((service, username), None)
