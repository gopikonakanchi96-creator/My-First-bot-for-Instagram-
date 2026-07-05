from fastapi import APIRouter
from ai_social_bot.app.services.post_service import generate_and_schedule_post, generate_post_now
from ai_social_bot.app.models.models import Post
from ai_social_bot.app.database.session import engine
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get('/posts')
async def list_posts():
    async with AsyncSession(engine) as s:
        res = await s.execute(Post.__table__.select().order_by(Post.created_at.desc()))
        rows = res.fetchall()
        return [dict(row._mapping) for row in rows]

@router.post('/generate')
async def generate():
    await generate_and_schedule_post()
    return {'status': 'queued'}

@router.post('/publish-now')
async def publish_now():
    publish_result = await generate_post_now()
    if 'error' in publish_result:
        return {'status': 'failed', 'facebook': publish_result}
    return {'status': 'published', 'facebook': publish_result}

@router.get('/logs')
async def get_logs():
    return {'message': 'logs endpoint - expand as needed'}
