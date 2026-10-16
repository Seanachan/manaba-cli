"""User configuration and on-disk locations.

Config lives in ``$XDG_CONFIG_HOME/manaba-cli/config.toml`` (default ``~/.config``).
Environment variables ``MANABA_BASE_URL`` and ``MANABA_USERNAME`` override the file.
The password is never stored here; see :mod:`manaba_cli.credentials`.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import tomli_w

APP_NAME = "manaba-cli"
DEFAULT_BASE_URL = "https://manaba.tsukuba.ac.jp"

ENV_BASE_URL = "MANABA_BASE_URL"
ENV_USERNAME = "MANABA_USERNAME"


@dataclass(frozen=True)
class Paths:
    config_dir: Path
    cache_dir: Path

    @classmethod
    def from_env(cls) -> "Paths":
        home = Path.home()
        config_root = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        cache_root = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
        return cls(config_dir=config_root / APP_NAME, cache_dir=cache_root / APP_NAME)

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"

    @property
    def cookies_file(self) -> Path:
        return self.config_dir / "cookies.json"

    @property
    def last_error_file(self) -> Path:
        return self.cache_dir / "last-error.html"


@dataclass(frozen=True)
class Config:
    base_url: str
    username: str | None
    paths: Paths

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).netloc


def load_config(paths: Paths | None = None) -> Config:
    paths = paths or Paths.from_env()
    stored = _read_toml(paths.config_file)
    base_url = os.environ.get(ENV_BASE_URL) or stored.get("base_url") or DEFAULT_BASE_URL
    username = os.environ.get(ENV_USERNAME) or stored.get("username")
    return Config(base_url=base_url.rstrip("/"), username=username, paths=paths)


def save_username(paths: Paths, username: str) -> None:
    stored = _read_toml(paths.config_file)
    stored["username"] = username
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.config_file.write_text(tomli_w.dumps(stored), encoding="utf-8")


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as file:
        return tomllib.load(file)
