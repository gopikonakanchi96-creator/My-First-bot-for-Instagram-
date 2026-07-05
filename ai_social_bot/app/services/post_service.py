from ai_social_bot.app.services.openai_service import generate_text
from ai_social_bot.app.services.image_service import create_quote_image
from ai_social_bot.app.services.meta_service import get_page_context, get_public_account_links, publish_to_meta, publish_video_to_meta
from ai_social_bot.app.services.video_service import create_quote_video
from ai_social_bot.app.prompts.prompts import QUOTE_PROMPT, IMAGE_PROMPTS, QUOTE_SUFFIX
from ai_social_bot.app.core.settings import settings
from ai_social_bot.app.database.session import AsyncSessionLocal
from ai_social_bot.app.models.models import Post
import json
import time
import httpx
import random
from pathlib import Path

PALETTES_BY_THEME = {
    'love': [((120, 30, 50), (220, 90, 120)), ((70, 28, 54), (240, 150, 135))],
    'motivation': [((30, 40, 80), (90, 120, 170)), ((58, 48, 34), (224, 164, 78))],
    'inspiration': [((20, 60, 80), (120, 190, 200)), ((36, 46, 72), (206, 139, 107))],
    'success': [((10, 40, 20), (180, 200, 120)), ((25, 71, 66), (226, 203, 112))],
    'mindfulness': [((40, 50, 60), (140, 170, 160)), ((48, 57, 85), (151, 197, 178))],
    'gratitude': [((60, 30, 10), (200, 150, 100)), ((75, 48, 44), (226, 181, 117))],
}

HASHTAGS_BY_THEME = {
    'love': ['#love', '#romance', '#relationship', '#valentine', '#heart', '#lovequotes', '#couples', '#affection', '#lover', '#kindness', '#loveher', '#lovehim', '#truelove', '#loveyou', '#sweet'],
    'motivation': ['#motivation', '#hustle', '#grind', '#success', '#mindset', '#entrepreneur', '#motivationquotes', '#goals', '#workhard', '#inspire', '#motivated', '#neversettle', '#ambition', '#focus', '#determination'],
    'inspiration': ['#inspiration', '#quotes', '#dailyinspo', '#wisdom', '#lifequotes', '#inspire', '#positivity', '#inspirationalquotes', '#quoteoftheday', '#mindset', '#believe', '#dreambig', '#staypositive', '#hope', '#encouragement'],
    'success': ['#success', '#goals', '#achievement', '#business', '#leadership', '#entrepreneur', '#win', '#ambition', '#motivated', '#grind', '#hustle', '#strategy', '#wealth', '#focus', '#mindset'],
    'mindfulness': ['#mindfulness', '#meditation', '#wellness', '#selfcare', '#peace', '#innerpeace', '#mentalhealth', '#breathe', '#mindful', '#calm', '#awareness', '#presence', '#wellbeing', '#balance', '#slowdown'],
    'gratitude': ['#gratitude', '#thankful', '#blessed', '#appreciation', '#gratitudeattitude', '#grateful', '#mindset', '#positivity', '#thankyou', '#countyourblessings', '#blessings', '#thanks', '#humble', '#gratitudejournal', '#goodvibes'],
}

LOCAL_QUOTE_PAYLOADS = [
    {
        'title': 'Daily Quote',
        'quote': 'Faith makes the next step brighter than the fear ahead.',
        'explanation': 'Trust can make progress possible even before the path feels clear.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#faith', '#dailyquote', '#inspiration', '#positivity', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Peace grows when your heart stops arguing with yesterday.',
        'explanation': 'Letting go of old weight makes room for a steadier today.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#peace', '#mindset', '#dailyquote', '#hope', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Gratitude turns ordinary moments into quiet proof of abundance.',
        'explanation': 'A thankful perspective helps small blessings feel meaningful again.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#gratitude', '#thankful', '#dailyquote', '#positivity', '#quotes'],
        'theme': 'gratitude',
        'image_prompt': IMAGE_PROMPTS[4],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Discipline keeps your dream alive after excitement becomes quiet.',
        'explanation': 'Consistent action protects progress when motivation is not enough.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#motivation', '#discipline', '#success', '#dailyquote', '#quotes'],
        'theme': 'motivation',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Hope becomes stronger when patience teaches the heart to breathe.',
        'explanation': 'Waiting with trust can steady you through uncertain seasons.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#hope', '#patience', '#faith', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Kindness reaches places pride will never know how to enter.',
        'explanation': 'Gentle care can open doors that force and ego cannot.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#kindness', '#healing', '#love', '#dailyquote', '#quotes'],
        'theme': 'love',
        'image_prompt': IMAGE_PROMPTS[1],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Your calm response can become the room’s first deep breath.',
        'explanation': 'Steady presence can change the direction of a difficult moment.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#calm', '#mindfulness', '#peace', '#dailyquote', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Small honest efforts build confidence no applause can replace.',
        'explanation': 'Integrity creates a quiet strength that stays with you.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#effort', '#integrity', '#success', '#dailyquote', '#quotes'],
        'theme': 'success',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Peace begins when every thought no longer needs an answer.',
        'explanation': 'Letting thoughts pass can create space for real rest.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#peace', '#mindfulness', '#mentalhealth', '#dailyquote', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'A grateful heart sees blessings before complaints find words.',
        'explanation': 'Gratitude trains attention to notice what is still good.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#gratitude', '#blessed', '#thankful', '#dailyquote', '#quotes'],
        'theme': 'gratitude',
        'image_prompt': IMAGE_PROMPTS[4],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Courage often whispers before it teaches your feet to move.',
        'explanation': 'Real strength can begin quietly before action becomes visible.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#courage', '#strength', '#motivation', '#dailyquote', '#quotes'],
        'theme': 'motivation',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Love becomes visible when care chooses consistency over performance.',
        'explanation': 'Steady care says more than occasional grand gestures.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#love', '#care', '#relationship', '#dailyquote', '#quotes'],
        'theme': 'love',
        'image_prompt': IMAGE_PROMPTS[1],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Focus protects your dream from noise pretending to matter.',
        'explanation': 'Clear attention keeps progress moving when distractions compete.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#focus', '#dreams', '#success', '#dailyquote', '#quotes'],
        'theme': 'success',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Faith may not stop storms, but it steadies every step.',
        'explanation': 'Belief can help you keep moving when life feels heavy.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#faith', '#strength', '#hope', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
]

def _local_quote_payload(used_quotes: set[str] | None = None) -> dict:
    state_path = Path('ai_social_bot/assets/.last_local_quote')
    last_quote = state_path.read_text(encoding='utf-8').strip() if state_path.exists() else ''
    used_quotes = used_quotes or set()
    choices = [
        payload
        for payload in LOCAL_QUOTE_PAYLOADS
        if payload['quote'] != last_quote and payload['quote'] not in used_quotes
    ]
    if not choices:
        choices = [payload for payload in LOCAL_QUOTE_PAYLOADS if payload['quote'] != last_quote]
    payload = random.choice(choices or LOCAL_QUOTE_PAYLOADS).copy()
    state_path.write_text(payload['quote'], encoding='utf-8')
    payload['hashtags'] = list(payload['hashtags'])
    return payload


def _quote_word_count(quote: str) -> int:
    cleaned = quote.replace(QUOTE_SUFFIX, '').strip()
    return len([word for word in cleaned.split() if word.strip('.,!?;:')])


def _parse_quote_payload(content: str) -> dict:
    try:
        payload = json.loads(content)
    except Exception:
        payload = {
            'title': 'Daily Quote',
            'quote': content,
            'explanation': '',
            'cta': '',
            'hashtags': [],
            'theme': 'inspiration',
            'image_prompt': IMAGE_PROMPTS[0],
        }

    quote = payload.get('quote', '').strip()
    if not quote.endswith(QUOTE_SUFFIX):
        quote = f'{quote} {QUOTE_SUFFIX}'.strip()
    payload['quote'] = quote
    if not 8 <= _quote_word_count(quote) <= 14:
        fallback = _local_quote_payload()
        fallback['hashtags'] = payload.get('hashtags') or fallback['hashtags']
        fallback['theme'] = payload.get('theme') or fallback['theme']
        return _parse_quote_payload(json.dumps(fallback))
    return payload

async def _generate_quote_payload(used_quotes: set[str] | None = None) -> dict:
    try:
        result = await generate_text(QUOTE_PROMPT)
        content = result['choices'][0]['message']['content']
        return _parse_quote_payload(content)
    except httpx.HTTPStatusError as exc:
        if not settings.ALLOW_LOCAL_QUOTE_FALLBACK:
            raise
        print(f"OpenAI quote generation failed; using local fallback quote: {exc.response.status_code}")
        return _parse_quote_payload(json.dumps(_local_quote_payload(used_quotes)))


def _caption_text(payload: dict) -> str:
    theme = payload.get('theme', 'inspiration')
    hashtags = payload.get('hashtags') or HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
    hashtag_text = ' '.join(hashtags)
    parts = [
        payload.get('quote', '').strip(),
        payload.get('explanation', '').strip(),
        hashtag_text.strip(),
    ]
    return '\n\n'.join(part for part in parts if part)


def _video_caption_text(payload: dict) -> str:
    theme = payload.get('theme', 'inspiration')
    hashtags = payload.get('hashtags') or HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
    parts = [
        payload.get('quote', '').strip(),
        ' '.join(hashtags).strip(),
    ]
    return '\n\n'.join(part for part in parts if part)


async def _posted_quote_exists(quote: str) -> bool:
    async with AsyncSessionLocal() as s:
        from sqlalchemy import select

        res = await s.execute(select(Post).where(Post.caption.ilike(f"%{quote}%")))
        return res.scalars().first() is not None


async def _posted_quote_texts() -> set[str]:
    async with AsyncSessionLocal() as s:
        from sqlalchemy import select

        res = await s.execute(select(Post.caption))
        captions = res.scalars().all()
    used = set()
    for payload in LOCAL_QUOTE_PAYLOADS:
        if any(payload['quote'] in (caption or '') for caption in captions):
            used.add(payload['quote'])
    return used


async def _generate_unique_quote_payload(max_attempts: int = 12) -> dict:
    used_quotes = await _posted_quote_texts()
    payload = None
    for _ in range(max_attempts):
        payload = await _generate_quote_payload(used_quotes)
        if not await _posted_quote_exists(payload['quote']):
            return payload
        used_quotes.add(payload['quote'])
    return payload


async def _meta_context_and_links() -> tuple[dict | None, dict]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            context = await get_page_context(client)
        return context, get_public_account_links(context)
    except Exception as exc:
        print(f"Meta account link lookup failed before image creation: {exc}")
        return None, get_public_account_links()


def _create_image(payload: dict, filename_prefix: str, account_links: dict | None = None) -> str:
    theme = payload.get('theme', 'inspiration')
    palettes = PALETTES_BY_THEME.get(theme, PALETTES_BY_THEME['inspiration'])
    palette = random.choice(palettes)
    filename = f"{filename_prefix}_{time.time_ns()}.jpg"
    return create_quote_image(
        payload.get('quote', ''),
        '',
        filename,
        settings.LOGO_PATH,
        palette=palette,
        theme=theme,
        account_links=account_links,
    )


async def generate_and_schedule_post():
    payload = await _generate_quote_payload()

    _, account_links = await _meta_context_and_links()
    image_path = _create_image(payload, 'quote', account_links)

    async with AsyncSessionLocal() as s:
        post = Post(
            title=payload.get('title', ''),
            caption=_caption_text(payload),
            hashtags=','.join(payload.get('hashtags', [])),
            image_path=image_path,
        )
        s.add(post)
        await s.commit()


async def generate_post_now():
    payload = await _generate_quote_payload()
    meta_context, account_links = await _meta_context_and_links()

    image_path = _create_image(payload, 'quote_now', account_links)
    theme = payload.get('theme', 'inspiration')
    hashtags = payload.get('hashtags') or HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
    caption = _caption_text(payload)

    try:
        publish_res = await publish_to_meta(image_path, caption, context=meta_context)
    except Exception as e:
        print(f"Meta publish error: {e}")
        publish_res = {'error': str(e)}

    async with AsyncSessionLocal() as s:
        post = Post(
            title=payload.get('title', ''),
            caption=caption,
            hashtags=','.join(hashtags),
            image_path=image_path,
            posted='error' not in publish_res,
        )
        s.add(post)
        await s.commit()

    return publish_res


async def generate_video_now():
    payload = await _generate_quote_payload()
    meta_context, account_links = await _meta_context_and_links()

    theme = payload.get('theme', 'inspiration')
    hashtags = payload.get('hashtags') or HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
    caption = _video_caption_text(payload)
    filename = f"quote_video_{time.time_ns()}.mp4"
    video_path = create_quote_video(
        payload.get('quote', ''),
        payload.get('explanation', ''),
        f'ai_social_bot/assets/{filename}',
        theme=theme,
        account_links=account_links,
    )

    try:
        publish_res = await publish_video_to_meta(video_path, caption, context=meta_context)
    except Exception as e:
        print(f"Meta video publish error: {e}")
        publish_res = {'error': str(e)}

    async with AsyncSessionLocal() as s:
        post = Post(
            title=payload.get('title', ''),
            caption=caption,
            hashtags=','.join(hashtags),
            image_path=video_path,
            posted='error' not in publish_res,
        )
        s.add(post)
        await s.commit()

    return publish_res
