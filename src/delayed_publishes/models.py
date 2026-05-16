from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"


class PostStatus(str, Enum):
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStep(str, Enum):
    WAITING_FOR_MEDIA = "waiting_for_media"
    WAITING_FOR_DATE = "waiting_for_date"
    WAITING_FOR_TIME = "waiting_for_time"
    WAITING_FOR_CAPTION = "waiting_for_caption"
    WAITING_FOR_BUSINESS = "waiting_for_business"
    WAITING_FOR_TIMEZONE = "waiting_for_timezone"


@dataclass(frozen=True)
class UserAccount:
    telegram_user_id: int
    chat_id: int
    timezone: str
    language: str
    business_connection_id: str | None


@dataclass(frozen=True)
class ScheduledPost:
    id: int
    telegram_user_id: int
    chat_id: int
    business_connection_id: str
    media_type: MediaType
    media_path: Path
    scheduled_at_utc: datetime
    status: PostStatus
    caption: str | None
    attempts: int
    last_error: str | None
    created_at_utc: datetime
    published_at_utc: datetime | None
    failed_at_utc: datetime | None
    cancelled_at_utc: datetime | None
