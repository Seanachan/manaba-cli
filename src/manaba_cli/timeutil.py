"""manaba shows local Japan time as ``YYYY-MM-DD HH:MM[:SS]``; we emit aware datetimes."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

_DATETIME_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?")


def find_datetimes(text: str) -> list[datetime]:
    """All manaba datetimes in ``text``, in order of appearance, as JST-aware values."""
    return [_to_datetime(match) for match in _DATETIME_PATTERN.finditer(text)]


def parse_datetime(text: str) -> datetime | None:
    """First manaba datetime in ``text``, or None when there is none (e.g. an empty cell)."""
    found = find_datetimes(text)
    return found[0] if found else None


def _to_datetime(match: re.Match[str]) -> datetime:
    year, month, day, hour, minute, second = (int(group or 0) for group in match.groups())
    return datetime(year, month, day, hour, minute, second, tzinfo=JST)
