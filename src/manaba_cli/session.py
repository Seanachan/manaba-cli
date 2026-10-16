"""GET-only HTTP access to manaba with one automatic re-login per run.

There is deliberately no method that sends POST, PUT or DELETE: manaba-cli never
submits anything to manaba. The only form submission is the SSO login performed by
the browser in :mod:`manaba_cli.auth`.
"""

import logging
import threading
from collections.abc import Callable
from types import TracebackType

import httpx

from manaba_cli import __version__
from manaba_cli.config import Config
from manaba_cli.cookie_store import load_state, to_httpx_cookies
from manaba_cli.errors import ManabaError, NotFoundError, NotLoggedInError
from manaba_cli.models import Page
from manaba_cli.urls import is_authenticated_page, redact, resolve

USER_AGENT = f"manaba-cli/{__version__} (+https://github.com/Seanachan/manaba-cli)"
REQUEST_TIMEOUT_S = 20.0
HOME_PAGE = "home"
NOT_LOGGED_IN_MESSAGE = "Not logged in to manaba. Run `manaba login` (or `manaba login --headed`)."

log = logging.getLogger(__name__)

Relogin = Callable[[], None]


class ManabaSession:
    """Thread-safe GET client; ``relogin`` is called at most once when the session expired."""

    def __init__(
        self,
        config: Config,
        relogin: Relogin | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._relogin = relogin
        self._relogin_lock = threading.Lock()
        self._relogin_attempted = False
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        )
        self._load_cookies()

    def __enter__(self) -> "ManabaSession":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def get(self, ref: str) -> Page:
        """Fetch a manaba page by URL, ``/ct/`` path or page name, re-logging in if needed."""
        url = resolve(self._config.base_url, ref)
        response = self._fetch(url)
        if not self._is_authenticated(response):
            self._renew_login()
            response = self._fetch(url)
            if not self._is_authenticated(response):
                raise NotLoggedInError(NOT_LOGGED_IN_MESSAGE)
        self._raise_for_status(response)
        return Page(url=str(response.url), html=response.text)

    def is_logged_in(self) -> bool:
        """Check the saved session without attempting a re-login."""
        return self._is_authenticated(self._fetch(resolve(self._config.base_url, HOME_PAGE)))

    def _fetch(self, url: str) -> httpx.Response:
        try:
            response = self._client.get(url)
        except httpx.HTTPError as error:
            raise ManabaError(f"Network error for {redact(url)}: {error}") from None
        log.debug("GET %s -> %s %s", redact(url), response.status_code, redact(str(response.url)))
        return response

    def _is_authenticated(self, response: httpx.Response) -> bool:
        return is_authenticated_page(str(response.url), self._config.base_url)

    def _renew_login(self) -> None:
        with self._relogin_lock:
            if self._relogin_attempted:
                return  # Never log in twice per run; the caller re-checks the session.
            self._relogin_attempted = True
            if self._relogin is None:
                raise NotLoggedInError(NOT_LOGGED_IN_MESSAGE)
            self._relogin()
            self._load_cookies()

    def _load_cookies(self) -> None:
        state = load_state(self._config.paths.cookies_file) or {}
        self._client.cookies = to_httpx_cookies(state)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        url = redact(str(response.url))
        if response.status_code in (403, 404):
            raise NotFoundError(f"{url} returned HTTP {response.status_code}.")
        if response.is_error:
            raise ManabaError(f"{url} returned HTTP {response.status_code}.")
