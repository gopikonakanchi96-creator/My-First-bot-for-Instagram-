import httpx
from ai_social_bot.app.core.settings import settings
from typing import Dict, Any

OPENAI_URL = 'https://api.openai.com/v1'

def get_text_models() -> list[str]:
    models = [settings.OPENAI_MODEL]
    models.extend(
        model.strip()
        for model in settings.OPENAI_MODEL_FALLBACKS.split(',')
        if model.strip()
    )
    return list(dict.fromkeys(models))

async def generate_text(prompt: str, max_tokens: int = 300) -> Dict[str, Any]:
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
