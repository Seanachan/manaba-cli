"""URL helpers shared by the browser login and the HTTP session."""

from urllib.parse import urljoin, urlsplit

from manaba_cli.errors import InvalidUrlError

CT_PREFIX = "/ct/"
LOGIN_PATH_PREFIX = "/ct/login"


def resolve(base_url: str, ref: str) -> str:
    """Absolute URL of a manaba page given as a full URL, a ``/ct/...`` path or a bare page name.

    Raises InvalidUrlError when the result is not on the configured manaba site.
    """
    url = urljoin(base_url + CT_PREFIX, ref.strip())
    target, base = urlsplit(url), urlsplit(base_url)
    if (target.scheme, target.netloc) != (base.scheme, base.netloc):
        raise InvalidUrlError(f"{redact(url)} is not on {base_url}")
    return url


def is_authenticated_page(url: str, base_url: str) -> bool:
    """True for a manaba page that is neither the IdP nor manaba's own login page."""
    target = urlsplit(url)
    return (
        target.netloc == urlsplit(base_url).netloc
        and target.path.startswith(CT_PREFIX)
        and not target.path.startswith(LOGIN_PATH_PREFIX)
    )


def redact(url: str) -> str:
    """``url`` without query or fragment, which may carry SAML payloads or tokens."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"
