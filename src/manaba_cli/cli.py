"""Command-line entry point."""

import getpass
import logging
import sys
from datetime import datetime
from typing import Annotated

import typer

from manaba_cli import __version__, auth, render
from manaba_cli.config import Config, load_config, save_username
from manaba_cli.cookie_store import StorageState, earliest_expiry, load_state
from manaba_cli.credentials import load_credentials, store_password
from manaba_cli.errors import ManabaError, ParseError
from manaba_cli.session import ManabaSession
from manaba_cli.timeutil import JST

app = typer.Typer(
    help="Read-only CLI for manaba: courses, deadlines, news and contents.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

JsonFlag = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def root(
    debug: Annotated[
        bool, typer.Option("--debug", help="Log request URLs and status codes to stderr.")
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_print_version, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Read-only CLI for manaba."""
    if debug:
        logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
        logging.getLogger("manaba_cli").setLevel(logging.DEBUG)


@app.command()
def login(
    headed: Annotated[
        bool, typer.Option("--headed", help="Show the Chrome window (finish SSO by hand).")
    ] = False,
    set_credentials: Annotated[
        bool, typer.Option("--set-credentials", help="Prompt for username and password first.")
    ] = False,
) -> None:
    """Log in through SSO and save the session cookies."""
    config = load_config()
    if set_credentials:
        config = _prompt_credentials(config)
    auth.login(config, load_credentials(config.username), headed=headed)
    with ManabaSession(config) as session:
        session.get("home")
    render.console.print(f"Logged in to {config.base_url} as {config.username or 'unknown user'}.")


@app.command()
def status(json_output: JsonFlag = False) -> None:
    """Show whether the saved session is valid, and where config lives."""
    config = load_config()
    state = load_state(config.paths.cookies_file)
    with ManabaSession(config) as session:
        logged_in = state is not None and session.is_logged_in()
    fields = {
        "logged_in": logged_in,
        "base_url": config.base_url,
        "username": config.username,
        "credentials_stored": load_credentials(config.username) is not None,
        "cookies_expire_at": _cookies_expiry(config, state),
        "config_file": config.paths.config_file,
        "cookies_file": config.paths.cookies_file,
    }
    if json_output:
        render.print_json(fields)
    else:
        render.print_fields(fields)


def open_session(config: Config) -> ManabaSession:
    """Session that renews an expired login headlessly with the stored credentials."""

    def relogin() -> None:
        auth.login(config, load_credentials(config.username), headed=False)

    return ManabaSession(config, relogin=relogin)


def _prompt_credentials(config: Config) -> Config:
    username = typer.prompt("Username", default=config.username or None)
    password = getpass.getpass("Password (stored in the system keychain): ")
    store_password(username, password)
    save_username(config.paths, username)
    return load_config(config.paths)


def _cookies_expiry(config: Config, state: StorageState | None) -> datetime | None:
    expiry = earliest_expiry(state, config.host) if state else None
    return expiry.astimezone(JST) if expiry else None


def _report(error: ManabaError) -> None:
    render.print_error(str(error))
    if isinstance(error, ParseError) and error.html is not None:
        dump = load_config().paths.last_error_file
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_text(error.html, encoding="utf-8")
        render.print_error(f"page HTML saved to {dump}")


def main() -> None:
    try:
        app()
    except ManabaError as error:
        _report(error)
        sys.exit(error.exit_code)
