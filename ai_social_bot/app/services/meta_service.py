import asyncio
import httpx
from ai_social_bot.app.core.settings import settings

API_BASE = f'https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}'
PAGE_CONTEXT_FIELDS = 'id,name,username,link,access_token,instagram_business_account{id,username,name}'


async def get_page_context(client: httpx.AsyncClient) -> dict:
    """
    Resolve Page token and connected Instagram business account from the configured token.
    """
    response = await client.get(
        f'{API_BASE}/me/accounts',
        params={
            'fields': PAGE_CONTEXT_FIELDS,
            'access_token': settings.META_PAGE_ACCESS_TOKEN,
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f'Meta account lookup failed ({response.status_code}): {response.text}')

    for page in response.json().get('data', []):
        if page.get('id') == settings.FACEBOOK_PAGE_ID:
            return {
                'page_id': page['id'],
                'page_name': page.get('name'),
                'page_username': page.get('username'),
                'page_link': page.get('link'),
                'page_access_token': page.get('access_token') or settings.META_PAGE_ACCESS_TOKEN,
                'instagram_account': page.get('instagram_business_account'),
            }

    page_response = await client.get(
        f'{API_BASE}/{settings.FACEBOOK_PAGE_ID}',
        params={
            'fields': PAGE_CONTEXT_FIELDS,
            'access_token': settings.META_PAGE_ACCESS_TOKEN,
        },
    )
    if page_response.status_code >= 400:
        raise RuntimeError(
            f'Facebook Page {settings.FACEBOOK_PAGE_ID} was not returned by /me/accounts '
            f'and direct Page lookup failed ({page_response.status_code}): {page_response.text}'
        )

    page = page_response.json()
    return {
        'page_id': page['id'],
        'page_name': page.get('name'),
        'page_username': page.get('username'),
        'page_link': page.get('link'),
        'page_access_token': page.get('access_token') or settings.META_PAGE_ACCESS_TOKEN,
        'instagram_account': page.get('instagram_business_account'),
    }


def _public_facebook_page_url(context: dict) -> str | None:
    if settings.FACEBOOK_PAGE_URL:
        return settings.FACEBOOK_PAGE_URL
    if context.get('page_link') and settings.FACEBOOK_PAGE_ID not in context['page_link']:
        return context['page_link']
    if context.get('page_username'):
        return f"https://www.facebook.com/{context['page_username']}"
    return None


def _public_instagram_url(instagram_account: dict | None) -> str | None:
    if settings.INSTAGRAM_PROFILE_URL:
        return settings.INSTAGRAM_PROFILE_URL
    if not instagram_account or not instagram_account.get('username'):
        if settings.INSTAGRAM_USERNAME:
            return f'https://www.instagram.com/{settings.INSTAGRAM_USERNAME.strip("@")}/'
        return None
    return f"https://www.instagram.com/{instagram_account['username']}/"


def _public_instagram_username(instagram_account: dict | None) -> str | None:
    if settings.INSTAGRAM_USERNAME:
        return settings.INSTAGRAM_USERNAME.strip('@')
    if instagram_account and instagram_account.get('username'):
        return instagram_account['username']
    return None


def get_public_account_links(context: dict | None = None) -> dict:
    context = context or {}
    instagram_account = context.get('instagram_account')
    return {
        'facebook_url': _public_facebook_page_url(context),
        'facebook_name': context.get('page_name'),
        'instagram_url': _public_instagram_url(instagram_account),
        'instagram_username': _public_instagram_username(instagram_account),
    }


def build_platform_captions(caption: str, context: dict) -> tuple[str, str]:
    """
    Add public account names without raw http links or internal Meta numeric account IDs.
    """
    base_caption = caption.strip()
    account_links = get_public_account_links(context)
    facebook_name = account_links.get('facebook_name')
    instagram_username = account_links.get('instagram_username')

    facebook_lines = [base_caption]
    account_lines = []
    if instagram_username:
        account_lines.append(f'Instagram: @{instagram_username}')
    if facebook_name:
        account_lines.append(f'Facebook: {facebook_name}')
    if account_lines:
        facebook_lines.extend(['', *account_lines])

    instagram_lines = [base_caption]
    if instagram_username:
        instagram_lines.extend(['', f'@{instagram_username}'])
    if facebook_name:
        instagram_lines.append(f'Facebook: {facebook_name}')

    return '\n'.join(facebook_lines), '\n'.join(instagram_lines)


async def _get_facebook_photo_url(client: httpx.AsyncClient, photo_id: str, page_access_token: str) -> str:
    response = await client.get(
        f'{API_BASE}/{photo_id}',
        params={
            'fields': 'images,link',
            'access_token': page_access_token,
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f'Facebook photo URL lookup failed ({response.status_code}): {response.text}')

    data = response.json()
    images = data.get('images') or []
    if images and images[0].get('source'):
        return images[0]['source']
    if data.get('link'):
        return data['link']

    raise RuntimeError(f'Facebook photo {photo_id} did not return a public image URL')


async def publish_page_photo(image_path: str, message: str, context: dict | None = None) -> dict:
    """
    Upload a local image file as a published Facebook Page photo post.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        context = context or await get_page_context(client)
        page_access_token = context['page_access_token']
        upload_url = f"{API_BASE}/{settings.FACEBOOK_PAGE_ID}/photos"
        data = {
            'caption': message,
            'published': 'true',
            'access_token': page_access_token,
        }
        with open(image_path, 'rb') as f:
            files = {'source': ('image.jpg', f, 'image/jpeg')}
            response = await client.post(upload_url, data=data, files=files)

        if response.status_code >= 400:
            raise RuntimeError(f'Facebook publish failed ({response.status_code}): {response.text}')

        result = response.json()
        if result.get('id'):
            result['image_url'] = await _get_facebook_photo_url(client, result['id'], page_access_token)
        return result


async def publish_instagram_photo(image_url: str, caption: str, context: dict | None = None) -> dict:
    """
    Publish an image URL to the Instagram business account connected to the Facebook Page.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        context = context or await get_page_context(client)
        instagram_account = context.get('instagram_account')
        if not instagram_account or not instagram_account.get('id'):
            raise RuntimeError('No Instagram business account is connected to the configured Facebook Page')

        page_access_token = context['page_access_token']
        instagram_id = instagram_account['id']
        create_response = await client.post(
            f'{API_BASE}/{instagram_id}/media',
            data={
                'image_url': image_url,
                'caption': caption,
                'access_token': page_access_token,
            },
        )
        if create_response.status_code >= 400:
            raise RuntimeError(f'Instagram media container failed ({create_response.status_code}): {create_response.text}')

        creation_id = create_response.json().get('id')
        if not creation_id:
            raise RuntimeError(f'Instagram media container did not return an id: {create_response.text}')

        publish_response = None
        for attempt in range(1, 7):
            publish_response = await client.post(
                f'{API_BASE}/{instagram_id}/media_publish',
                data={
                    'creation_id': creation_id,
                    'access_token': page_access_token,
                },
            )
            if publish_response.status_code < 400:
                break
            if 'not ready to be published' not in publish_response.text and 'Media ID is not available' not in publish_response.text:
                break
            await asyncio.sleep(attempt * 5)

        if publish_response is None or publish_response.status_code >= 400:
            status_code = publish_response.status_code if publish_response is not None else 'unknown'
            response_text = publish_response.text if publish_response is not None else 'no response'
            raise RuntimeError(f'Instagram publish failed ({status_code}): {response_text}')

        return {
            'instagram_account_id': instagram_id,
            'instagram_username': instagram_account.get('username'),
            'creation_id': creation_id,
            'publish': publish_response.json(),
        }


async def publish_to_meta(image_path: str, caption: str, context: dict | None = None) -> dict:
    """
    Publish one generated image to both Facebook Page and connected Instagram business account.
    Facebook is published first so its public photo URL can be reused by Instagram.
    """
    result = {'facebook': None, 'instagram': None}
    if context is None:
        async with httpx.AsyncClient(timeout=60) as client:
            context = await get_page_context(client)

    facebook_caption, instagram_caption = build_platform_captions(caption, context)
    result['facebook'] = await publish_page_photo(image_path, facebook_caption, context=context)

    image_url = result['facebook'].get('image_url')
    if not image_url:
        raise RuntimeError('Facebook published, but no public image URL was available for Instagram')

    result['instagram'] = await publish_instagram_photo(image_url, instagram_caption, context=context)
    return result
