from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .storage import Storage


logger = logging.getLogger(__name__)


class RetentionCleaner:
    def __init__(
        self,
        storage: Storage,
        published_media_retention_hours: int,
        failed_media_retention_days: int,
        draft_retention_hours: int,
    ):
        self.storage = storage
        self.published_media_retention = timedelta(hours=published_media_retention_hours)
        self.failed_media_retention = timedelta(days=failed_media_retention_days)
        self.draft_retention = timedelta(hours=draft_retention_hours)

    def run_once(self) -> None:
        now = datetime.now(timezone.utc)
        self._cleanup_posts(now)
        self._cleanup_sessions(now)

    def _cleanup_posts(self, now: datetime) -> None:
        candidates = self.storage.media_cleanup_candidates(
            published_before=now - self.published_media_retention,
            failed_before=now - self.failed_media_retention,
        )
        for post in candidates:
            self._unlink(post.media_path)
            self.storage.delete_post_record(post.id)

    def _cleanup_sessions(self, now: datetime) -> None:
        stale_before = now - self.draft_retention
        for session in self.storage.stale_sessions(stale_before):
            media_path = session["media_path"]
            if media_path:
                self._unlink(Path(media_path))
            self.storage.clear_session(session["telegram_user_id"])

    def _unlink(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not delete media file %s", path)
