from ai_social_bot.app.services.openai_service import generate_image, generate_text
from ai_social_bot.app.services.image_service import create_quote_image
from ai_social_bot.app.services.meta_service import get_page_context, get_public_account_links, publish_to_meta, publish_video_to_meta
from ai_social_bot.app.services.video_service import create_quote_video
from ai_social_bot.app.prompts.prompts import QUOTE_PROMPT, IMAGE_PROMPTS, QUOTE_SUFFIX
from ai_social_bot.app.core.settings import settings
from ai_social_bot.app.database.session import AsyncSessionLocal
from ai_social_bot.app.models.models import Post
from PIL import Image, ImageFilter, ImageOps
import base64
import json
import time
import httpx
import random
from pathlib import Path

LOCAL_QUOTE_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_THEMES = {'love', 'motivation', 'inspiration', 'success', 'mindfulness', 'gratitude'}
WEAK_CAPTION_PHRASES = {
    'inner light',
    'radiance',
    'journey',
    'embrace',
    'shine bright',
    'true contentment',
    'external validation',
    'positive vibes',
    'inner garden',
    'the world awaits',
    'authentic glow',
}

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
    {
        'title': 'Daily Quote',
        'quote': 'Every quiet beginning can become a powerful turning point.',
        'explanation': 'Small starts can carry more strength than they first reveal.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#newbeginnings', '#inspiration', '#growth', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Patience turns waiting into wisdom when the heart stays steady.',
        'explanation': 'A steady heart can learn even while life is still unfolding.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#patience', '#wisdom', '#peace', '#dailyquote', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'A focused heart makes progress feel possible again.',
        'explanation': 'Clarity can restore momentum when distractions feel heavy.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#focus', '#progress', '#motivation', '#dailyquote', '#quotes'],
        'theme': 'motivation',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Grace meets you gently where strength feels empty.',
        'explanation': 'Even tired seasons can hold quiet support and renewal.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#grace', '#faith', '#hope', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Your next step matters more than yesterday’s delay.',
        'explanation': 'Progress begins again the moment you choose to move.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#progress', '#motivation', '#mindset', '#dailyquote', '#quotes'],
        'theme': 'motivation',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'A peaceful heart can hear answers noise hides.',
        'explanation': 'Stillness often reveals what pressure keeps hidden.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#peace', '#stillness', '#mindfulness', '#dailyquote', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Consistency makes small courage look like lasting change.',
        'explanation': 'Repeated brave choices slowly build a stronger life.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#consistency', '#courage', '#success', '#dailyquote', '#quotes'],
        'theme': 'success',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Gratitude opens windows the worried mind keeps closed.',
        'explanation': 'Thankfulness can help you notice light beside uncertainty.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#gratitude', '#thankful', '#positivity', '#dailyquote', '#quotes'],
        'theme': 'gratitude',
        'image_prompt': IMAGE_PROMPTS[4],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Kindness gives strength a softer way to speak.',
        'explanation': 'Gentleness can carry power without becoming harsh.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#kindness', '#strength', '#love', '#dailyquote', '#quotes'],
        'theme': 'love',
        'image_prompt': IMAGE_PROMPTS[1],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Hope rises quietly when you choose not to quit.',
        'explanation': 'Continuing with faith can invite courage back into the day.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#hope', '#faith', '#nevergiveup', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Trust grows stronger when your steps stay honest.',
        'explanation': 'A sincere path can steady you even when results take time.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#trust', '#faith', '#honesty', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Quiet effort becomes strength before the world notices.',
        'explanation': 'Private consistency often builds the confidence people later admire.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#effort', '#strength', '#motivation', '#dailyquote', '#quotes'],
        'theme': 'motivation',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Peace returns when you stop carrying every fear.',
        'explanation': 'Letting go of what you cannot control makes space for calm.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#peace', '#calm', '#mindfulness', '#dailyquote', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Gratitude makes today feel rich before tomorrow arrives.',
        'explanation': 'Thankfulness helps the present moment feel full enough.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#gratitude', '#thankful', '#blessed', '#dailyquote', '#quotes'],
        'theme': 'gratitude',
        'image_prompt': IMAGE_PROMPTS[4],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Love speaks clearly when patience chooses to stay.',
        'explanation': 'Steady patience can show care more deeply than words alone.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#love', '#patience', '#care', '#dailyquote', '#quotes'],
        'theme': 'love',
        'image_prompt': IMAGE_PROMPTS[1],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Success follows the habits your excuses could not stop.',
        'explanation': 'Reliable habits move you forward when excuses lose their power.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#success', '#habits', '#discipline', '#dailyquote', '#quotes'],
        'theme': 'success',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Faith steadies the heart before answers become visible.',
        'explanation': 'Belief can keep you grounded while life is still unfolding.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#faith', '#hope', '#inspiration', '#dailyquote', '#quotes'],
        'theme': 'inspiration',
        'image_prompt': IMAGE_PROMPTS[0],
    },
    {
        'title': 'Daily Quote',
        'quote': 'A calm mind can find doors pressure overlooks.',
        'explanation': 'Stillness often reveals choices that stress keeps hidden.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#calm', '#mindfulness', '#clarity', '#dailyquote', '#quotes'],
        'theme': 'mindfulness',
        'image_prompt': IMAGE_PROMPTS[3],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Small progress is still proof that courage moved.',
        'explanation': 'Every honest step counts, even when the distance feels long.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#progress', '#courage', '#motivation', '#dailyquote', '#quotes'],
        'theme': 'motivation',
        'image_prompt': IMAGE_PROMPTS[2],
    },
    {
        'title': 'Daily Quote',
        'quote': 'Kind words can heal rooms silence left heavy.',
        'explanation': 'Gentle speech can bring light where tension has settled.',
        'cta': 'Share this reminder today.',
        'hashtags': ['#kindness', '#healing', '#love', '#dailyquote', '#quotes'],
        'theme': 'love',
        'image_prompt': IMAGE_PROMPTS[1],
    },
]


def _quote_key(text: str) -> str:
    normalized = (
        text.lower()
        .replace('â€™', "'")
        .replace('’', "'")
        .replace('“', '"')
        .replace('”', '"')
    )
    normalized = _quote_without_suffix(normalized)
    return ' '.join(word.strip('.,!?;:"\'()[]{}') for word in normalized.split())


def _quote_without_suffix(quote: str) -> str:
    quote = (
        quote.strip()
        .replace('â\x9d¤ï¸\x8f', '❤️')
        .replace('â¤ï¸', '❤️')
        .replace('â™¥', '♥')
    )
    marker = 'krishna.....'
    index = quote.lower().find(marker)
    if index != -1:
        quote = quote[:index].strip()
    return quote


def _with_clean_quote_suffix(quote: str) -> str:
    quote = _quote_without_suffix(quote)
    return f'{quote} {QUOTE_SUFFIX}'.strip()


def _local_quote_payload(used_quotes: set[str] | None = None) -> dict:
    state_path = Path('ai_social_bot/assets/.last_local_quote')
    last_quote = state_path.read_text(encoding='utf-8').strip() if state_path.exists() else ''
    used_quotes = used_quotes or set()
    used_keys = {_quote_key(quote) for quote in used_quotes}
    last_key = _quote_key(last_quote)
    choices = [
        payload
        for payload in LOCAL_QUOTE_PAYLOADS
        if _quote_key(payload['quote']) != last_key and _quote_key(payload['quote']) not in used_keys
    ]
    if not choices:
        raise RuntimeError(
            'All local fallback quotes have already been used. '
            'Add more fallback quotes or restore OpenAI quota before publishing again.'
        )
    payload = random.choice(choices or LOCAL_QUOTE_PAYLOADS).copy()
    state_path.write_text(payload['quote'], encoding='utf-8')
    payload['hashtags'] = list(payload['hashtags'])
    return payload


def _quote_word_count(quote: str) -> int:
    cleaned = _quote_without_suffix(quote)
    return len([word for word in cleaned.split() if word.strip('.,!?;:')])


def _normalize_hashtags(payload: dict) -> list[str]:
    theme = payload.get('theme', 'inspiration')
    fallback = HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
    raw_hashtags = payload.get('hashtags') or fallback
    normalized = []
    for tag in raw_hashtags:
        tag = str(tag).strip()
        if not tag:
            continue
        tag = tag.replace(' ', '')
        if not tag.startswith('#'):
            tag = f'#{tag}'
        normalized.append(tag)
    normalized = list(dict.fromkeys(normalized))
    if len(normalized) < 15:
        normalized.extend(tag for tag in fallback if tag not in normalized)
    return normalized[:15]


def _validate_generated_payload(payload: dict) -> None:
    quote = payload.get('quote', '').strip()
    explanation = payload.get('explanation', '').strip()
    theme = payload.get('theme', 'inspiration')
    hashtags = payload.get('hashtags') or []

    if theme not in ALLOWED_THEMES:
        raise ValueError(f'LLM returned unsupported theme: {theme}')
    if not 8 <= _quote_word_count(quote) <= 14:
        raise ValueError(f'LLM quote word count is outside 8-14 words: {quote}')
    if quote.lower().count('krishna.....') != 1:
        raise ValueError(f'LLM quote has malformed signature: {quote}')
    if len(explanation.split()) > 28:
        raise ValueError(f'LLM explanation is too long: {explanation}')
    if len(hashtags) < 15:
        raise ValueError('LLM returned too few hashtags')

    caption_key = f'{quote} {explanation}'.lower()
    weak_matches = [phrase for phrase in WEAK_CAPTION_PHRASES if phrase in caption_key]
    if weak_matches:
        raise ValueError(f'LLM caption used weak/generic phrase(s): {", ".join(weak_matches)}')


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

    quote = _with_clean_quote_suffix(payload.get('quote', ''))
    payload['quote'] = quote
    payload['theme'] = str(payload.get('theme') or 'inspiration').strip().lower()
    payload['hashtags'] = _normalize_hashtags(payload)
    _validate_generated_payload(payload)
    return payload

async def _generate_quote_payload(used_quotes: set[str] | None = None) -> dict:
    last_validation_error = None
    for _ in range(4):
        try:
            result = await generate_text(QUOTE_PROMPT)
            content = result['choices'][0]['message']['content']
            return _parse_quote_payload(content)
        except ValueError as exc:
            last_validation_error = exc
            print(f"LLM quote quality check failed; retrying: {exc}")
        except httpx.HTTPStatusError as exc:
            if not settings.ALLOW_LOCAL_QUOTE_FALLBACK:
                raise
            print(f"LLM quote generation failed; using local fallback quote: {exc.response.status_code}")
            return _parse_quote_payload(json.dumps(_local_quote_payload(used_quotes)))
    if not settings.ALLOW_LOCAL_QUOTE_FALLBACK:
        raise last_validation_error or RuntimeError('LLM quote quality checks failed')
    print(f"LLM quote quality checks failed; using local fallback quote: {last_validation_error}")
    return _parse_quote_payload(json.dumps(_local_quote_payload(used_quotes)))


async def _try_generate_ai_quote_payload() -> dict | None:
    try:
        result = await generate_text(QUOTE_PROMPT)
    except Exception as exc:
        if not settings.ALLOW_LOCAL_QUOTE_FALLBACK:
            raise
        print(f"AI quote generation failed; checking local quote image fallback: {exc}")
        return None
    content = result['choices'][0]['message']['content']
    return _parse_quote_payload(content)


async def _try_generate_unique_ai_quote_payload(max_attempts: int = 12) -> dict | None:
    payload = None
    for _ in range(max_attempts):
        try:
            payload = await _try_generate_ai_quote_payload()
        except ValueError as exc:
            print(f"LLM quote quality check failed; retrying: {exc}")
            continue
        if payload is None:
            return None
        if not await _posted_quote_exists(payload['quote']):
            return payload
    return payload


def _local_quote_images() -> list[Path]:
    image_dir = Path(settings.LOCAL_QUOTE_IMAGE_DIR)
    if not image_dir.exists():
        return []
    return sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in LOCAL_QUOTE_IMAGE_EXTENSIONS
    )


def _pick_local_quote_image() -> Path | None:
    images = _local_quote_images()
    if not images:
        return None
    return images[0]


def _delete_local_quote_image(image_path: str) -> None:
    if not settings.DELETE_LOCAL_QUOTE_IMAGE_AFTER_POST:
        return

    path = Path(image_path)
    fallback_dir = Path(settings.LOCAL_QUOTE_IMAGE_DIR).resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(fallback_dir)
    except ValueError:
        print(f"Skipping delete for image outside local quote folder: {path}")
        return

    if resolved_path.exists():
        resolved_path.unlink()
        print(f"Deleted published local quote image: {resolved_path}")


def _prepare_local_quote_image_for_publish(image_path: str) -> str:
    path = Path(image_path)
    if path.suffix.lower() in {'.jpg', '.jpeg'}:
        return image_path

    output_dir = Path('ai_social_bot/assets')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'local_quote_publish_{time.time_ns()}.jpg'
    with Image.open(path) as image:
        image.convert('RGB').save(output_path, 'JPEG', quality=95)
    return str(output_path)


def _delete_generated_publish_image(image_path: str, original_path: str) -> None:
    if image_path == original_path:
        return

    path = Path(image_path)
    assets_dir = Path('ai_social_bot/assets').resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(assets_dir)
    except ValueError:
        return

    if resolved_path.exists():
        resolved_path.unlink()


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

        res = await s.execute(select(Post.caption))
        captions = res.scalars().all()
    quote_key = _quote_key(quote)
    return any(quote_key and quote_key in _quote_key(caption or '') for caption in captions)


async def _posted_quote_texts() -> set[str]:
    async with AsyncSessionLocal() as s:
        from sqlalchemy import select

        res = await s.execute(select(Post.caption))
        captions = res.scalars().all()
    used = set()
    for payload in LOCAL_QUOTE_PAYLOADS:
        payload_key = _quote_key(payload['quote'])
        if any(payload_key and payload_key in _quote_key(caption or '') for caption in captions):
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


def _create_image(
    payload: dict,
    filename_prefix: str,
    account_links: dict | None = None,
    use_stored_backgrounds: bool = True,
) -> str:
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
        use_stored_backgrounds=use_stored_backgrounds,
    )


def _ai_quote_image_prompt(payload: dict, account_links: dict | None = None) -> str:
    quote = payload.get('quote', '').strip()
    theme = payload.get('theme', 'inspiration')
    style = payload.get('style', '').strip()
    visual_prompt = payload.get('image_prompt', '').strip()
    footer_lines = []
    if account_links:
        instagram_username = account_links.get('instagram_username')
        facebook_name = account_links.get('facebook_name')
        threads_username = account_links.get('threads_username')
        if instagram_username:
            footer_lines.append(f'@{instagram_username}')
        if facebook_name:
            footer_lines.append(f'Facebook: {facebook_name}')
        if threads_username:
            footer_lines.append(f'Threads: @{threads_username}')

    footer_instruction = ''
    if footer_lines:
        footer_instruction = f"Add a small footer with exactly this account text: {' | '.join(footer_lines)}."

    return f"""
Create a complete premium social-media quote poster as a finished raster image.
Do not use, copy, or imitate any stored/local background image.
Canvas should be portrait 4:5 safe, with generous margins so it can be fitted to 1080x1350.
Theme: {theme}. Style: {style or 'cinematic editorial'}.
Visual concept: {visual_prompt or random.choice(IMAGE_PROMPTS)}.
Render the quote text exactly as written, centered and highly readable:
{quote}
Use elegant typography, strong contrast, no extra quotes, no extra slogans, no watermarks, and no raw URLs.
{footer_instruction}
""".strip()


async def _create_ai_quote_image(payload: dict, filename_prefix: str, account_links: dict | None = None) -> str:
    out_dir = Path('ai_social_bot/assets')
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{filename_prefix}_{time.time_ns()}.jpg"
    result = await generate_image(_ai_quote_image_prompt(payload, account_links))
    image_data = result.get('data') or []
    if not image_data:
        raise RuntimeError(f'AI image generation returned no image data: {result}')

    first_image = image_data[0]
    b64_json = first_image.get('b64_json')
    if b64_json:
        raw_image = base64.b64decode(b64_json)
    elif first_image.get('url'):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(first_image['url'])
            response.raise_for_status()
            raw_image = response.content
    else:
        raise RuntimeError(f'AI image generation returned no supported image payload: {result}')

    temp_path = output_path.with_suffix('.generated.png')
    temp_path.write_bytes(raw_image)
    try:
        with Image.open(temp_path) as image:
            image = image.convert('RGB')
            background = Image.new('RGB', (1080, 1350), (18, 18, 18))
            fill = ImageOps.fit(image, (1080, 1350), method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(18))
            background.paste(fill)
            image.thumbnail((1000, 1270), Image.Resampling.LANCZOS)
            x = int((1080 - image.width) / 2)
            y = int((1350 - image.height) / 2)
            background.paste(image, (x, y))
            background.save(output_path, 'JPEG', quality=95)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return str(output_path)


async def generate_and_schedule_post():
    payload = await _generate_unique_quote_payload()

    _, account_links = await _meta_context_and_links()
    if settings.USE_AI_GENERATED_QUOTE_IMAGES:
        try:
            image_path = await _create_ai_quote_image(payload, 'quote', account_links)
        except Exception as exc:
            print(f"AI quote image generation failed; using generated non-stored fallback: {exc}")
            image_path = _create_image(payload, 'quote', account_links, use_stored_backgrounds=False)
    else:
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
    meta_context, account_links = await _meta_context_and_links()
    payload = await _try_generate_unique_ai_quote_payload()
    local_quote_image = None
    publish_image_path = None

    if payload is None:
        local_quote_image = _pick_local_quote_image()
        if local_quote_image is None:
            used_quotes = await _posted_quote_texts()
            payload = _parse_quote_payload(json.dumps(_local_quote_payload(used_quotes)))
            image_path = _create_image(payload, 'quote_now', account_links)
            theme = payload.get('theme', 'inspiration')
            hashtags = payload.get('hashtags') or HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
            caption = _caption_text(payload)
        else:
            image_path = str(local_quote_image)
            publish_image_path = _prepare_local_quote_image_for_publish(image_path)
            hashtags = ['#dailyquote', '#inspiration', '#quotes']
            caption = settings.LOCAL_QUOTE_IMAGE_CAPTION.strip()
    else:
        if settings.USE_AI_GENERATED_QUOTE_IMAGES:
            try:
                image_path = await _create_ai_quote_image(payload, 'quote_now', account_links)
            except Exception as exc:
                print(f"AI quote image generation failed; using generated non-stored fallback: {exc}")
                image_path = _create_image(payload, 'quote_now', account_links, use_stored_backgrounds=False)
        else:
            image_path = _create_image(payload, 'quote_now', account_links)
        theme = payload.get('theme', 'inspiration')
        hashtags = payload.get('hashtags') or HASHTAGS_BY_THEME.get(theme, HASHTAGS_BY_THEME['inspiration'])
        caption = _caption_text(payload)

    publish_image_path = publish_image_path or image_path
    try:
        publish_res = await publish_to_meta(publish_image_path, caption, context=meta_context)
    except Exception as e:
        print(f"Meta publish error: {e}")
        publish_res = {'error': str(e)}
    finally:
        _delete_generated_publish_image(publish_image_path, image_path)

    posted = 'error' not in publish_res
    if posted and local_quote_image is not None:
        _delete_local_quote_image(image_path)

    async with AsyncSessionLocal() as s:
        post = Post(
            title=payload.get('title', 'Local Quote Image') if payload else 'Local Quote Image',
            caption=caption,
            hashtags=','.join(hashtags),
            image_path=image_path,
            posted=posted,
        )
        s.add(post)
        await s.commit()

    return publish_res


async def generate_video_now():
    payload = await _generate_unique_quote_payload()
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
