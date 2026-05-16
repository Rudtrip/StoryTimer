from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .i18n import FLAG_TO_LANGUAGE, LANGUAGE_FLAGS, t
from .media import validate_story_media
from .models import MediaType, PostStatus, SessionStep
from .storage import Storage
from .telegram_api import TelegramApi, TelegramApiError
from .timeparse import format_utc_for_user, parse_local_time_for_date


logger = logging.getLogger(__name__)

POPULAR_TIMEZONES = ("Europe/Moscow", "Europe/London", "Europe/Berlin", "America/New_York")
DATE_BUTTON_DAYS = 14


class BotApp:
    def __init__(
        self,
        api: TelegramApi,
        storage: Storage,
        media_dir: Path,
        default_timezone: ZoneInfo,
        onboarding_video_path: Path | None = None,
    ):
        self.api = api
        self.storage = storage
        self.media_dir = media_dir
        self.default_timezone = default_timezone
        self.onboarding_video_path = onboarding_video_path
        self.offset: int | None = None

    def run_polling(self, timeout_seconds: int) -> None:
        logger.info("Bot polling started")
        while True:
            try:
                updates = self.api.get_updates(self.offset, timeout_seconds)
            except Exception:
                logger.exception("Could not fetch updates")
                continue

            for update in updates:
                self.offset = update["update_id"] + 1
                self.handle_update(update)

    def handle_update(self, update: dict[str, Any]) -> None:
        if "business_connection" in update:
            self._handle_business_connection(update["business_connection"])
            return
        callback_query = update.get("callback_query")
        if callback_query:
            self._handle_callback_query(callback_query)
            return
        message = update.get("message")
        if message:
            self._handle_message(message)

    def _handle_callback_query(self, callback_query: dict[str, Any]) -> None:
        self.api.answer_callback_query(callback_query["id"])
        message = callback_query.get("message") or {}
        chat_id = message.get("chat", {}).get("id")
        user_id = callback_query.get("from", {}).get("id", chat_id)
        if chat_id is None or user_id is None:
            return
        self.storage.upsert_user(user_id, chat_id, self.default_timezone.key)

        data = callback_query.get("data", "")
        if data.startswith("lang:"):
            language = data.removeprefix("lang:")
            self.storage.set_language(user_id, language)
            self.api.send_message(
                chat_id,
                t(language, "language_saved"),
                reply_markup=self._main_menu_markup(language),
            )
            return
        if data.startswith("tz:"):
            self._save_timezone(user_id, chat_id, data.removeprefix("tz:"))
            return
        if data.startswith("date:"):
            self._select_schedule_date(user_id, chat_id, data.removeprefix("date:"))
            return
        if data.startswith("cancel:"):
            self._cancel_by_id(user_id, chat_id, data.removeprefix("cancel:"))
            return

        action = data.removeprefix("menu:")
        if action == "schedule":
            self._schedule(user_id, chat_id)
        elif action == "list":
            self._list(user_id, chat_id)
        elif action == "cancel":
            self._cancel_menu(user_id, chat_id)
        elif action == "timezone":
            self._timezone_menu(user_id, chat_id)
        elif action == "language":
            self._language(user_id, chat_id, "")
        elif action == "business":
            self._business_prompt(user_id, chat_id)
        elif action == "abort":
            self.storage.clear_session(user_id)
            self.api.send_message(chat_id, t(self._language_for(user_id), "draft_cancelled"))

    def _handle_business_connection(self, connection: dict[str, Any]) -> None:
        user = connection.get("user") or {}
        user_id = user.get("id")
        chat_id = connection.get("user_chat_id")
        connection_id = connection.get("id")
        is_enabled = connection.get("is_enabled", True)
        can_manage_stories = connection.get("rights", {}).get("can_manage_stories")
        if not user_id or not connection_id:
            return

        account = self.storage.get_user(user_id)
        if account is None and chat_id is not None:
            self.storage.upsert_user(user_id, chat_id, self.default_timezone.key)
            account = self.storage.get_user(user_id)
        if account is None:
            logger.warning("Business connection received before chat is known: %s", connection)
            return

        language = account.language
        if not is_enabled:
            self.storage.set_business_connection(user_id, None)
            self.api.send_message(account.chat_id, t(language, "business_disabled"))
            return

        if can_manage_stories:
            self.storage.set_business_connection(user_id, connection_id)
            self.api.send_message(account.chat_id, t(language, "business_connected"))
        else:
            self.storage.set_business_connection(user_id, None)
            self.api.send_message(account.chat_id, t(language, "business_connected_no_stories"))

    def _handle_message(self, message: dict[str, Any]) -> None:
        chat_id = message["chat"]["id"]
        user_id = message.get("from", {}).get("id", chat_id)
        self.storage.upsert_user(user_id, chat_id, self.default_timezone.key)

        text = (message.get("text") or "").strip()
        button_action = self._button_action(user_id, text)
        if text.startswith("/start"):
            self._start(user_id, chat_id)
        elif text.startswith("/help"):
            self._help(user_id, chat_id)
        elif text.startswith("/language") or text in FLAG_TO_LANGUAGE or button_action == "language":
            self._language(user_id, chat_id, text)
        elif text.startswith("/schedule") or button_action == "schedule":
            self._schedule(user_id, chat_id)
        elif text.startswith("/business"):
            self._business(user_id, chat_id, text)
        elif text.startswith("/timezone") or button_action == "timezone":
            self._timezone(user_id, chat_id, text)
        elif text.startswith("/list") or button_action == "list":
            self._list(user_id, chat_id)
        elif text.startswith("/cancel"):
            self._cancel(user_id, chat_id, text)
        elif button_action == "cancel":
            self._cancel_menu(user_id, chat_id)
        elif button_action == "business":
            self._business_prompt(user_id, chat_id)
        elif text.startswith("/abort") or button_action == "abort":
            self.storage.clear_session(user_id)
            self.api.send_message(chat_id, t(self._language_for(user_id), "draft_cancelled"))
        else:
            self._continue_session(user_id, chat_id, message)

    def _start(self, user_id: int, chat_id: int) -> None:
        language = self._language_for(user_id)
        if self.onboarding_video_path and self.onboarding_video_path.exists():
            self.api.send_video(
                chat_id,
                self.onboarding_video_path,
                t(language, "start"),
                reply_markup=self._main_menu_markup(language),
            )
            return

        self.api.send_message(chat_id, t(language, "start"), reply_markup=self._main_menu_markup(language))

    def _help(self, user_id: int, chat_id: int) -> None:
        self._start(user_id, chat_id)

    def _language(self, user_id: int, chat_id: int, text: str) -> None:
        language = FLAG_TO_LANGUAGE.get(text)
        if language is None:
            self.api.send_message(
                chat_id,
                t(self._language_for(user_id), "language_prompt"),
                reply_markup={
                    "inline_keyboard": [
                        [
                            {"text": f"{LANGUAGE_FLAGS['en']} English", "callback_data": "lang:en"},
                            {"text": f"{LANGUAGE_FLAGS['ru']} Русский", "callback_data": "lang:ru"},
                        ]
                    ]
                },
            )
            return
        self.storage.set_language(user_id, language)
        self.api.send_message(
            chat_id,
            t(language, "language_saved"),
            reply_markup=self._main_menu_markup(language),
        )

    def _schedule(self, user_id: int, chat_id: int) -> None:
        account = self.storage.get_user(user_id)
        language = self._language_for(user_id)
        if not account or not account.business_connection_id:
            self.api.send_message(
                chat_id,
                t(language, "business_missing"),
            )
            return
        self.storage.set_session(user_id, chat_id, SessionStep.WAITING_FOR_MEDIA.value)
        self.api.send_message(chat_id, t(language, "media_prompt"))

    def _business(self, user_id: int, chat_id: int, text: str) -> None:
        language = self._language_for(user_id)
        parts = text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            self._business_prompt(user_id, chat_id)
            return
        self._save_business_connection(user_id, chat_id, parts[1].strip())

    def _timezone(self, user_id: int, chat_id: int, text: str) -> None:
        language = self._language_for(user_id)
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            self._timezone_menu(user_id, chat_id)
            return
        self._save_timezone(user_id, chat_id, parts[1].strip())

    def _save_timezone(self, user_id: int, chat_id: int, timezone_name: str) -> None:
        language = self._language_for(user_id)
        try:
            ZoneInfo(timezone_name)
        except Exception:
            self.api.send_message(chat_id, t(language, "timezone_unknown"))
            return
        self.storage.set_timezone(user_id, timezone_name)
        self.storage.clear_session(user_id)
        self.api.send_message(chat_id, t(language, "timezone_saved", timezone=timezone_name))

    def _timezone_menu(self, user_id: int, chat_id: int) -> None:
        language = self._language_for(user_id)
        self.storage.set_session(user_id, chat_id, SessionStep.WAITING_FOR_TIMEZONE.value)
        keyboard = [[{"text": item, "callback_data": f"tz:{item}"}] for item in POPULAR_TIMEZONES]
        self.api.send_message(
            chat_id,
            t(language, "timezone_prompt"),
            reply_markup={"inline_keyboard": keyboard},
        )

    def _business_prompt(self, user_id: int, chat_id: int) -> None:
        language = self._language_for(user_id)
        self.storage.set_session(user_id, chat_id, SessionStep.WAITING_FOR_BUSINESS.value)
        self.api.send_message(chat_id, t(language, "business_prompt"))

    def _save_business_connection(self, user_id: int, chat_id: int, business_connection_id: str) -> None:
        language = self._language_for(user_id)
        if not business_connection_id.strip():
            self.api.send_message(chat_id, t(language, "business_usage"))
            return
        self.storage.set_business_connection(user_id, business_connection_id.strip())
        self.storage.clear_session(user_id)
        self.api.send_message(chat_id, t(language, "business_saved"))

    def _list(self, user_id: int, chat_id: int) -> None:
        account = self.storage.get_user(user_id)
        timezone_name = account.timezone if account else self.default_timezone.key
        language = account.language if account else self._language_for(user_id)
        user_timezone = ZoneInfo(timezone_name)
        posts = self.storage.list_posts(user_id, statuses=(PostStatus.SCHEDULED, PostStatus.FAILED))
        if not posts:
            self.api.send_message(chat_id, t(language, "list_empty"))
            return
        lines = [t(language, "list_header")]
        for post in posts:
            lines.append(
                t(
                    language,
                    "list_item",
                    id=post.id,
                    status=post.status.value,
                    media_type=post.media_type.value,
                    when=format_utc_for_user(post.scheduled_at_utc, user_timezone),
                )
            )
            if post.last_error:
                lines.append(f"  error: {post.last_error}")
        self.api.send_message(chat_id, "\n".join(lines))

    def _cancel(self, user_id: int, chat_id: int, text: str) -> None:
        language = self._language_for(user_id)
        parts = text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip().isdigit():
            self._cancel_menu(user_id, chat_id)
            return
        self._cancel_by_id(user_id, chat_id, parts[1].strip())

    def _cancel_by_id(self, user_id: int, chat_id: int, raw_post_id: str) -> None:
        language = self._language_for(user_id)
        if not raw_post_id.isdigit():
            self.api.send_message(chat_id, t(language, "cancel_usage"))
            return
        cancelled = self.storage.cancel_post(user_id, int(raw_post_id))
        self.api.send_message(chat_id, t(language, "cancel_success" if cancelled else "cancel_failed"))

    def _cancel_menu(self, user_id: int, chat_id: int) -> None:
        language = self._language_for(user_id)
        account = self.storage.get_user(user_id)
        user_timezone = ZoneInfo(account.timezone if account else self.default_timezone.key)
        posts = self.storage.list_posts(user_id, statuses=(PostStatus.SCHEDULED,))
        if not posts:
            self.api.send_message(chat_id, t(language, "cancel_none"))
            return
        keyboard = [
            [
                {
                    "text": f"#{post.id} {format_utc_for_user(post.scheduled_at_utc, user_timezone)}",
                    "callback_data": f"cancel:{post.id}",
                }
            ]
            for post in posts
        ]
        self.api.send_message(chat_id, t(language, "cancel_choose"), reply_markup={"inline_keyboard": keyboard})

    def _continue_session(self, user_id: int, chat_id: int, message: dict[str, Any]) -> None:
        language = self._language_for(user_id)
        session = self.storage.get_session(user_id)
        if session is None:
            self.api.send_message(chat_id, t(language, "no_session"))
            return

        step = session["step"]
        if step == SessionStep.WAITING_FOR_MEDIA.value:
            self._receive_media(user_id, chat_id, message)
        elif step == SessionStep.WAITING_FOR_DATE.value:
            self._receive_date(user_id, chat_id, message, session)
        elif step == SessionStep.WAITING_FOR_TIME.value:
            self._receive_time(user_id, chat_id, message, session)
        elif step == SessionStep.WAITING_FOR_CAPTION.value:
            self._receive_caption(user_id, chat_id, message, session)
        elif step == SessionStep.WAITING_FOR_BUSINESS.value:
            self._save_business_connection(user_id, chat_id, (message.get("text") or "").strip())
        elif step == SessionStep.WAITING_FOR_TIMEZONE.value:
            self._save_timezone(user_id, chat_id, (message.get("text") or "").strip())

    def _receive_media(self, user_id: int, chat_id: int, message: dict[str, Any]) -> None:
        language = self._language_for(user_id)
        try:
            media_type, file_id, extension = self._extract_media(message)
        except ValueError as exc:
            self.api.send_message(chat_id, t(language, str(exc)))
            return

        destination = self.media_dir / str(user_id) / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{extension}"
        try:
            file_path = self.api.get_file_path(file_id)
            self.api.download_file(file_path, destination)
            validate_story_media(media_type, destination)
        except TelegramApiError as exc:
            self.api.send_message(chat_id, t(language, "media_download_failed", error=str(exc)))
            return
        except ValueError as exc:
            destination.unlink(missing_ok=True)
            self.api.send_message(chat_id, str(exc))
            return

        self.storage.set_session(user_id, chat_id, SessionStep.WAITING_FOR_DATE.value, media_type, destination)
        self._send_date_picker(user_id, chat_id)

    def _send_date_picker(self, user_id: int, chat_id: int) -> None:
        language = self._language_for(user_id)
        account = self.storage.get_user(user_id)
        user_timezone = ZoneInfo(account.timezone if account else self.default_timezone.key)
        today = datetime.now(timezone.utc).astimezone(user_timezone).date()
        keyboard: list[list[dict[str, str]]] = []
        row: list[dict[str, str]] = []
        for index in range(DATE_BUTTON_DAYS):
            current = today + timedelta(days=index)
            label_key = "date_today" if index == 0 else "date_tomorrow" if index == 1 else None
            label = t(language, label_key) if label_key else current.strftime("%d.%m")
            row.append({"text": label, "callback_data": f"date:{current.isoformat()}"})
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        self.api.send_message(
            chat_id,
            t(language, "date_prompt", year=today.year),
            reply_markup={"inline_keyboard": keyboard},
        )

    def _receive_date(self, user_id: int, chat_id: int, message: dict[str, Any], session: Any) -> None:
        text = (message.get("text") or "").strip()
        account = self.storage.get_user(user_id)
        user_timezone = ZoneInfo(account.timezone if account else self.default_timezone.key)
        current_year = datetime.now(timezone.utc).astimezone(user_timezone).year
        try:
            selected_date = datetime.strptime(f"{text}.{current_year}", "%d.%m.%Y").date()
        except ValueError:
            self.api.send_message(chat_id, t(self._language_for(user_id), "date_parse_failed"))
            return
        self._set_selected_date(user_id, chat_id, session, selected_date.isoformat())

    def _select_schedule_date(self, user_id: int, chat_id: int, raw_date: str) -> None:
        session = self.storage.get_session(user_id)
        if session is None or session["step"] != SessionStep.WAITING_FOR_DATE.value:
            self.api.send_message(chat_id, t(self._language_for(user_id), "no_session"))
            return
        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            self.api.send_message(chat_id, t(self._language_for(user_id), "date_parse_failed"))
            return
        self._set_selected_date(user_id, chat_id, session, raw_date)

    def _set_selected_date(self, user_id: int, chat_id: int, session: Any, selected_date: str) -> None:
        self.storage.set_session(
            user_id,
            chat_id,
            SessionStep.WAITING_FOR_TIME.value,
            MediaType(session["media_type"]),
            Path(session["media_path"]),
            selected_date=selected_date,
        )
        self.api.send_message(chat_id, t(self._language_for(user_id), "time_prompt"))

    def _receive_time(self, user_id: int, chat_id: int, message: dict[str, Any], session: Any) -> None:
        language = self._language_for(user_id)
        text = (message.get("text") or "").strip()
        account = self.storage.get_user(user_id)
        timezone_name = account.timezone if account else self.default_timezone.key
        user_timezone = ZoneInfo(timezone_name)
        try:
            selected_date = datetime.strptime(session["selected_date"], "%Y-%m-%d").date()
            scheduled_at = parse_local_time_for_date(text, selected_date, user_timezone)
        except ValueError:
            self.api.send_message(chat_id, t(language, "time_parse_failed"))
            return
        self.storage.set_session(
            user_id,
            chat_id,
            SessionStep.WAITING_FOR_CAPTION.value,
            MediaType(session["media_type"]),
            Path(session["media_path"]),
            scheduled_at,
        )
        self.api.send_message(chat_id, t(language, "caption_prompt"))

    def _receive_caption(self, user_id: int, chat_id: int, message: dict[str, Any], session: Any) -> None:
        text = (message.get("text") or "").strip()
        caption = None if text == "-" else text[:2048]
        account = self.storage.get_user(user_id)
        if not account or not account.business_connection_id:
            self.storage.clear_session(user_id)
            self.api.send_message(chat_id, t(self._language_for(user_id), "business_missing"))
            return
        post_id = self.storage.create_post(
            telegram_user_id=user_id,
            chat_id=chat_id,
            business_connection_id=account.business_connection_id,
            media_type=MediaType(session["media_type"]),
            media_path=Path(session["media_path"]),
            scheduled_at_utc=datetime.fromisoformat(session["scheduled_at_utc"]),
            caption=caption,
        )
        self.storage.clear_session(user_id)
        user_timezone = ZoneInfo(account.timezone)
        when = format_utc_for_user(datetime.fromisoformat(session["scheduled_at_utc"]), user_timezone)
        self.api.send_message(chat_id, t(account.language, "scheduled", id=post_id, when=when))

    def _extract_media(self, message: dict[str, Any]) -> tuple[MediaType, str, str]:
        photos = message.get("photo")
        if photos:
            largest = photos[-1]
            return MediaType.PHOTO, largest["file_id"], "jpg"

        video = message.get("video")
        if video:
            mime_type = video.get("mime_type", "")
            extension = "mp4" if mime_type == "video/mp4" else "video"
            return MediaType.VIDEO, video["file_id"], extension

        raise ValueError("media_required")

    def _language_for(self, user_id: int) -> str:
        account = self.storage.get_user(user_id)
        return account.language if account else "en"

    def _main_menu_markup(self, language: str) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": t(language, "menu_schedule"), "callback_data": "menu:schedule"},
                    {"text": t(language, "menu_list"), "callback_data": "menu:list"},
                ],
                [
                    {"text": t(language, "menu_cancel"), "callback_data": "menu:cancel"},
                    {"text": t(language, "menu_timezone"), "callback_data": "menu:timezone"},
                ],
                [
                    {"text": t(language, "menu_language"), "callback_data": "menu:language"},
                    {"text": t(language, "menu_abort"), "callback_data": "menu:abort"},
                ],
                [
                    {"text": t(language, "menu_business"), "callback_data": "menu:business"},
                ],
            ],
        }

    def _button_action(self, user_id: int, text: str) -> str | None:
        if not text:
            return None
        language = self._language_for(user_id)
        labels = {
            t(language, "menu_schedule"): "schedule",
            t(language, "menu_list"): "list",
            t(language, "menu_cancel"): "cancel",
            t(language, "menu_timezone"): "timezone",
            t(language, "menu_language"): "language",
            t(language, "menu_abort"): "abort",
            t(language, "menu_business"): "business",
        }
        return labels.get(text)
