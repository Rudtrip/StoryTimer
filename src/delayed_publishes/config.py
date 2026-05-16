from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_path: Path
    media_dir: Path
    onboarding_video_path: Path | None
    poll_timeout_seconds: int
    scheduler_interval_seconds: int
    default_timezone: ZoneInfo
    story_active_period_seconds: int
    published_media_retention_hours: int
    failed_media_retention_days: int
    draft_retention_hours: int


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    timezone_name = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow").strip()
    try:
        default_timezone = ZoneInfo(timezone_name)
    except Exception as exc:
        raise ValueError(f"Invalid DEFAULT_TIMEZONE: {timezone_name}") from exc

    onboarding_video_path_raw = os.getenv("ONBOARDING_VIDEO_PATH", "assets/telegram_business_setup.mp4").strip()

    return Settings(
        telegram_bot_token=token,
        database_path=Path(os.getenv("DATABASE_PATH", "data/delayed_publishes.sqlite3")),
        media_dir=Path(os.getenv("MEDIA_DIR", "data/media")),
        onboarding_video_path=Path(onboarding_video_path_raw) if onboarding_video_path_raw else None,
        poll_timeout_seconds=_int_env("POLL_TIMEOUT_SECONDS", 30),
        scheduler_interval_seconds=_int_env("SCHEDULER_INTERVAL_SECONDS", 15),
        default_timezone=default_timezone,
        story_active_period_seconds=_int_env("STORY_ACTIVE_PERIOD_SECONDS", 86400),
        published_media_retention_hours=_int_env("PUBLISHED_MEDIA_RETENTION_HOURS", 24),
        failed_media_retention_days=_int_env("FAILED_MEDIA_RETENTION_DAYS", 7),
        draft_retention_hours=_int_env("DRAFT_RETENTION_HOURS", 24),
    )
