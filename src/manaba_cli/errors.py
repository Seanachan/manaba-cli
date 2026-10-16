"""Exceptions with the process exit code each one maps to."""


class ManabaError(Exception):
    """Base class for errors reported to the user without a traceback."""

    exit_code = 1


class NotLoggedInError(ManabaError):
    """No usable session, missing credentials, or the SSO login failed."""

    exit_code = 2


class ParseError(ManabaError):
    """A manaba page did not have the structure the parser expects."""

    exit_code = 3

    def __init__(self, message: str, *, url: str | None = None, html: str | None = None) -> None:
        super().__init__(message)
        self.url = url
        self.html = html


class NotFoundError(ManabaError):
    """manaba answered 403/404 for the requested page."""


class InvalidUrlError(ManabaError):
    """A URL argument points outside the configured manaba site."""
