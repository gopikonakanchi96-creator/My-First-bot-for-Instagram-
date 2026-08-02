import argparse
import asyncio
import json
import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv


THREADS_API_HOST = 'https://graph.threads.net'
THREADS_AUTH_HOST = 'https://threads.net'
DEFAULT_SCOPES = 'threads_basic,threads_content_publish'


def _env_or_arg(value: str | None, env_name: str) -> str:
    resolved = value or os.getenv(env_name)
    if not resolved:
        raise SystemExit(f'Missing {env_name}. Pass it as an argument or set it in .env.')
    return resolved


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_auth_url(args: argparse.Namespace) -> None:
    app_id = _env_or_arg(args.app_id, 'THREADS_APP_ID')
    redirect_uri = _env_or_arg(args.redirect_uri, 'THREADS_REDIRECT_URI')
    params = {
        'client_id': app_id,
        'redirect_uri': redirect_uri,
        'scope': args.scope,
        'response_type': 'code',
    }
    if args.state:
        params['state'] = args.state

    print(f'{THREADS_AUTH_HOST}/oauth/authorize?{urlencode(params)}')


async def exchange_code(args: argparse.Namespace) -> None:
    app_id = _env_or_arg(args.app_id, 'THREADS_APP_ID')
    app_secret = _env_or_arg(args.app_secret, 'THREADS_APP_SECRET')
    redirect_uri = _env_or_arg(args.redirect_uri, 'THREADS_REDIRECT_URI')
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f'{THREADS_API_HOST}/oauth/access_token',
            params={
                'client_id': app_id,
                'client_secret': app_secret,
                'code': args.code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            },
        )
    payload = response.json() if response.content else {}
    if response.status_code >= 400:
        raise SystemExit(f'Code exchange failed ({response.status_code}): {payload or response.text}')
    _print_json(payload)


async def exchange_long_lived(args: argparse.Namespace) -> None:
    app_secret = _env_or_arg(args.app_secret, 'THREADS_APP_SECRET')
    access_token = _env_or_arg(args.access_token, 'THREADS_ACCESS_TOKEN')
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f'{THREADS_API_HOST}/access_token',
            params={
                'grant_type': 'th_exchange_token',
                'client_secret': app_secret,
                'access_token': access_token,
            },
        )
    payload = response.json() if response.content else {}
    if response.status_code >= 400:
        raise SystemExit(f'Long-lived token exchange failed ({response.status_code}): {payload or response.text}')
    _print_json(payload)


async def refresh_token(args: argparse.Namespace) -> None:
    access_token = _env_or_arg(args.access_token, 'THREADS_ACCESS_TOKEN')
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f'{THREADS_API_HOST}/refresh_access_token',
            params={
                'grant_type': 'th_refresh_token',
                'access_token': access_token,
            },
        )
    payload = response.json() if response.content else {}
    if response.status_code >= 400:
        raise SystemExit(f'Token refresh failed ({response.status_code}): {payload or response.text}')
    _print_json(payload)


async def check_me(args: argparse.Namespace) -> None:
    access_token = _env_or_arg(args.access_token, 'THREADS_ACCESS_TOKEN')
    api_version = args.api_version or os.getenv('THREADS_API_VERSION') or 'v1.0'
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f'{THREADS_API_HOST}/{api_version}/me',
            params={
                'fields': 'id,username,name',
                'access_token': access_token,
            },
        )
    payload = response.json() if response.content else {}
    if response.status_code >= 400:
        raise SystemExit(f'Threads /me check failed ({response.status_code}): {payload or response.text}')
    _print_json(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Threads OAuth setup helper.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    auth_url = subparsers.add_parser('auth-url', help='Print the Threads authorization URL.')
    auth_url.add_argument('--app-id')
    auth_url.add_argument('--redirect-uri')
    auth_url.add_argument('--scope', default=DEFAULT_SCOPES)
    auth_url.add_argument('--state')
    auth_url.set_defaults(func=build_auth_url)

    exchange = subparsers.add_parser('exchange-code', help='Exchange an authorization code for a short-lived token.')
    exchange.add_argument('--code', required=True)
    exchange.add_argument('--app-id')
    exchange.add_argument('--app-secret')
    exchange.add_argument('--redirect-uri')
    exchange.set_defaults(func=exchange_code)

    long_lived = subparsers.add_parser('long-lived', help='Exchange a short-lived token for a long-lived token.')
    long_lived.add_argument('--access-token')
    long_lived.add_argument('--app-secret')
    long_lived.set_defaults(func=exchange_long_lived)

    refresh = subparsers.add_parser('refresh', help='Refresh an unexpired long-lived token.')
    refresh.add_argument('--access-token')
    refresh.set_defaults(func=refresh_token)

    me = subparsers.add_parser('me', help='Validate the configured Threads token.')
    me.add_argument('--access-token')
    me.add_argument('--api-version')
    me.set_defaults(func=check_me)

    return parser


def main() -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    if asyncio.iscoroutine(result):
        asyncio.run(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
