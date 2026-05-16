from __future__ import annotations

from pathlib import Path

from .models import MediaType


PHOTO_MAX_BYTES = 10 * 1024 * 1024
VIDEO_MAX_BYTES = 30 * 1024 * 1024


def validate_story_media(media_type: MediaType, path: Path) -> None:
    size = path.stat().st_size
    if media_type == MediaType.PHOTO and size > PHOTO_MAX_BYTES:
        raise ValueError("photo_too_large")
    if media_type == MediaType.VIDEO and size > VIDEO_MAX_BYTES:
        raise ValueError("video_too_large")
