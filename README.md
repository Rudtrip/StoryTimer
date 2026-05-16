# Delayed Publishes

Telegram bot MVP for delayed Telegram Stories publishing.

The service runs as one Python process:

- Telegram Bot API polling for button-first bot flows.
- SQLite for users, drafts, scheduled posts, and statuses.
- Local media storage.
- Background scheduler that publishes due stories through `postStory`.

## Requirements

- Python 3.10+
- Telegram bot token from BotFather
- Telegram Business connection that grants the bot `can_manage_stories`

Telegram Stories publishing is only possible through the official Business flow. A normal bot token is not enough until the user/account grants story-management rights.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=123456:replace_me
DATABASE_PATH=data/delayed_publishes.sqlite3
MEDIA_DIR=data/media
ONBOARDING_VIDEO_PATH=assets/telegram_business_setup.mp4
DEFAULT_TIMEZONE=Europe/Moscow
PUBLISHED_MEDIA_RETENTION_HOURS=24
FAILED_MEDIA_RETENTION_DAYS=7
DRAFT_RETENTION_HOURS=24
```

Run:

```powershell
python -m delayed_publishes
```

## Bot UI

`/start` sends the onboarding video from `ONBOARDING_VIDEO_PATH` and shows an inline menu with all primary actions:

- Schedule story
- My stories
- Cancel story
- Timezone
- Language
- Cancel draft
- Business connection

Slash commands are still supported for compatibility, but the normal user flow uses buttons.

## Scheduling Flow

1. User taps `Schedule story`.
2. Bot asks for a photo or video.
3. Bot downloads the file into `MEDIA_DIR`.
4. User chooses publication date. The year is always the current year.
5. User sends publication time in `HH:MM` format.
6. User sends optional caption or `-`.
7. Scheduler publishes it when `scheduled_at_utc` is due.

Use the `Language` button any time to switch bot messages between English and Russian.

Supported manual date/time formats:

- Date: `20.05`
- Time: `19:30`

## Verification

```powershell
pytest
python -m compileall src tests
```

## Media Retention

The scheduler also runs media cleanup:

- `published` media is deleted after `PUBLISHED_MEDIA_RETENTION_HOURS`.
- `cancelled` media is deleted on the next cleanup run.
- `failed` media is deleted after `FAILED_MEDIA_RETENTION_DAYS`.
- unfinished drafts are deleted after `DRAFT_RETENTION_HOURS`.

## Current Limits

- Only Telegram Stories are implemented.
- Media is stored locally.
- Failed publications are not retried automatically yet.
- Business onboarding is minimal; if the Business update is not captured, use the `Business connection` button and send the id manually.
