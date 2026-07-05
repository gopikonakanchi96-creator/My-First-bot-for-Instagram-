from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get('/', response_class=HTMLResponse)
async def dashboard():
    html = """
    <html><head><title>AI Facebook Quote Bot</title></head><body>
    <h1>AI Facebook Quote Bot Dashboard</h1>
    <p>Simple dashboard. Use API endpoints to interact.</p>
    </body></html>
    """
    return html
