# AI Facebook, Instagram, and Threads Quote Bot

This project generates quote content, turns it into image or video posts, and publishes the content to a Facebook Page, the Instagram business account connected to that Page, and an optional Threads account.

The current production path is image quote publishing. It publishes one generated quote image to Facebook first, gets the public Facebook image URL, and then uses that URL to publish the same post to Instagram and Threads.

## Current Requirements Implemented

- Publish quote image posts to Facebook Page, connected Instagram business account, and optional Threads account.
- Schedule six automatic quote image posts every day.
- Default schedule is every four hours: `00:00`, `04:00`, `08:00`, `12:00`, `16:00`, and `20:00`.
- Schedule timezone is configurable and currently set to `America/Chicago`.
- Generate a fresh quote for every publish attempt.
- Avoid reusing the same fallback quote when OpenAI is unavailable.
- Use different backgrounds and fonts across posts.
- Keep quote text readable and centered inside the image.
- Keep `Krishna.....` plus a small heart as the signature.
- Show account identity at the bottom of the image:
  - Instagram handle
  - Facebook page name
  - Threads handle when configured
- Do not print raw `http://` or `https://` URLs inside the generated image.
- Add hashtags to captions based on the quote theme.
- Store generated post records in SQLite.
- Support music-only MP4 quote videos locally, Facebook video publishing, and optional Threads video publishing when Meta returns a public video URL.

## Important Runtime Notes

The scheduler only runs while the FastAPI app is running. If the computer is shut down, asleep, or the server process is stopped, scheduled posts will not publish.

Meta Page access tokens must stay valid. If the token expires or loses permissions, Facebook and Instagram publishing will fail until the token is replaced. Threads uses `THREADS_ACCESS_TOKEN`, which must also stay valid.

OpenAI quote generation currently falls back to local quotes when the OpenAI API returns quota or billing errors. The fallback path is intentional so the bot can still publish when OpenAI is unavailable, but the fallback quote list must be expanded over time to avoid running out of unused quotes.

When AI quote generation is unavailable, scheduled image posts can publish a finished quote image from `ai_social_bot/local_quote_images`. Successfully published fallback images are deleted from that folder so they are not reused.

Instagram video/Reels and Threads video publishing require a public MP4 URL. The bot can create MP4 videos and publish them to Facebook, but Instagram and Threads video publishing may fail when Meta only returns a Facebook-relative video URL instead of a public MP4 URL.

## End-to-End Flow

1. FastAPI starts from `ai_social_bot/app/main.py`.
2. The SQLite database is initialized by `ai_social_bot/app/database/session.py`.
3. The scheduler starts from `ai_social_bot/app/scheduler/scheduler.py`.
4. At each configured schedule time, the scheduler calls `generate_post_now()`.
5. `generate_post_now()` asks OpenAI for a quote through `openai_service.py`.
6. If AI quote generation fails and local fallback is enabled, `post_service.py` first tries a ready-made image from `LOCAL_QUOTE_IMAGE_DIR`.
7. If no ready-made image is available, `post_service.py` picks an unused local fallback quote.
8. Duplicate quote checks compare normalized quote text against previous database captions.
9. `image_service.py` creates a 1080x1350 quote image with:
   - selected background
   - selected font
   - centered quote
   - `Krishna.....` signature and small heart
   - bottom account footer
10. `meta_service.py` resolves the Facebook Page token and connected Instagram account.
11. `meta_service.py` uploads the image to the Facebook Page.
12. The Facebook photo URL is reused as the Instagram `image_url`.
13. `meta_service.py` creates and publishes the Instagram media container.
14. If Threads is configured, the same Facebook photo URL is reused as the Threads `image_url`.
15. `post_service.py` records the result in the `posts` table.
16. If a ready-made local quote image was used and publishing succeeded, that source image is deleted.

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
|   |   |   `-- routes.py
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

Uses APScheduler to register one daily job per configured post time. The default six jobs are:

```text
00:00
04:00
08:00
12:00
16:00
20:00
```

Each job calls `generate_post_now()`, which publishes to Facebook, Instagram, and Threads when Threads is configured.

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

Handles Facebook, Instagram, and Threads publishing through the Meta Graph APIs:

- looks up the configured Facebook Page
- gets a Page access token
- finds the connected Instagram business account
- publishes Facebook Page photos
- publishes Instagram photo posts
- publishes Threads image posts
- publishes Facebook videos
- attempts Instagram Reels when a public MP4 URL is available
- attempts Threads video posts when a public MP4 URL is available

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
THREADS_ACCESS_TOKEN=your-threads-access-token
THREADS_PROFILE_URL=https://www.threads.net/@your-threads/
THREADS_USERNAME=your-threads
THREADS_API_VERSION=v1.0
THREADS_APP_ID=your-threads-app-id
THREADS_APP_SECRET=your-threads-app-secret
THREADS_REDIRECT_URI=https://www.example.com/threads/callback
META_GRAPH_API_VERSION=v23.0
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODEL_FALLBACKS=gemini-2.0-flash-lite,gemini-2.0-flash
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FALLBACKS=gpt-4o-mini,gpt-4.1-mini
ALLOW_LOCAL_QUOTE_FALLBACK=true
LOCAL_QUOTE_IMAGE_DIR=ai_social_bot/local_quote_images
LOCAL_QUOTE_IMAGE_CAPTION=Daily inspiration. Krishna.....
DELETE_LOCAL_QUOTE_IMAGE_AFTER_POST=true
USE_NATURE_BACKGROUNDS=true
NATURE_BACKGROUND_DIR=ai_social_bot/assets
POST_TIMES=00:00,04:00,08:00,12:00,16:00,20:00
POST_TIME_1=09:00
POST_TIME_2=17:00
SCHEDULER_TIMEZONE=America/Chicago
ENABLE_IN_APP_SCHEDULER=false
LOGO_PATH=assets/logo.png
DATABASE_URL=sqlite+aiosqlite:///./ai_social_bot.db
```

`POST_TIMES` is the active schedule setting. `POST_TIME_1` and `POST_TIME_2` remain only for backward compatibility.

`ENABLE_IN_APP_SCHEDULER=false` keeps the FastAPI server from also running scheduled posts. Leave it false when using Windows Task Scheduler. Set it to true only when you want the FastAPI process itself to own scheduling.

Place ready-made fallback quote images in `ai_social_bot/local_quote_images`. Supported extensions are `.jpg`, `.jpeg`, `.png`, and `.webp`. The scheduler uses the first filename in sorted order when AI quote generation fails, publishes it with `LOCAL_QUOTE_IMAGE_CAPTION`, and deletes it after a successful image publish when `DELETE_LOCAL_QUOTE_IMAGE_AFTER_POST=true`.

## Meta Requirements

The Meta token must have access to the configured Facebook Page and the connected Instagram business account. Threads publishing uses a separate Threads API token in `THREADS_ACCESS_TOKEN`.

Required Page publishing behavior depends on these permissions and connections:

- Facebook Page must be connected to the Instagram business account.
- Token can be either a user token that can read `/me/accounts` or a Page token for the configured `FACEBOOK_PAGE_ID`.
- Token must return the configured `FACEBOOK_PAGE_ID`.
- Token must include or resolve a valid Page access token.
- Page token must be able to publish photos to the Page.
- Connected Instagram account must support content publishing through the Instagram Graph API.
- Required permissions normally include `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, and `instagram_content_publish`.
- Threads token must belong to the target Threads profile and include Threads publishing access, normally `threads_basic` and `threads_content_publish`.

If `/status` works but publishing fails, the issue is usually token expiration, missing permissions, Instagram not being connected to the selected Facebook Page, or a missing Threads token.

Run a read-only Meta access check before publishing:

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/check_meta_access.py
```

If the script prints `"ready_for_publish": false`, fix the failing Meta check before running `python tools/publish_once.py`.

## Threads Setup

Threads uses a separate Threads API token from the Facebook Page token. The bot already knows how to publish to Threads after `THREADS_ACCESS_TOKEN` is configured.

1. In the Meta Developer dashboard, create or open an app with the Threads API/use case enabled.
2. In the app's basic settings, copy the Threads App ID and Threads App Secret.
3. Add a valid OAuth redirect URI to the Threads app. For a one-person local setup, this can be any URL you control or a temporary callback URL where you can copy the returned `code` query parameter.
4. Add these values to `.env`:

```env
THREADS_APP_ID=your-threads-app-id
THREADS_APP_SECRET=your-threads-app-secret
THREADS_REDIRECT_URI=https://www.example.com/threads/callback
THREADS_PROFILE_URL=https://www.threads.net/@your-threads/
THREADS_USERNAME=your-threads
THREADS_API_VERSION=v1.0
```

5. Generate the authorization URL:

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/threads_setup.py auth-url
```

6. Open the printed URL in a browser, sign in to the target Threads account, approve access, and copy the `code` value from the redirected URL.
7. Exchange the code for a short-lived Threads user token:

```powershell
python tools/threads_setup.py exchange-code --code "paste-code-here"
```

8. Temporarily set `THREADS_ACCESS_TOKEN` in `.env` to the short-lived `access_token` from the response.
9. Exchange it for a long-lived token:

```powershell
python tools/threads_setup.py long-lived
```

10. Replace `THREADS_ACCESS_TOKEN` in `.env` with the long-lived `access_token`.
11. Validate the Threads token:

```powershell
python tools/threads_setup.py me
python tools/check_meta_access.py
```

The Meta access check should print `"threads_ready_for_publish": true`. After that, image publishing through `python tools/publish_once.py` or `POST /publish-now` will publish to Facebook, Instagram, and Threads.

Refresh the long-lived token before it expires:

```powershell
python tools/threads_setup.py refresh
```

## Installation

Install dependencies:

```powershell
pip install -r ai_social_bot/requirements.txt
```

Run the app:

```powershell
python -m uvicorn ai_social_bot.app.main:app --host 127.0.0.1 --port 8000
```

On Windows, you can also start the bot and in-app scheduler with the helper script:

```powershell
.\start_bot.ps1
```

Keep that process running before each scheduled time when using the in-app scheduler. If Windows Task Scheduler is already installed, do not keep a separate in-app scheduler running unless you intentionally want a second scheduler.

For more reliable daily posting on Windows, register one Task Scheduler job per post time. These tasks publish one post and exit, so the API server does not need to stay open all day:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_windows_schedule.ps1
```

The installer reads `POST_TIMES` from `.env` and creates daily tasks named `AI Social Bot Publish 0900`, `AI Social Bot Publish 1100`, and so on. Each task runs:

```powershell
.\run_scheduled_publish.ps1
```

Scheduled publish output is written to `scheduled_publish.log`.

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

Generates one fresh quote image and publishes it to Facebook, Instagram, and Threads when Threads is configured.

`POST /publish-video-now`

Generates one fresh animated quote MP4 and publishes it to Facebook. Instagram Reels and Threads video publishing are attempted when a public MP4 URL is available.

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
python tools/publish_video_once.py
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
POST_TIMES=00:00,04:00,08:00,12:00,16:00,20:00
SCHEDULER_TIMEZONE=America/Chicago
ENABLE_IN_APP_SCHEDULER=false
```

Recommended Windows setup is the Task Scheduler scripts. In that mode, `ENABLE_IN_APP_SCHEDULER` should stay false so only one scheduler creates posts.

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

Facebook video publishing is supported. Instagram Reels and Threads video publishing are attempted only when a public MP4 URL is available. If Meta returns only a Facebook-relative video link, Instagram and Threads video publishing are skipped with an error message.

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

The OpenAI account does not have available quota or billing is not active. If `GEMINI_API_KEY` is configured, the bot tries Gemini before OpenAI. The bot can still use local fallback quotes when `ALLOW_LOCAL_QUOTE_FALLBACK=true`.

Meta says token expired

Create a new long-lived Page access token or refresh the token process. The bot cannot publish with an expired token.

Instagram does not publish

Check that the Instagram account is a business or creator account connected to the same Facebook Page configured by `FACEBOOK_PAGE_ID`.

Scheduled posts do not happen

If you use the in-app scheduler, make sure the FastAPI server is running at the scheduled time and the machine is not sleeping. On Windows, run `.\start_bot.ps1` from the project root before the first scheduled post.

For a stronger Windows setup, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_windows_schedule.ps1
```

Then confirm the tasks are ready in Task Scheduler or with:

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like 'AI Social Bot Publish*' }
```

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
