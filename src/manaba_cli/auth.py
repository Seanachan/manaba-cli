"""Shibboleth SSO login driven through the system Chrome by Playwright.

This is the only code path that submits a form, and it submits only the IdP login
form (plus an attribute-release consent page if one appears), exactly as a person
would in the browser. All manaba reads go through :mod:`manaba_cli.session` (GET only).
"""

import time

from manaba_cli.config import Config
from manaba_cli.cookie_store import save_state
from manaba_cli.credentials import Credentials
from manaba_cli.errors import NotLoggedInError
from manaba_cli.urls import is_authenticated_page, redact

# Standard Shibboleth IdP v3+ login form, verified on idp.account.tsukuba.ac.jp.
USERNAME_FIELD = "input[name=j_username]"
PASSWORD_FIELD = "input[name=j_password]"
PROCEED_BUTTON = "button[name=_eventId_proceed], input[type=submit][name=_eventId_proceed]"

HEADLESS_TIMEOUT_S = 60
HEADED_TIMEOUT_S = 300
POLL_INTERVAL_MS = 500


def login(config: Config, credentials: Credentials | None, *, headed: bool) -> None:
    """Log in through SSO and save the session cookies.

    Headless mode needs stored credentials. Headed mode opens a Chrome window; it
    fills stored credentials when available and otherwise waits for the user.
    """
    if credentials is None and not headed:
        raise NotLoggedInError("No stored credentials. Run `manaba login --set-credentials` first.")

    # Imported lazily: Playwright is heavy and only needed when logging in.
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    timeout_s = HEADED_TIMEOUT_S if headed else HEADLESS_TIMEOUT_S
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=not headed)
            try:
                context = browser.new_context(storage_state=_previous_state_file(config))
                page = context.new_page()
                page.goto(f"{config.base_url}/ct/home")
                _complete_sso(page, config.base_url, credentials, headed, timeout_s)
                save_state(config.paths.cookies_file, context.storage_state())
            finally:
                browser.close()
    except PlaywrightError as error:
        # Only the first line: Playwright call logs are verbose and not meant for users.
        reason = str(error).splitlines()[0]
        raise NotLoggedInError(f"Browser login failed: {reason}") from None


def _previous_state_file(config: Config) -> str | None:
    """Reuse saved IdP cookies so an expired manaba session can renew without a password."""
    cookies_file = config.paths.cookies_file
    return str(cookies_file) if cookies_file.exists() else None


def _complete_sso(
    page, base_url: str, credentials: Credentials | None, headed: bool, timeout_s: int
) -> None:
    deadline = time.monotonic() + timeout_s
    submitted = False
    while time.monotonic() < deadline:
        if is_authenticated_page(page.url, base_url):
            return
        if page.locator(USERNAME_FIELD).is_visible():
            if credentials is not None and not submitted:
                _submit_credentials(page, credentials)
                submitted = True
            elif submitted and not headed:
                raise NotLoggedInError(
                    "The IdP rejected the username or password. "
                    "Run `manaba login --set-credentials` to update them."
                )
        elif page.locator(PROCEED_BUTTON).first.is_visible():
            page.locator(PROCEED_BUTTON).first.click()  # attribute-release consent page
        page.wait_for_timeout(POLL_INTERVAL_MS)

    raise NotLoggedInError(
        f"SSO did not return to manaba within {timeout_s}s "
        f"(stopped at {redact(page.url)}). Try `manaba login --headed`."
    )


def _submit_credentials(page, credentials: Credentials) -> None:
    page.locator(USERNAME_FIELD).fill(credentials.username)
    page.locator(PASSWORD_FIELD).fill(credentials.password)
    with page.expect_navigation():
        page.locator(PROCEED_BUTTON).first.click()
