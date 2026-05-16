from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


SHORT_DATE_RE = re.compile(r"^(?P<day>\d{1,2})\.(?P<month>\d{1,2}) (?P<hour>\d{1,2}):(?P<minute>\d{2})$")

SUPPORTED_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%d.%m.%Y %H:%M",
)


def parse_local_datetime(raw: str, user_timezone: ZoneInfo, now_utc: datetime | None = None) -> datetime:
    text = re.sub(r"\s+", " ", raw.strip())
    if not text:
        raise ValueError("empty datetime")

    now = now_utc or datetime.now(timezone.utc)
    local_now = now.astimezone(user_timezone)

    parsed: datetime | None = _parse_short_date(text, local_now)
    for fmt in SUPPORTED_FORMATS:
        if parsed is not None:
            break
        try:
            candidate = datetime.strptime(text, fmt)
        except ValueError:
            continue
        parsed = candidate
        break

    if parsed is None:
        raise ValueError("unsupported datetime format")

    scheduled_at = parsed.replace(tzinfo=user_timezone).astimezone(timezone.utc)
    if scheduled_at <= now:
        raise ValueError("datetime is in the past")

    return scheduled_at


def parse_local_time_for_date(
    raw: str,
    selected_date: date,
    user_timezone: ZoneInfo,
    now_utc: datetime | None = None,
) -> datetime:
    text = re.sub(r"\s+", " ", raw.strip())
    match = re.match(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})$", text)
    if not match:
        raise ValueError("unsupported time format")

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    if hour > 23 or minute > 59:
        raise ValueError("unsupported time format")

    now = now_utc or datetime.now(timezone.utc)
    local_datetime = datetime.combine(selected_date, time(hour=hour, minute=minute), tzinfo=user_timezone)
    scheduled_at = local_datetime.astimezone(timezone.utc)
    if scheduled_at <= now:
        raise ValueError("datetime is in the past")
    return scheduled_at


def _parse_short_date(text: str, local_now: datetime) -> datetime | None:
    match = SHORT_DATE_RE.match(text)
    if not match:
        return None
    parts = {key: int(value) for key, value in match.groupdict().items()}
    candidate = datetime(
        year=local_now.year,
        month=parts["month"],
        day=parts["day"],
        hour=parts["hour"],
        minute=parts["minute"],
    )
    if candidate.replace(tzinfo=local_now.tzinfo) <= local_now:
        candidate = candidate.replace(year=local_now.year + 1)
    return candidate


def format_utc_for_user(value: datetime, user_timezone: ZoneInfo) -> str:
    return value.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M %Z")
