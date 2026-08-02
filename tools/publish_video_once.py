import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_social_bot.app.database.session import init_db
from ai_social_bot.app.services.post_service import generate_video_now


async def main() -> int:
    await init_db()
    started_at = datetime.now().isoformat(timespec='seconds')
    print(f'Video publish started at {started_at}')

    result = await generate_video_now()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    if 'error' in result:
        return 1
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f'Video publish failed: {exc}', file=sys.stderr)
        raise
