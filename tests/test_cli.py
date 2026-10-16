import json

from typer.testing import CliRunner

from manaba_cli import __version__
from manaba_cli.cli import app
from manaba_cli.errors import ManabaError

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])

    for command in ("login", "status", "courses", "todo", "news", "contents", "show"):
        assert command in result.output


def test_status_without_session_needs_no_network() -> None:
    result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0
    status = json.loads(result.output)
    assert status["logged_in"] is False
    assert status["credentials_stored"] is False


def test_bare_news_id_requires_course() -> None:
    result = runner.invoke(app, ["news", "show", "123"])

    assert isinstance(result.exception, ManabaError)
