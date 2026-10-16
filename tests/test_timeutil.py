from datetime import datetime

from manaba_cli.timeutil import JST, find_datetimes, parse_datetime


def test_parse_minutes_precision() -> None:
    parsed = parse_datetime("2026-10-18 23:00")

    assert parsed == datetime(2026, 10, 18, 23, 0, tzinfo=JST)
    assert parsed.isoformat() == "2026-10-18T23:00:00+09:00"


def test_parse_seconds_precision_and_extra_spaces() -> None:
    assert parse_datetime(" 2026-10-13  12:00:30 ") == datetime(2026, 10, 13, 12, 0, 30, tzinfo=JST)


def test_parse_returns_none_for_text_without_datetime() -> None:
    assert parse_datetime("") is None
    assert parse_datetime("受付中") is None


def test_find_datetimes_in_publish_window() -> None:
    window = "公開期間 2026-10-01 09:00:00 ～ 2026-12-31 23:59:00"

    assert find_datetimes(window) == [
        datetime(2026, 10, 1, 9, 0, tzinfo=JST),
        datetime(2026, 12, 31, 23, 59, tzinfo=JST),
    ]
