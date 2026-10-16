"""Command-line entry point."""

from typing import Annotated

import typer

from manaba_cli import __version__

app = typer.Typer(
    help="Read-only CLI for manaba: courses, deadlines, news and contents.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_print_version, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Read-only CLI for manaba."""


def main() -> None:
    app()
