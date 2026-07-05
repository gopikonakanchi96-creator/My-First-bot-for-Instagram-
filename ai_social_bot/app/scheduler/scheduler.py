from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ai_social_bot.app.core.settings import settings
from ai_social_bot.app.services.post_service import generate_post_now

class Scheduler:
    _scheduler = AsyncIOScheduler()

    @classmethod
    def start(cls, app=None):
        for t in (settings.POST_TIME_1, settings.POST_TIME_2):
            h,m = t.split(':')
            cls._scheduler.add_job(
                generate_post_now,
                CronTrigger(hour=int(h), minute=int(m)),
                id=f'post_{t}',
                replace_existing=True,
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
