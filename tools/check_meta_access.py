import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_social_bot.app.services.meta_service import check_meta_access


async def main() -> int:
    result = await check_meta_access()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result.get('ready_for_publish') else 1


if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f'Meta access check failed: {exc}', file=sys.stderr)
        raise
