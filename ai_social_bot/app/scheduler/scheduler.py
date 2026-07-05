from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ai_social_bot.app.core.settings import settings
from ai_social_bot.app.services.post_service import generate_post_now


def _configured_post_times() -> list[str]:
    raw_times = settings.POST_TIMES.strip()
    if raw_times:
        times = [time.strip() for time in raw_times.split(',') if time.strip()]
    else:
        times = [settings.POST_TIME_1, settings.POST_TIME_2]

    valid_times = []
    for time in times:
        parts = time.split(':')
        if len(parts) != 2:
            raise ValueError(f'Invalid post time "{time}". Use HH:MM format.')
        hour, minute = (int(part) for part in parts)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError(f'Invalid post time "{time}". Use a real 24-hour time.')
        valid_times.append(f'{hour:02d}:{minute:02d}')

    return sorted(set(valid_times))


class Scheduler:
    _scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)

    @classmethod
    def start(cls, app=None):
        for post_time in _configured_post_times():
            hour, minute = post_time.split(':')
            cls._scheduler.add_job(
                generate_post_now,
                CronTrigger(
                    hour=int(hour),
                    minute=int(minute),
                    timezone=settings.SCHEDULER_TIMEZONE,
                ),
                id=f'post_{post_time.replace(":", "")}',
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=900,
            )
        if not cls._scheduler.running:
            cls._scheduler.start()

    @classmethod
    async def shutdown(cls):
        cls._scheduler.shutdown(wait=False)

    @classmethod
    def status(cls):
        return {
            'running': cls._scheduler.running,
            'timezone': str(cls._scheduler.timezone),
            'jobs': [
                {
                    'id': job.id,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in cls._scheduler.get_jobs()
            ],
        }
