from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from delayed_publishes.timeparse import parse_local_datetime, parse_local_time_for_date


def test_parse_full_iso_like_datetime_to_utc() -> None:
    value = parse_local_datetime(
        "2026-05-20 19:30",
        ZoneInfo("Europe/Moscow"),
        now_utc=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert value.isoformat() == "2026-05-20T16:30:00+00:00"


def test_parse_short_date_rolls_to_next_year_when_needed() -> None:
    value = parse_local_datetime(
        "01.01 10:00",
        ZoneInfo("Europe/Moscow"),
        now_utc=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert value.year == 2027


def test_rejects_past_datetime() -> None:
    with pytest.raises(ValueError):
        parse_local_datetime(
            "2026-05-15 19:30",
            ZoneInfo("Europe/Moscow"),
            now_utc=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
        )


def test_parse_time_for_selected_date_to_utc() -> None:
    value = parse_local_time_for_date(
        "19:30",
        datetime(2026, 5, 20).date(),
        ZoneInfo("Europe/Moscow"),
        now_utc=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert value.isoformat() == "2026-05-20T16:30:00+00:00"


def test_rejects_invalid_time_for_selected_date() -> None:
    with pytest.raises(ValueError):
        parse_local_time_for_date(
            "24:00",
            datetime(2026, 5, 20).date(),
            ZoneInfo("Europe/Moscow"),
            now_utc=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
        )
