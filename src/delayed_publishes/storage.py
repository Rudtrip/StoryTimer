from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .i18n import DEFAULT_LANGUAGE, normalize_language
from .models import MediaType, PostStatus, ScheduledPost, UserAccount


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    return datetime.fromisoformat(raw)


class Storage:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    timezone TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    business_connection_id TEXT,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "users", "language", f"TEXT NOT NULL DEFAULT '{DEFAULT_LANGUAGE}'")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    business_connection_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    media_path TEXT NOT NULL,
                    scheduled_at_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    caption TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at_utc TEXT NOT NULL,
                    published_at_utc TEXT,
                    failed_at_utc TEXT,
                    cancelled_at_utc TEXT,
                    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
                )
                """
            )
            self._ensure_column(conn, "scheduled_posts", "failed_at_utc", "TEXT")
            self._ensure_column(conn, "scheduled_posts", "cancelled_at_utc", "TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    telegram_user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    media_type TEXT,
                    media_path TEXT,
                    selected_date TEXT,
                    scheduled_at_utc TEXT,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "sessions", "selected_date", "TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_posts_due ON scheduled_posts(status, scheduled_at_utc)"
            )

    def upsert_user(self, telegram_user_id: int, chat_id: int, timezone_name: str) -> None:
        now = _utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO users (telegram_user_id, chat_id, timezone, language, created_at_utc, updated_at_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (telegram_user_id, chat_id, timezone_name, DEFAULT_LANGUAGE, now, now),
            )

    def get_user(self, telegram_user_id: int) -> UserAccount | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_user_id = ?",
                (telegram_user_id,),
            ).fetchone()
        if row is None:
            return None
        return UserAccount(
            telegram_user_id=row["telegram_user_id"],
            chat_id=row["chat_id"],
            timezone=row["timezone"],
            language=normalize_language(row["language"]),
            business_connection_id=row["business_connection_id"],
        )

    def set_business_connection(self, telegram_user_id: int, business_connection_id: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET business_connection_id = ?, updated_at_utc = ?
                WHERE telegram_user_id = ?
                """,
                (business_connection_id, _utc_now_iso(), telegram_user_id),
            )

    def set_timezone(self, telegram_user_id: int, timezone_name: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET timezone = ?, updated_at_utc = ?
                WHERE telegram_user_id = ?
                """,
                (timezone_name, _utc_now_iso(), telegram_user_id),
            )

    def set_language(self, telegram_user_id: int, language: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET language = ?, updated_at_utc = ?
                WHERE telegram_user_id = ?
                """,
                (normalize_language(language), _utc_now_iso(), telegram_user_id),
            )

    def set_session(
        self,
        telegram_user_id: int,
        chat_id: int,
        step: str,
        media_type: MediaType | None = None,
        media_path: Path | None = None,
        selected_date: str | None = None,
        scheduled_at_utc: datetime | None = None,
    ) -> None:
        now = _utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    telegram_user_id, chat_id, step, media_type, media_path,
                    selected_date, scheduled_at_utc, created_at_utc, updated_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    step = excluded.step,
                    media_type = excluded.media_type,
                    media_path = excluded.media_path,
                    selected_date = excluded.selected_date,
                    scheduled_at_utc = excluded.scheduled_at_utc,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (
                    telegram_user_id,
                    chat_id,
                    step,
                    media_type.value if media_type else None,
                    str(media_path) if media_path else None,
                    selected_date,
                    scheduled_at_utc.isoformat() if scheduled_at_utc else None,
                    now,
                    now,
                ),
            )

    def get_session(self, telegram_user_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE telegram_user_id = ?",
                (telegram_user_id,),
            ).fetchone()

    def clear_session(self, telegram_user_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE telegram_user_id = ?", (telegram_user_id,))

    def create_post(
        self,
        telegram_user_id: int,
        chat_id: int,
        business_connection_id: str,
        media_type: MediaType,
        media_path: Path,
        scheduled_at_utc: datetime,
        caption: str | None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scheduled_posts (
                    telegram_user_id, chat_id, business_connection_id, media_type,
                    media_path, scheduled_at_utc, status, caption, created_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_user_id,
                    chat_id,
                    business_connection_id,
                    media_type.value,
                    str(media_path),
                    scheduled_at_utc.isoformat(),
                    PostStatus.SCHEDULED.value,
                    caption,
                    _utc_now_iso(),
                ),
            )
            return int(cursor.lastrowid)

    def list_posts(self, telegram_user_id: int, statuses: tuple[PostStatus, ...] | None = None) -> list[ScheduledPost]:
        params: list[str | int] = [telegram_user_id]
        where = "telegram_user_id = ?"
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            where += f" AND status IN ({placeholders})"
            params.extend(status.value for status in statuses)

        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM scheduled_posts WHERE {where} ORDER BY scheduled_at_utc ASC LIMIT 20",
                params,
            ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def cancel_post(self, telegram_user_id: int, post_id: int) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, cancelled_at_utc = ?
                WHERE id = ? AND telegram_user_id = ? AND status = ?
                """,
                (PostStatus.CANCELLED.value, _utc_now_iso(), post_id, telegram_user_id, PostStatus.SCHEDULED.value),
            )
            return cursor.rowcount > 0

    def claim_due_posts(self, limit: int = 10) -> list[ScheduledPost]:
        now = _utc_now_iso()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM scheduled_posts
                WHERE status = ? AND scheduled_at_utc <= ?
                ORDER BY scheduled_at_utc ASC
                LIMIT ?
                """,
                (PostStatus.SCHEDULED.value, now, limit),
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                placeholders = ", ".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE scheduled_posts SET status = ? WHERE id IN ({placeholders})",
                    [PostStatus.PUBLISHING.value, *ids],
                )
        return [self._row_to_post(row) for row in rows]

    def mark_published(self, post_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, published_at_utc = ?, failed_at_utc = NULL, last_error = NULL
                WHERE id = ?
                """,
                (PostStatus.PUBLISHED.value, _utc_now_iso(), post_id),
            )

    def mark_failed(self, post_id: int, error: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, attempts = attempts + 1, failed_at_utc = ?, last_error = ?
                WHERE id = ?
                """,
                (PostStatus.FAILED.value, _utc_now_iso(), error[:1000], post_id),
            )

    def media_cleanup_candidates(
        self,
        published_before: datetime,
        failed_before: datetime,
    ) -> list[ScheduledPost]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM scheduled_posts
                WHERE
                    (status = ? AND published_at_utc IS NOT NULL AND published_at_utc <= ?)
                    OR (status = ? AND failed_at_utc IS NOT NULL AND failed_at_utc <= ?)
                    OR status = ?
                ORDER BY created_at_utc ASC
                LIMIT 100
                """,
                (
                    PostStatus.PUBLISHED.value,
                    published_before.isoformat(),
                    PostStatus.FAILED.value,
                    failed_before.isoformat(),
                    PostStatus.CANCELLED.value,
                ),
            ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def delete_post_record(self, post_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))

    def stale_sessions(self, stale_before: datetime) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE created_at_utc <= ? LIMIT 100",
                (stale_before.isoformat(),),
            ).fetchall()

    def _row_to_post(self, row: sqlite3.Row) -> ScheduledPost:
        return ScheduledPost(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            chat_id=row["chat_id"],
            business_connection_id=row["business_connection_id"],
            media_type=MediaType(row["media_type"]),
            media_path=Path(row["media_path"]),
            scheduled_at_utc=_parse_dt(row["scheduled_at_utc"]) or datetime.now(timezone.utc),
            status=PostStatus(row["status"]),
            caption=row["caption"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            created_at_utc=_parse_dt(row["created_at_utc"]) or datetime.now(timezone.utc),
            published_at_utc=_parse_dt(row["published_at_utc"]),
            failed_at_utc=_parse_dt(row["failed_at_utc"]),
            cancelled_at_utc=_parse_dt(row["cancelled_at_utc"]),
        )

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(row["name"] == column for row in columns):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
