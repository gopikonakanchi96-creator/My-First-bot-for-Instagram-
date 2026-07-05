from fastapi import FastAPI
from ai_social_bot.app.core.settings import settings
from ai_social_bot.app.database.session import init_db
from ai_social_bot.app.scheduler.scheduler import Scheduler
from ai_social_bot.app.api.routes import router
from ai_social_bot.app.utils.logger import setup_logging

app = FastAPI(title="AI Facebook Quote Bot")
app.include_router(router)

setup_logging()

@app.on_event("startup")
async def startup_event():
    await init_db()
    Scheduler.start(app)

@app.on_event("shutdown")
async def shutdown_event():
    await Scheduler.shutdown()

@app.get("/status")
async def status():
    return {"status": "ok", "scheduler": Scheduler.status()}
