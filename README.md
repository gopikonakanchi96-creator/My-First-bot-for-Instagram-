# AI Facebook and Instagram Quote Bot

This project generates quote content, turns it into image or video posts, and publishes the content to a Facebook Page and the Instagram business account connected to that Page.

The current production path is image quote publishing. It publishes one generated quote image to Facebook first, gets the public Facebook image URL, and then uses that URL to publish the same post to Instagram.

## Current Requirements Implemented

- Publish quote image posts to both Facebook Page and connected Instagram business account.
- Schedule five automatic quote image posts every day.
- Default schedule is `09:00`, `11:00`, `13:00`, `15:00`, and `17:00`.
- Schedule timezone is configurable and currently set to `America/Chicago`.
- Generate a fresh quote for every publish attempt.
- Avoid reusing the same fallback quote when OpenAI is unavailable.
- Use different backgrounds and fonts across posts.
- Keep quote text readable and centered inside the image.
- Keep `Krishna.....` plus a small heart as the signature.
- Show account identity at the bottom of the image:
  - Instagram handle
  - Facebook page name
- Do not print raw `http://` or `https://` URLs inside the generated image.
- Add hashtags to captions based on the quote theme.
- Store generated post records in SQLite.
- Support music-only MP4 quote videos locally and Facebook video publishing.

## Important Runtime Notes

The scheduler only runs while the FastAPI app is running. If the computer is shut down, asleep, or the server process is stopped, scheduled posts will not publish.

Meta Page access tokens must stay valid. If the token expires or loses permissions, Facebook and Instagram publishing will fail until the token is replaced.

OpenAI quote generation currently falls back to local quotes when the OpenAI API returns quota or billing errors. The fallback path is intentional so the bot can still publish when OpenAI is unavailable, but the fallback quote list must be expanded over time to avoid running out of unused quotes.

Instagram video/Reels publishing requires a public MP4 URL. The bot can create MP4 videos and publish them to Facebook, but Instagram Reels may fail when Meta only returns a Facebook-relative video URL instead of a public MP4 URL.

## End-to-End Flow

1. FastAPI starts from `ai_social_bot/app/main.py`.
2. The SQLite database is initialized by `ai_social_bot/app/database/session.py`.
3. The scheduler starts from `ai_social_bot/app/scheduler/scheduler.py`.
4. At each configured schedule time, the scheduler calls `generate_post_now()`.
5. `generate_post_now()` asks OpenAI for a quote through `openai_service.py`.
6. If OpenAI fails and local fallback is enabled, `post_service.py` picks an unused local fallback quote.
7. Duplicate quote checks compare normalized quote text against previous database captions.
8. `image_service.py` creates a 1080x1350 quote image with:
   - selected background
   - selected font
   - centered quote
   - `Krishna.....` signature and small heart
   - bottom account footer
9. `meta_service.py` resolves the Facebook Page token and connected Instagram account.
10. `meta_service.py` uploads the image to the Facebook Page.
11. The Facebook photo URL is reused as the Instagram `image_url`.
12. `meta_service.py` creates and publishes the Instagram media container.
13. `post_service.py` records the result in the `posts` table.

## Project Structure

```text
.
|-- README.md
|-- .env.example
|-- ai_social_bot.db
|-- ai_social_bot/
|   |-- requirements.txt
|   |-- app/
|   |   |-- main.py
|   |   |-- api/
|   |   |   |-- routes.py
|   |   |   `-- dashboard.py
|   |   |-- core/
|   |   |   `-- settings.py
|   |   |-- database/
|   |   |   `-- session.py
|   |   |-- models/
|   |   |   `-- models.py
|   |   |-- prompts/
|   |   |   `-- prompts.py
|   |   |-- scheduler/
|   |   |   `-- scheduler.py
|   |   |-- services/
|   |   |   |-- image_service.py
|   |   |   |-- meta_service.py
|   |   |   |-- openai_service.py
|   |   |   |-- post_service.py
|   |   |   `-- video_service.py
|   |   `-- utils/
|   |       |-- image_utils.py
|   |       `-- logger.py
|   `-- assets/
|       |-- quote_background_*.png
|       |-- nature_background_*.png
|       |-- quote_now_*.jpg
|       `-- quote_video_*.mp4
`-- tools/
    `-- generate_quote_backgrounds.py
```

## Main Files

`ai_social_bot/app/main.py`

Creates the FastAPI application, initializes the database on startup, starts the scheduler, and exposes `/status`.

`ai_social_bot/app/core/settings.py`

Loads configuration from `.env`. This includes OpenAI settings, Meta settings, schedule times, timezone, background settings, and database URL.

`ai_social_bot/app/scheduler/scheduler.py`

Uses APScheduler to register one daily job per configured post time. The default five jobs are:

```text
09:00
11:00
13:00
15:00
17:00
```

Each job calls `generate_post_now()`, which publishes to both Facebook and Instagram.

`ai_social_bot/app/services/post_service.py`

Coordinates the full publish flow:

- quote generation
- local fallback quotes
- duplicate quote prevention
- caption and hashtag generation
- image creation
- Meta publish
- database save

`ai_social_bot/app/services/openai_service.py`

Calls OpenAI chat completions using the configured primary model and fallback models. Current defaults:

```text
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FALLBACKS=gpt-4o-mini,gpt-4.1-mini
```

If all models fail with allowed fallback enabled, `post_service.py` uses local fallback quotes.

`ai_social_bot/app/services/image_service.py`

Creates quote images. It handles font selection, background selection, quote wrapping, text fitting, signature rendering, small heart drawing, and bottom account footer rendering.

`ai_social_bot/app/services/meta_service.py`

Handles Facebook and Instagram publishing through the Meta Graph API:

- looks up the configured Facebook Page
- gets a Page access token
- finds the connected Instagram business account
- publishes Facebook Page photos
- publishes Instagram photo posts
- publishes Facebook videos
- attempts Instagram Reels when a public MP4 URL is available

`ai_social_bot/app/services/video_service.py`

Creates local MP4 quote videos with background music only. The video uses animated quote reveal styles and the same account footer concept.

`ai_social_bot/app/models/models.py`

Defines database tables:

- `posts`
- `images`
- `logs`
- `errors`

The active publish flow mainly writes to `posts`.

## Environment Configuration

Create `.env` from `.env.example` and fill in real values.

```env
OPENAI_API_KEY=your-openai-api-key
META_PAGE_ACCESS_TOKEN=your-facebook-page-access-token
FACEBOOK_PAGE_ID=your-facebook-page-id
FACEBOOK_PAGE_URL=https://www.facebook.com/your-page
FACEBOOK_PAGE_NAME=your-page-name
INSTAGRAM_PROFILE_URL=https://www.instagram.com/your-instagram/
INSTAGRAM_USERNAME=your-instagram
META_GRAPH_API_VERSION=v23.0
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FALLBACKS=gpt-4o-mini,gpt-4.1-mini
ALLOW_LOCAL_QUOTE_FALLBACK=true
USE_NATURE_BACKGROUNDS=true
NATURE_BACKGROUND_DIR=ai_social_bot/assets
POST_TIMES=09:00,11:00,13:00,15:00,17:00
POST_TIME_1=09:00
POST_TIME_2=17:00
SCHEDULER_TIMEZONE=America/Chicago
LOGO_PATH=assets/logo.png
DATABASE_URL=sqlite+aiosqlite:///./ai_social_bot.db
```

`POST_TIMES` is the active schedule setting. `POST_TIME_1` and `POST_TIME_2` remain only for backward compatibility.

## Meta Requirements

The Meta token must have access to the configured Facebook Page and the connected Instagram business account.

Required Page publishing behavior depends on these permissions and connections:

- Facebook Page must be connected to the Instagram business account.
- Token must be able to read `/me/accounts`.
- Token must return the configured `FACEBOOK_PAGE_ID`.
- Token must include or resolve a valid Page access token.
- Page token must be able to publish photos to the Page.
- Connected Instagram account must support content publishing through the Instagram Graph API.

If `/status` works but publishing fails, the issue is usually token expiration, missing permissions, or Instagram not being connected to the selected Facebook Page.

## Installation

Install dependencies:

```powershell
pip install -r ai_social_bot/requirements.txt
```

Run the app:

```powershell
python -m uvicorn ai_social_bot.app.main:app --host 127.0.0.1 --port 8000
```

Check the server:

```text
http://127.0.0.1:8000/status
```

## API Endpoints

`GET /status`

Returns server status and scheduler job details.

`GET /posts`

Returns saved post records from the database.

`POST /generate`

Generates a post image and saves it in the database without publishing it.

`POST /publish-now`

Generates one fresh quote image and publishes it to Facebook and Instagram.

`GET /logs`

Placeholder endpoint for future log expansion.

## Manual Publish Commands

Publish one image quote now:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "import asyncio, json; from ai_social_bot.app.services.post_service import generate_post_now; print(json.dumps(asyncio.run(generate_post_now()), indent=2, ensure_ascii=False, default=str))"
```

Create and publish one video now:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "import asyncio, json; from ai_social_bot.app.services.post_service import generate_video_now; print(json.dumps(asyncio.run(generate_video_now()), indent=2, ensure_ascii=False, default=str))"
```

Check configured schedule times:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "from ai_social_bot.app.scheduler.scheduler import _configured_post_times; print(_configured_post_times())"
```

## Scheduler Behavior

The scheduler registers one job per value in `POST_TIMES`.

Default:

```env
POST_TIMES=09:00,11:00,13:00,15:00,17:00
SCHEDULER_TIMEZONE=America/Chicago
```

The app must already be running at each scheduled time. Missed jobs are not backfilled hours later. Jobs have a short misfire grace window so small delays do not create duplicate posts.

## Quote and Caption Rules

The quote payload contains:

- title
- quote
- explanation
- call to action
- hashtags
- theme
- image prompt

The visible image does not use the title. Captions include:

- quote
- explanation
- hashtags
- account identity lines

The image footer includes the account identity without raw URLs.

## Duplicate Prevention

The bot normalizes quote text before comparing it with older post captions. It removes signature text and punctuation differences, then checks whether a quote has already been used.

When OpenAI is unavailable, local fallback quotes are selected from `LOCAL_QUOTE_PAYLOADS` in `post_service.py`. Already used fallback quotes are skipped. If every local fallback quote has been used, the bot raises an error instead of posting a repeated quote.

## Background and Font Rotation

Image backgrounds are selected from `ai_social_bot/assets`.

Supported background naming patterns include:

```text
nature_background_*.png
quote_background_*.png
```

The image generator avoids immediately reusing the last background. Fonts are selected by theme and background type so posts do not all look the same.

## Video Behavior

The video generator creates portrait MP4 files with:

- one quote
- animated word, chunk, line, or typewriter reveal
- generated background music
- no voice narration
- account footer
- quote signature

Facebook video publishing is supported. Instagram Reels publishing is attempted only when a public MP4 URL is available. If Meta returns only a Facebook-relative video link, Instagram video publishing is skipped with an error message.

## Database

The default database is SQLite:

```env
DATABASE_URL=sqlite+aiosqlite:///./ai_social_bot.db
```

The main `posts` fields are:

- `id`
- `title`
- `caption`
- `hashtags`
- `image_path`
- `posted`
- `created_at`

## Common Problems

OpenAI returns `429 insufficient_quota`

The OpenAI account does not have available quota or billing is not active. The bot can still use local fallback quotes when `ALLOW_LOCAL_QUOTE_FALLBACK=true`.

Meta says token expired

Create a new long-lived Page access token or refresh the token process. The bot cannot publish with an expired token.

Instagram does not publish

Check that the Instagram account is a business or creator account connected to the same Facebook Page configured by `FACEBOOK_PAGE_ID`.

Scheduled posts do not happen

Make sure the FastAPI server is running at the scheduled time and the machine is not sleeping.

Repeated quotes

OpenAI may produce similar content, and local fallback quotes are finite. Add more unique fallback quote payloads in `LOCAL_QUOTE_PAYLOADS` or restore OpenAI quota.

## Verification Checklist

Run syntax checks:

```powershell
python -m py_compile ai_social_bot\app\core\settings.py ai_social_bot\app\scheduler\scheduler.py ai_social_bot\app\services\post_service.py
```

Start the app:

```powershell
python -m uvicorn ai_social_bot.app.main:app --host 127.0.0.1 --port 8000
```

Check scheduler status:

```text
http://127.0.0.1:8000/status
```

Expected scheduler jobs:

```text
post_0900
post_1100
post_1300
post_1500
post_1700
```

Publish a test post with `POST /publish-now` or the manual publish command above.
