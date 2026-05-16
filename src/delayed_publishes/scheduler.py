from __future__ import annotations

import logging
import threading

from .cleanup import RetentionCleaner
from .i18n import t
from .storage import Storage
from .telegram_api import TelegramApi


logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        storage: Storage,
        telegram_api: TelegramApi,
        interval_seconds: int,
        story_active_period_seconds: int,
        cleaner: RetentionCleaner | None = None,
    ):
        self.storage = storage
        self.telegram_api = telegram_api
        self.interval_seconds = interval_seconds
        self.story_active_period_seconds = story_active_period_seconds
        self.cleaner = cleaner
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, name="scheduler", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=10)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.interval_seconds)

    def run_once(self) -> None:
        for post in self.storage.claim_due_posts():
            try:
                self.telegram_api.post_story(post, self.story_active_period_seconds)
                self.storage.mark_published(post.id)
                language = self._language_for(post.telegram_user_id)
                self.telegram_api.send_message(post.chat_id, t(language, "published", id=post.id))
            except Exception as exc:
                logger.exception("Failed to publish scheduled post %s", post.id)
                error = str(exc)
                self.storage.mark_failed(post.id, error)
                language = self._language_for(post.telegram_user_id)
                self.telegram_api.send_message(
                    post.chat_id,
                    t(language, "publish_failed", id=post.id, error=error),
                )
        if self.cleaner:
            self.cleaner.run_once()

    def _language_for(self, telegram_user_id: int) -> str:
        account = self.storage.get_user(telegram_user_id)
        return account.language if account else "en"
