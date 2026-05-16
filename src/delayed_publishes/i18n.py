from __future__ import annotations

from typing import Any


DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "ru"}

LANGUAGE_FLAGS = {
    "ru": "🇷🇺",
    "en": "🇬🇧",
}

FLAG_TO_LANGUAGE = {flag: language for language, flag in LANGUAGE_FLAGS.items()}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "business_connected": "Telegram Business connected. I can publish stories for this account.",
        "business_connected_no_stories": "Telegram Business connected, but story management is not allowed. Open Telegram Business chat bot settings and enable story permissions for this bot.",
        "business_disabled": "Telegram Business connection was disabled. Connect the bot again before scheduling stories.",
        "business_missing": "I need a Telegram Business connection before scheduling stories. Use the Business connection button below, or reconnect this bot in Telegram Business settings.",
        "business_prompt": "Send business_connection_id, or reconnect this bot in Telegram Business settings and grant story permissions.",
        "business_saved": "Business connection saved. You can use /schedule now.",
        "business_usage": "Usage: /business <business_connection_id>",
        "cancel_failed": "Could not cancel this story.",
        "cancel_success": "Story cancelled.",
        "cancel_choose": "Choose a story to cancel:",
        "cancel_none": "No scheduled stories to cancel.",
        "cancel_usage": "Usage: /cancel <id>",
        "caption_prompt": "Optional caption? Send text, or send '-' to publish without caption.",
        "date_parse_failed": "Could not parse date. Choose a date with buttons or send it as DD.MM.",
        "date_prompt": "Media saved. Choose publication date. The year is fixed to {year}.",
        "date_today": "Today",
        "date_tomorrow": "Tomorrow",
        "draft_cancelled": "Draft cancelled.",
        "language_prompt": "Choose language:\n🇬🇧 English\n🇷🇺 Русский",
        "language_saved": "Language saved: English.",
        "list_empty": "No scheduled or failed stories.",
        "list_header": "Your stories:",
        "list_item": "#{id} {status} {media_type} at {when}",
        "menu_abort": "Cancel draft",
        "menu_business": "Business connection",
        "menu_cancel": "Cancel story",
        "menu_language": "Language",
        "menu_list": "My stories",
        "menu_schedule": "Schedule story",
        "menu_timezone": "Timezone",
        "media_download_failed": "Could not download media: {error}",
        "media_prompt": "Send one photo or video for the story. Use the Cancel draft button to cancel.",
        "media_required": "Please send a photo or video file for the story.",
        "media_saved": "Media saved.",
        "no_session": "Use the Schedule story button to create a delayed story.",
        "published": "Story #{id} published.",
        "publish_failed": "Could not publish story #{id}.\nReason: {error}",
        "photo_too_large": "Photo is too large for Telegram Stories. Maximum: 10 MB.",
        "scheduled": "Story #{id} scheduled for {when}.",
        "start": "Delayed Telegram Stories bot.\n\nWatch the video first: it shows how to connect this bot in Telegram Business and allow story publishing.\n\nAfter connecting:\n1. Return here.\n2. Tap Schedule story.\n3. Send a photo or video and choose the publication time.\n\nIf the connection was not captured automatically, tap Business connection.\n\nNote: Telegram Stories publishing works only for Telegram Premium accounts with Telegram Business features enabled.",
        "time_parse_failed": "Could not parse time or it is in the past. Example: 19:30",
        "time_prompt": "Now send publication time in HH:MM format, for example 19:30.",
        "timezone_saved": "Timezone saved: {timezone}",
        "timezone_prompt": "Choose timezone or send it manually, for example Europe/Moscow.",
        "timezone_unknown": "Unknown timezone. Example: /timezone Europe/Moscow",
        "timezone_usage": "Usage: /timezone Europe/Moscow",
        "video_too_large": "Video is too large for Telegram Stories. Maximum: 30 MB.",
    },
    "ru": {
        "business_connected": "Telegram Business подключен. Я могу публиковать stories для этого аккаунта.",
        "business_connected_no_stories": "Telegram Business подключен, но право на управление stories не выдано. Открой настройки чат-бота в Telegram Business и включи права на stories для этого бота.",
        "business_disabled": "Telegram Business connection отключен. Перед планированием stories подключи бота заново.",
        "business_missing": "Перед отложенной публикацией нужен Telegram Business connection. Используй кнопку Business connection ниже или переподключи бота в настройках Telegram Business.",
        "business_prompt": "Отправь business_connection_id или переподключи бота в настройках Telegram Business и выдай права на stories.",
        "business_saved": "Business connection сохранен. Теперь можно использовать /schedule.",
        "business_usage": "Формат: /business <business_connection_id>",
        "cancel_failed": "Не удалось отменить эту story.",
        "cancel_success": "Story отменена.",
        "cancel_choose": "Выбери story для отмены:",
        "cancel_none": "Нет запланированных stories для отмены.",
        "cancel_usage": "Формат: /cancel <id>",
        "caption_prompt": "Добавить подпись? Отправь текст или '-' для публикации без подписи.",
        "date_parse_failed": "Не получилось распознать дату. Выбери дату кнопкой или отправь ее в формате ДД.ММ.",
        "date_prompt": "Медиа сохранено. Выбери дату публикации. Год всегда текущий: {year}.",
        "date_today": "Сегодня",
        "date_tomorrow": "Завтра",
        "draft_cancelled": "Черновик отменен.",
        "language_prompt": "Выбери язык:\n🇬🇧 English\n🇷🇺 Русский",
        "language_saved": "Язык сохранен: русский.",
        "list_empty": "Нет запланированных или упавших stories.",
        "list_header": "Твои stories:",
        "list_item": "#{id} {status} {media_type} на {when}",
        "menu_abort": "Отменить черновик",
        "menu_business": "Business connection",
        "menu_cancel": "Отменить story",
        "menu_language": "Язык",
        "menu_list": "Мои stories",
        "menu_schedule": "Запланировать story",
        "menu_timezone": "Таймзона",
        "media_download_failed": "Не удалось скачать медиа: {error}",
        "media_prompt": "Отправь одно фото или видео для story. Кнопка Отменить черновик отменит черновик.",
        "media_required": "Отправь фото или видео для story.",
        "media_saved": "Медиа сохранено.",
        "no_session": "Используй кнопку Запланировать story, чтобы создать отложенную story.",
        "published": "Story #{id} опубликована.",
        "publish_failed": "Не удалось опубликовать story #{id}.\nПричина: {error}",
        "photo_too_large": "Фото слишком большое для Telegram Stories. Максимум: 10 MB.",
        "scheduled": "Story #{id} запланирована на {when}.",
        "start": "Бот для отложенных Telegram Stories.\n\nСначала посмотри видео: в нем показано, как подключить этого бота в Telegram Business и разрешить публикацию stories.\n\nПосле подключения:\n1. Вернись сюда.\n2. Нажми Запланировать story.\n3. Отправь фото или видео и выбери время публикации.\n\nЕсли connection не поймался автоматически, нажми Business connection.\n\nВажно: публикация Telegram Stories работает только для Telegram Premium аккаунтов с включенными Telegram Business функциями.",
        "time_parse_failed": "Не получилось распознать время или оно уже прошло. Пример: 19:30",
        "time_prompt": "Теперь отправь время публикации в формате ЧЧ:ММ, например 19:30.",
        "timezone_saved": "Таймзона сохранена: {timezone}",
        "timezone_prompt": "Выбери таймзону или отправь ее вручную, например Europe/Moscow.",
        "timezone_unknown": "Неизвестная таймзона. Пример: /timezone Europe/Moscow",
        "timezone_usage": "Формат: /timezone Europe/Moscow",
        "video_too_large": "Видео слишком большое для Telegram Stories. Максимум: 30 MB.",
    },
}


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(language: str | None, key: str, **kwargs: Any) -> str:
    normalized = normalize_language(language)
    template = TRANSLATIONS[normalized].get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    return template.format(**kwargs)
