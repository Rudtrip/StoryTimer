from datetime import datetime, timedelta, timezone

from delayed_publishes.models import MediaType, PostStatus
from delayed_publishes.storage import Storage


def test_create_and_claim_due_post(tmp_path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    storage.migrate()
    storage.upsert_user(1, 100, "Europe/Moscow")
    storage.set_business_connection(1, "bc_1")

    post_id = storage.create_post(
        telegram_user_id=1,
        chat_id=100,
        business_connection_id="bc_1",
        media_type=MediaType.PHOTO,
        media_path=tmp_path / "photo.jpg",
        scheduled_at_utc=datetime.now(timezone.utc) - timedelta(seconds=1),
        caption="hello",
    )

    due = storage.claim_due_posts()

    assert [post.id for post in due] == [post_id]
    assert storage.list_posts(1)[0].status == PostStatus.PUBLISHING


def test_user_language_can_be_saved(tmp_path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    storage.migrate()
    storage.upsert_user(1, 100, "Europe/Moscow")

    assert storage.get_user(1).language == "en"

    storage.set_language(1, "ru")

    assert storage.get_user(1).language == "ru"
