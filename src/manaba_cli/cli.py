"""Command-line entry point."""

import getpass
import logging
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Annotated

import typer

from manaba_cli import __version__, auth, render
from manaba_cli.client import ManabaClient
from manaba_cli.config import Config, load_config, save_username
from manaba_cli.cookie_store import StorageState, earliest_expiry, load_state
from manaba_cli.credentials import load_credentials, store_password
from manaba_cli.errors import ManabaError, ParseError
from manaba_cli.models import Course
from manaba_cli.parsers.news import news_article_ref
from manaba_cli.selection import select_news, select_tasks
from manaba_cli.session import ManabaSession
from manaba_cli.timeutil import JST

app = typer.Typer(
    help="Read-only CLI for manaba: courses, deadlines, news and contents.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

JsonFlag = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]
CourseOption = Annotated[
    int | None, typer.Option("--course", help="Only this course id (see `manaba courses`).")
]


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


@app.command()
def courses(json_output: JsonFlag = False) -> None:
    """List the courses on your My Courses page."""
    with open_client() as client:
        result = client.courses()
    _output(result, json_output, render.print_courses)


@app.command()
def todo(
    show_all: Annotated[
        bool, typer.Option("--all", help="Include submitted and closed tasks.")
    ] = False,
    course: CourseOption = None,
    days: Annotated[
        int | None, typer.Option("--days", min=0, help="Only tasks due within N days.")
    ] = None,
    json_output: JsonFlag = False,
) -> None:
    """Tasks across all courses, soonest deadline first.

    By default only what is still to do: not submitted and not closed.
    """
    with open_client() as client:
        tasks = client.tasks(_select_courses(client.courses(), course))
    selected = select_tasks(tasks, include_done=show_all, within_days=days, now=datetime.now(JST))
    _output(selected, json_output, render.print_tasks)


news_app = typer.Typer(help="Course news.")
app.add_typer(news_app, name="news")


@news_app.callback(invoke_without_command=True)
def news(
    ctx: typer.Context,
    course: CourseOption = None,
    since: Annotated[
        datetime | None,
        typer.Option("--since", formats=["%Y-%m-%d"], help="Only news posted on/after YYYY-MM-DD."),
    ] = None,
    limit: Annotated[int | None, typer.Option("--limit", min=1, help="At most N items.")] = None,
    json_output: JsonFlag = False,
) -> None:
    """List course news across courses, newest first. `manaba news show` prints one."""
    if ctx.invoked_subcommand is not None:
        return
    with open_client() as client:
        items = client.news(_select_courses(client.courses(), course))
    since_jst = since.replace(tzinfo=JST) if since else None
    _output(select_news(items, since=since_jst, limit=limit), json_output, render.print_news)


@news_app.command("show")
def news_show(
    ref: Annotated[str, typer.Argument(help="News URL, or a news id together with --course.")],
    course: CourseOption = None,
    json_output: JsonFlag = False,
) -> None:
    """Print one news article. Like the browser, this marks it as read."""
    if ref.isdigit():
        if course is None:
            raise ManabaError("A bare news id needs --course.")
        ref = news_article_ref(course, int(ref))
    with open_client() as client:
        article = client.news_article(ref)
    _output(article, json_output, render.print_article)


@contextmanager
def open_client() -> Iterator[ManabaClient]:
    """Client whose session renews an expired login headlessly with the stored credentials."""
    config = load_config()

    def relogin() -> None:
        auth.login(config, load_credentials(config.username), headed=False)

    with ManabaSession(config, relogin=relogin) as session:
        yield ManabaClient(session)


def _select_courses(courses: list[Course], course_id: int | None) -> list[Course]:
    if course_id is None:
        return courses
    selected = [course for course in courses if course.id == course_id]
    if not selected:
        raise ManabaError(f"Course {course_id} is not on your My Courses page.")
    return selected


def _output[T](result: T, as_json: bool, print_table: Callable[[T], None]) -> None:
    if as_json:
        render.print_json(result)
    else:
        print_table(result)


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
