from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

import requests

from .models import MediaType, ScheduledPost


class TelegramApiError(RuntimeError):
    pass


class TelegramApi:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"

    def call(self, method: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
        response = requests.post(f"{self.base_url}/{method}", json=payload or {}, timeout=timeout)
        return self._decode_response(response)

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query", "business_connection"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = self.call("getUpdates", payload=payload, timeout=timeout + 5)
        return result["result"]

    def send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        self.call(
            "sendMessage",
            payload,
        )

    def send_video(
        self,
        chat_id: int,
        video_path: Path,
        caption: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "caption": caption,
        }
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup)

        mime_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        with video_path.open("rb") as file_handle:
            response = requests.post(
                f"{self.base_url}/sendVideo",
                data=payload,
                files={"video": (video_path.name, file_handle, mime_type)},
                timeout=120,
            )
        self._decode_response(response)

    def answer_callback_query(self, callback_query_id: str) -> None:
        self.call("answerCallbackQuery", {"callback_query_id": callback_query_id})

    def get_file_path(self, file_id: str) -> str:
        result = self.call("getFile", {"file_id": file_id})
        return result["result"]["file_path"]

    def download_file(self, file_path: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(f"{self.file_base_url}/{file_path}", timeout=60)
        if response.status_code >= 400:
            raise TelegramApiError(f"download failed: HTTP {response.status_code}")
        destination.write_bytes(response.content)

    def post_story(self, post: ScheduledPost, active_period_seconds: int) -> None:
        content_type = "photo" if post.media_type == MediaType.PHOTO else "video"
        content_payload: dict[str, Any] = {
            "type": content_type,
            content_type: "attach://story_media",
        }
        payload: dict[str, Any] = {
            "business_connection_id": post.business_connection_id,
            "content": json.dumps(content_payload),
            "active_period": active_period_seconds,
        }
        if post.caption:
            payload["caption"] = post.caption

        mime_type = mimetypes.guess_type(post.media_path.name)[0] or "application/octet-stream"
        with post.media_path.open("rb") as file_handle:
            files = {"story_media": (post.media_path.name, file_handle, mime_type)}
            response = requests.post(
                f"{self.base_url}/postStory",
                data=payload,
                files=files,
                timeout=120,
            )
        self._decode_response(response)

    def _decode_response(self, response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise TelegramApiError(f"Telegram returned non-JSON HTTP {response.status_code}") from exc
        if not data.get("ok"):
            description = data.get("description", "unknown Telegram API error")
            raise TelegramApiError(description)
        return data
