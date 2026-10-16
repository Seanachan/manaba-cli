from pathlib import Path

import pytest

from manaba_cli.config import DEFAULT_BASE_URL, Paths, load_config, save_username


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    return Paths(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MANABA_BASE_URL", raising=False)
    monkeypatch.delenv("MANABA_USERNAME", raising=False)


def test_defaults_without_config_file(paths: Paths) -> None:
    config = load_config(paths)

    assert config.base_url == DEFAULT_BASE_URL
    assert config.username is None


def test_save_username_round_trips(paths: Paths) -> None:
    save_username(paths, "s0000000")

    assert load_config(paths).username == "s0000000"


def test_save_username_keeps_other_keys(paths: Paths) -> None:
    paths.config_dir.mkdir(parents=True)
    paths.config_file.write_text('base_url = "https://manaba.example.ac.jp/"\n')

    save_username(paths, "s0000000")

    config = load_config(paths)
    assert config.base_url == "https://manaba.example.ac.jp"
    assert config.username == "s0000000"


def test_env_overrides_file(paths: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    save_username(paths, "from-file")
    monkeypatch.setenv("MANABA_USERNAME", "from-env")
    monkeypatch.setenv("MANABA_BASE_URL", "https://manaba.example.ac.jp")

    config = load_config(paths)

    assert config.username == "from-env"
    assert config.base_url == "https://manaba.example.ac.jp"


def test_xdg_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    paths = Paths.from_env()

    assert paths.cookies_file == tmp_path / "cfg" / "manaba-cli" / "cookies.json"
    assert paths.last_error_file == tmp_path / "cache" / "manaba-cli" / "last-error.html"
