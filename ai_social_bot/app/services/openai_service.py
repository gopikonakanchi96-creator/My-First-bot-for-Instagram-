import httpx
from ai_social_bot.app.core.settings import settings
from typing import Dict, Any

OPENAI_URL = 'https://api.openai.com/v1'
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta'

def get_text_models() -> list[str]:
    models = [settings.OPENAI_MODEL]
    models.extend(
        model.strip()
        for model in settings.OPENAI_MODEL_FALLBACKS.split(',')
        if model.strip()
    )
    return list(dict.fromkeys(models))


def get_gemini_text_models() -> list[str]:
    models = [settings.GEMINI_MODEL]
    models.extend(
        model.strip()
        for model in settings.GEMINI_MODEL_FALLBACKS.split(',')
        if model.strip()
    )
    return list(dict.fromkeys(models))


def _extract_gemini_text(data: dict) -> str:
    candidates = data.get('candidates') or []
    if not candidates:
        raise RuntimeError(f'Gemini response did not include candidates: {data}')

    content = candidates[0].get('content') or {}
    parts = content.get('parts') or []
    text_parts = [part.get('text', '') for part in parts if part.get('text')]
    text = ''.join(text_parts).strip()
    if not text:
        raise RuntimeError(f'Gemini response did not include text: {data}')
    return text


async def _generate_text_with_gemini(prompt: str, max_tokens: int) -> Dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError('GEMINI_API_KEY is not configured')

    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': settings.GEMINI_API_KEY,
    }
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': prompt}],
            }
        ],
        'generationConfig': {
            'maxOutputTokens': max_tokens,
            'temperature': 0.9,
            'responseMimeType': 'application/json',
        },
    }

    last_error = None
    async with httpx.AsyncClient(timeout=30) as client:
        for model in get_gemini_text_models():
            response = await client.post(
                f'{GEMINI_URL}/models/{model}:generateContent',
                json=payload,
                headers=headers,
            )
            if response.status_code < 400:
                content = _extract_gemini_text(response.json())
                return {
                    'choices': [
                        {
                            'message': {
                                'content': content,
                            }
                        }
                    ],
                    '_provider': 'gemini',
                    '_model': model,
                }

            last_error = response
            print(f"Gemini model failed: {model} ({response.status_code}) {response.text}")

            if response.status_code not in (400, 404, 429, 503):
                response.raise_for_status()

    if last_error is not None:
        last_error.raise_for_status()
    raise RuntimeError('No Gemini models were configured')

async def generate_text(prompt: str, max_tokens: int = 300) -> Dict[str, Any]:
    if settings.GEMINI_API_KEY:
        try:
            return await _generate_text_with_gemini(prompt, max_tokens)
        except Exception as exc:
            print(f"Gemini quote generation failed; trying OpenAI fallback: {exc}")

    headers = {'Authorization': f'Bearer {settings.OPENAI_API_KEY}', 'Content-Type': 'application/json'}
    last_error = None
    async with httpx.AsyncClient(timeout=30) as client:
        for model in get_text_models():
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
            }
            r = await client.post(f'{OPENAI_URL}/chat/completions', json=payload, headers=headers)
            if r.status_code < 400:
                data = r.json()
                data['_model'] = model
                return data

            last_error = r
            print(f"OpenAI model failed: {model} ({r.status_code}) {r.text}")

            if r.status_code not in (400, 404, 429):
                r.raise_for_status()

    if last_error is not None:
        last_error.raise_for_status()
    raise RuntimeError('No OpenAI models were configured')

async def generate_image(prompt: str, size: str = '1080x1350') -> Dict[str, Any]:
    headers = {'Authorization': f'Bearer {settings.OPENAI_API_KEY}', 'Content-Type': 'application/json'}
    payload = {'prompt': prompt, 'size': size}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f'{OPENAI_URL}/images/generations', json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
