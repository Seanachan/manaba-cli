from pathlib import Path

import pytest

from manaba_cli import auth
from manaba_cli.config import Config, Paths
from manaba_cli.errors import NotLoggedInError


def test_headless_login_without_credentials_fails_before_starting_a_browser(
    tmp_path: Path,
) -> None:
    config = Config(
        base_url="https://manaba.example.ac.jp",
        username=None,
        paths=Paths(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache"),
    )

    with pytest.raises(NotLoggedInError, match="--set-credentials"):
        auth.login(config, None, headed=False)
