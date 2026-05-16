from __future__ import annotations

import logging
import signal
import sys

from .bot import BotApp
from .cleanup import RetentionCleaner
from .config import load_settings
from .scheduler import Scheduler
from .storage import Storage
from .telegram_api import TelegramApi


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = load_settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)

    storage = Storage(settings.database_path)
    storage.migrate()

    api = TelegramApi(settings.telegram_bot_token)
    cleaner = RetentionCleaner(
        storage=storage,
        published_media_retention_hours=settings.published_media_retention_hours,
        failed_media_retention_days=settings.failed_media_retention_days,
        draft_retention_hours=settings.draft_retention_hours,
    )
    scheduler = Scheduler(
        storage=storage,
        telegram_api=api,
        interval_seconds=settings.scheduler_interval_seconds,
        story_active_period_seconds=settings.story_active_period_seconds,
        cleaner=cleaner,
    )

    def stop(_signum: int, _frame: object) -> None:
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    scheduler.start()
    BotApp(
        api,
        storage,
        settings.media_dir,
        settings.default_timezone,
        settings.onboarding_video_path,
    ).run_polling(settings.poll_timeout_seconds)
