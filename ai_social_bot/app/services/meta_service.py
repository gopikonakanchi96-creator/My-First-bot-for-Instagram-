import asyncio
import httpx
from ai_social_bot.app.core.settings import settings

API_BASE = f'https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}'
THREADS_API_BASE = f'https://graph.threads.net/{settings.THREADS_API_VERSION}'
PAGE_CONTEXT_FIELDS = 'id,name,username,link,access_token,instagram_business_account{id,username,name}'
PAGE_DIRECT_FIELDS = 'id,name,username,link,instagram_business_account{id,username,name}'
TRANSIENT_META_STATUS_CODES = {500, 502, 503, 504}


def _safe_meta_payload(payload: dict) -> dict:
    safe = {}
    for key, value in payload.items():
        if key == 'access_token':
            safe[key] = '<redacted>'
        elif isinstance(value, dict):
            safe[key] = _safe_meta_payload(value)
        elif isinstance(value, list):
            safe[key] = [_safe_meta_payload(item) if isinstance(item, dict) else item for item in value]
        else:
            safe[key] = value
    return safe


def _meta_response_detail(response: httpx.Response) -> str:
    try:
        payload = _safe_meta_payload(response.json())
    except Exception:
        return response.text
    return str(payload)


def _is_transient_meta_error(response: httpx.Response) -> bool:
    return response.status_code in TRANSIENT_META_STATUS_CODES


async def get_page_context(client: httpx.AsyncClient) -> dict:
    """
    Resolve Page token and connected Instagram business account from the configured token.
    Supports either a Facebook user token that can read /me/accounts or a Page token for
    the configured FACEBOOK_PAGE_ID.
    """
    response = await client.get(
        f'{API_BASE}/me/accounts',
        params={
            'fields': PAGE_CONTEXT_FIELDS,
            'access_token': settings.META_PAGE_ACCESS_TOKEN,
        },
    )
    account_lookup_error = None
    if response.status_code >= 400:
        account_lookup_error = f'/me/accounts failed ({response.status_code}): {_meta_response_detail(response)}'
    else:
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
        account_lookup_error = f'/{settings.FACEBOOK_PAGE_ID} was not returned by /me/accounts'

    page_response = await client.get(
        f'{API_BASE}/{settings.FACEBOOK_PAGE_ID}',
        params={
            'fields': PAGE_DIRECT_FIELDS,
            'access_token': settings.META_PAGE_ACCESS_TOKEN,
        },
    )
    if page_response.status_code >= 400:
        raise RuntimeError(
            f'Meta account lookup failed. {account_lookup_error}; '
            f'direct Page lookup failed ({page_response.status_code}): {_meta_response_detail(page_response)}'
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


async def check_meta_access() -> dict:
    """
    Run read-only Graph API checks and return sanitized diagnostics.
    """
    checks = {}
    async with httpx.AsyncClient(timeout=30) as client:
        me_response = await client.get(
            f'{API_BASE}/me',
            params={
                'fields': 'id,name',
                'access_token': settings.META_PAGE_ACCESS_TOKEN,
            },
        )
        token_identity_payload = me_response.json() if me_response.content else {}
        checks['token_identity'] = {
            'ok': me_response.status_code < 400,
            'status_code': me_response.status_code,
            'response': _safe_meta_payload(token_identity_payload),
        }

        accounts_response = await client.get(
            f'{API_BASE}/me/accounts',
            params={
                'fields': PAGE_CONTEXT_FIELDS,
                'access_token': settings.META_PAGE_ACCESS_TOKEN,
            },
        )
        accounts_payload = accounts_response.json() if accounts_response.content else {}
        account_pages = [
            page
            for page in accounts_payload.get('data', [])
            if isinstance(page, dict)
        ]
        configured_page = next(
            (page for page in account_pages if page.get('id') == settings.FACEBOOK_PAGE_ID),
            None,
        )
        checks['user_accounts_lookup'] = {
            'ok': accounts_response.status_code < 400,
            'status_code': accounts_response.status_code,
            'response': _safe_meta_payload(accounts_payload),
            'configured_page_found': configured_page is not None,
            'configured_page_has_access_token': bool(configured_page and configured_page.get('access_token')),
        }

        page_response = await client.get(
            f'{API_BASE}/{settings.FACEBOOK_PAGE_ID}',
            params={
                'fields': PAGE_DIRECT_FIELDS,
                'access_token': settings.META_PAGE_ACCESS_TOKEN,
            },
        )
        checks['direct_page_lookup'] = {
            'ok': page_response.status_code < 400,
            'status_code': page_response.status_code,
            'response': _safe_meta_payload(page_response.json()) if page_response.content else {},
        }

        try:
            context = await get_page_context(client)
            checks['resolved_context'] = {
                'ok': True,
                'page_id': context.get('page_id'),
                'page_name': context.get('page_name'),
                'instagram_account': context.get('instagram_account'),
            }
        except Exception as exc:
            checks['resolved_context'] = {
                'ok': False,
                'error': str(exc),
            }

        checks['threads_account_lookup'] = await check_threads_access(client)

    token_identity_id = checks['token_identity'].get('response', {}).get('id')
    page_token_for_configured_page = (
        checks['token_identity'].get('ok')
        and token_identity_id == settings.FACEBOOK_PAGE_ID
    )
    user_token_can_resolve_page_token = (
        checks['user_accounts_lookup'].get('ok')
        and checks['user_accounts_lookup'].get('configured_page_found')
        and checks['user_accounts_lookup'].get('configured_page_has_access_token')
    )
    checks['page_publish_token_available'] = bool(
        page_token_for_configured_page
        or user_token_can_resolve_page_token
    )
    checks['ready_for_publish'] = bool(
        checks['resolved_context'].get('ok')
        and checks['resolved_context'].get('instagram_account', {}).get('id')
        and checks['page_publish_token_available']
    )
    checks['threads_ready_for_publish'] = bool(checks['threads_account_lookup'].get('ok'))
    return checks


async def check_threads_access(client: httpx.AsyncClient | None = None) -> dict:
    """
    Run a read-only Threads API check. Threads uses its own Graph host and token.
    """
    if not settings.THREADS_ACCESS_TOKEN:
        return {
            'ok': False,
            'configured': False,
            'error': 'THREADS_ACCESS_TOKEN is not configured',
        }

    close_client = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        response = await client.get(
            f'{THREADS_API_BASE}/me',
            params={
                'fields': 'id,username,name',
                'access_token': settings.THREADS_ACCESS_TOKEN,
            },
        )
        payload = response.json() if response.content else {}
        return {
            'ok': response.status_code < 400,
            'configured': True,
            'status_code': response.status_code,
            'response': _safe_meta_payload(payload),
        }
    finally:
        if close_client:
            await client.aclose()


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


def _public_threads_url() -> str | None:
    if settings.THREADS_PROFILE_URL:
        return settings.THREADS_PROFILE_URL
    if settings.THREADS_USERNAME:
        return f'https://www.threads.net/@{settings.THREADS_USERNAME.strip("@")}/'
    return None


def _public_threads_username() -> str | None:
    if settings.THREADS_USERNAME:
        return settings.THREADS_USERNAME.strip('@')
    return None


def get_public_account_links(context: dict | None = None) -> dict:
    context = context or {}
    instagram_account = context.get('instagram_account')
    return {
        'facebook_url': _public_facebook_page_url(context),
        'facebook_name': settings.FACEBOOK_PAGE_NAME or context.get('page_name'),
        'instagram_url': _public_instagram_url(instagram_account),
        'instagram_username': _public_instagram_username(instagram_account),
        'threads_url': _public_threads_url(),
        'threads_username': _public_threads_username(),
    }


def build_platform_captions(caption: str, context: dict) -> tuple[str, str, str]:
    """
    Add public account names without raw http links or internal Meta numeric account IDs.
    """
    base_caption = caption.strip()
    account_links = get_public_account_links(context)
    facebook_name = account_links.get('facebook_name')
    instagram_username = account_links.get('instagram_username')
    threads_username = account_links.get('threads_username')

    facebook_lines = [base_caption]
    account_lines = []
    if instagram_username:
        account_lines.append(f'Instagram: @{instagram_username}')
    if facebook_name:
        account_lines.append(f'Facebook: {facebook_name}')
    if threads_username:
        account_lines.append(f'Threads: @{threads_username}')
    if account_lines:
        facebook_lines.extend(['', *account_lines])

    instagram_lines = [base_caption]
    if instagram_username:
        instagram_lines.extend(['', f'@{instagram_username}'])
    if facebook_name:
        instagram_lines.append(f'Facebook: {facebook_name}')

    threads_lines = [base_caption]
    if threads_username:
        threads_lines.extend(['', f'@{threads_username}'])
    if instagram_username:
        threads_lines.append(f'Instagram: @{instagram_username}')
    if facebook_name:
        threads_lines.append(f'Facebook: {facebook_name}')

    return '\n'.join(facebook_lines), '\n'.join(instagram_lines), '\n'.join(threads_lines)


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


async def _get_facebook_video_url(client: httpx.AsyncClient, video_id: str, page_access_token: str) -> str | None:
    response = await client.get(
        f'{API_BASE}/{video_id}',
        params={
            'fields': 'source,permalink_url',
            'access_token': page_access_token,
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f'Facebook video URL lookup failed ({response.status_code}): {response.text}')

    data = response.json()
    return data.get('source') or data.get('permalink_url')


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
        response = None
        for attempt in range(1, 4):
            with open(image_path, 'rb') as f:
                files = {'source': ('image.jpg', f, 'image/jpeg')}
                response = await client.post(upload_url, data=data, files=files)
            if response.status_code < 400 or not _is_transient_meta_error(response):
                break
            await asyncio.sleep(attempt * 5)

        if response is None or response.status_code >= 400:
            raise RuntimeError(f'Facebook publish failed ({response.status_code}): {response.text}')

        result = response.json()
        if result.get('id'):
            result['image_url'] = await _get_facebook_photo_url(client, result['id'], page_access_token)
        return result


async def publish_page_video(video_path: str, description: str, context: dict | None = None) -> dict:
    """
    Upload a local MP4 as a published Facebook Page video post.
    """
    async with httpx.AsyncClient(timeout=180) as client:
        context = context or await get_page_context(client)
        page_access_token = context['page_access_token']
        upload_url = f"{API_BASE}/{settings.FACEBOOK_PAGE_ID}/videos"
        data = {
            'description': description,
            'published': 'true',
            'access_token': page_access_token,
        }
        response = None
        for attempt in range(1, 4):
            with open(video_path, 'rb') as f:
                files = {'source': ('quote_video.mp4', f, 'video/mp4')}
                response = await client.post(upload_url, data=data, files=files)
            if response.status_code < 400 or not _is_transient_meta_error(response):
                break
            await asyncio.sleep(attempt * 5)

        if response is None or response.status_code >= 400:
            raise RuntimeError(f'Facebook video publish failed ({response.status_code}): {response.text}')

        result = response.json()
        video_id = result.get('id')
        if video_id:
            result['video_url'] = await _get_facebook_video_url(client, video_id, page_access_token)
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


async def _publish_threads_media(media_type: str, media_url_key: str, media_url: str, text: str) -> dict:
    if not settings.THREADS_ACCESS_TOKEN:
        raise RuntimeError('THREADS_ACCESS_TOKEN is not configured')

    async with httpx.AsyncClient(timeout=90) as client:
        create_response = await client.post(
            f'{THREADS_API_BASE}/me/threads',
            data={
                'media_type': media_type,
                media_url_key: media_url,
                'text': text,
                'access_token': settings.THREADS_ACCESS_TOKEN,
            },
        )
        if create_response.status_code >= 400:
            raise RuntimeError(f'Threads media container failed ({create_response.status_code}): {create_response.text}')

        creation_id = create_response.json().get('id')
        if not creation_id:
            raise RuntimeError(f'Threads media container did not return an id: {create_response.text}')

        container_status = None
        for attempt in range(1, 8):
            status_response = await client.get(
                f'{THREADS_API_BASE}/{creation_id}',
                params={
                    'fields': 'id,status,error_message',
                    'access_token': settings.THREADS_ACCESS_TOKEN,
                },
            )
            if status_response.status_code >= 400:
                container_status = {
                    'status': 'UNKNOWN',
                    'error_message': f'status lookup failed ({status_response.status_code}): {status_response.text}',
                }
                break

            container_status = status_response.json()
            status = str(container_status.get('status', '')).upper()
            if status in {'FINISHED', 'PUBLISHED'}:
                break
            if status in {'ERROR', 'EXPIRED'}:
                raise RuntimeError(f'Threads media container failed before publish: {container_status}')
            await asyncio.sleep(attempt * 3)

        publish_response = None
        for attempt in range(1, 7):
            publish_response = await client.post(
                f'{THREADS_API_BASE}/me/threads_publish',
                data={
                    'creation_id': creation_id,
                    'access_token': settings.THREADS_ACCESS_TOKEN,
                },
            )
            if publish_response.status_code < 400:
                break
            if 'not ready' not in publish_response.text.lower():
                break
            await asyncio.sleep(attempt * 5)

        if publish_response is None or publish_response.status_code >= 400:
            status_code = publish_response.status_code if publish_response is not None else 'unknown'
            response_text = publish_response.text if publish_response is not None else 'no response'
            raise RuntimeError(f'Threads publish failed ({status_code}): {response_text}')

        return {
            'creation_id': creation_id,
            'container_status': container_status,
            'publish': publish_response.json(),
        }


async def publish_threads_photo(image_url: str, text: str) -> dict:
    """
    Publish an image URL as a Threads post.
    """
    return await _publish_threads_media('IMAGE', 'image_url', image_url, text)


async def publish_threads_video(video_url: str, text: str) -> dict:
    """
    Publish a public MP4 URL as a Threads video post.
    """
    return await _publish_threads_media('VIDEO', 'video_url', video_url, text)


async def publish_instagram_reel(video_url: str, caption: str, context: dict | None = None) -> dict:
    """
    Publish a public MP4 URL as an Instagram Reel.
    """
    async with httpx.AsyncClient(timeout=180) as client:
        context = context or await get_page_context(client)
        instagram_account = context.get('instagram_account')
        if not instagram_account or not instagram_account.get('id'):
            raise RuntimeError('No Instagram business account is connected to the configured Facebook Page')

        page_access_token = context['page_access_token']
        instagram_id = instagram_account['id']
        create_response = await client.post(
            f'{API_BASE}/{instagram_id}/media',
            data={
                'media_type': 'REELS',
                'video_url': video_url,
                'caption': caption,
                'access_token': page_access_token,
            },
        )
        if create_response.status_code >= 400:
            raise RuntimeError(f'Instagram reel container failed ({create_response.status_code}): {create_response.text}')

        creation_id = create_response.json().get('id')
        if not creation_id:
            raise RuntimeError(f'Instagram reel container did not return an id: {create_response.text}')

        publish_response = None
        for attempt in range(1, 13):
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
            raise RuntimeError(f'Instagram reel publish failed ({status_code}): {response_text}')

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
    result = {'facebook': None, 'instagram': None, 'threads': None}
    if context is None:
        async with httpx.AsyncClient(timeout=60) as client:
            context = await get_page_context(client)

    facebook_caption, instagram_caption, threads_caption = build_platform_captions(caption, context)
    result['facebook'] = await publish_page_photo(image_path, facebook_caption, context=context)

    image_url = result['facebook'].get('image_url')
    if not image_url:
        raise RuntimeError('Facebook published, but no public image URL was available for Instagram')

    result['instagram'] = await publish_instagram_photo(image_url, instagram_caption, context=context)
    if settings.THREADS_ACCESS_TOKEN:
        try:
            result['threads'] = await publish_threads_photo(image_url, threads_caption)
        except Exception as exc:
            result['threads'] = {'error': str(exc)}
    else:
        result['threads'] = {'skipped': 'THREADS_ACCESS_TOKEN is not configured'}
    return result


async def publish_video_to_meta(video_path: str, caption: str, context: dict | None = None) -> dict:
    """
    Publish one generated MP4 to Facebook Page, then attempt Instagram Reels and Threads video.
    Instagram and Threads require a public video URL; Meta may reject Facebook-hosted first-party URLs.
    """
    result = {'facebook': None, 'instagram': None, 'threads': None}
    if context is None:
        async with httpx.AsyncClient(timeout=60) as client:
            context = await get_page_context(client)

    facebook_caption, instagram_caption, threads_caption = build_platform_captions(caption, context)
    result['facebook'] = await publish_page_video(video_path, facebook_caption, context=context)

    video_url = result['facebook'].get('video_url')
    if not video_url:
        result['instagram'] = {'error': 'Facebook published, but no public video URL was available for Instagram'}
        result['threads'] = {'error': 'Facebook published, but no public video URL was available for Threads'}
        return result
    if not video_url.startswith(('http://', 'https://')):
        result['instagram'] = {
            'error': (
                'Facebook published, but Meta returned a Facebook-relative video link instead of '
                'a public MP4 URL required by Instagram Reels'
            ),
            'video_url': video_url,
        }
        result['threads'] = {
            'error': (
                'Facebook published, but Meta returned a Facebook-relative video link instead of '
                'a public MP4 URL required by Threads'
            ),
            'video_url': video_url,
        }
        return result

    try:
        result['instagram'] = await publish_instagram_reel(video_url, instagram_caption, context=context)
    except Exception as exc:
        result['instagram'] = {'error': str(exc)}
    if settings.THREADS_ACCESS_TOKEN:
        try:
            result['threads'] = await publish_threads_video(video_url, threads_caption)
        except Exception as exc:
            result['threads'] = {'error': str(exc)}
    else:
        result['threads'] = {'skipped': 'THREADS_ACCESS_TOKEN is not configured'}
    return result
