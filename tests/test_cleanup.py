from datetime import datetime, timedelta, timezone

from delayed_publishes.cleanup import RetentionCleaner
from delayed_publishes.models import MediaType, SessionStep
from delayed_publishes.storage import Storage


def test_cleanup_deletes_cancelled_post_media(tmp_path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    storage.migrate()
    storage.upsert_user(1, 100, "Europe/Moscow")
    storage.set_business_connection(1, "bc_1")
    media_path = tmp_path / "photo.jpg"
    media_path.write_bytes(b"x")
    post_id = storage.create_post(
        telegram_user_id=1,
        chat_id=100,
        business_connection_id="bc_1",
        media_type=MediaType.PHOTO,
        media_path=media_path,
        scheduled_at_utc=datetime.now(timezone.utc) + timedelta(days=1),
        caption=None,
    )
    storage.cancel_post(1, post_id)

    RetentionCleaner(storage, 24, 7, 24).run_once()

    assert not media_path.exists()
    assert storage.list_posts(1) == []


def test_cleanup_deletes_stale_draft_media(tmp_path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    storage.migrate()
    media_path = tmp_path / "draft.jpg"
    media_path.write_bytes(b"x")
    storage.set_session(
        telegram_user_id=1,
        chat_id=100,
        step=SessionStep.WAITING_FOR_DATE.value,
        media_type=MediaType.PHOTO,
        media_path=media_path,
    )
    with storage.connect() as conn:
        conn.execute(
            "UPDATE sessions SET created_at_utc = ? WHERE telegram_user_id = ?",
            ((datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(), 1),
        )

    RetentionCleaner(storage, 24, 7, 24).run_once()

    assert not media_path.exists()
    assert storage.get_session(1) is None
