"""Happy House Manager - FastAPI app serving HTML templates + API endpoints."""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import logging

from config import settings
from auth.middleware import AuthMiddleware
from routers import auth, gmail, drive, calendar, todoist, settings as settings_router, voice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Happy House Manager",
    description="Family home management: Gmail, Drive, Calendar, Tasks",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# --- Middleware (added in reverse execution order: last added = outermost = runs first) ---
# AuthMiddleware must be added first so SessionMiddleware wraps it and runs first
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie="hhm_session",
    https_only=settings.environment == "production",
    same_site="lax",
)

# --- Static files ---
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Templates ---
templates = Jinja2Templates(directory="templates")

# --- Routers ---
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(gmail.router, prefix="/gmail", tags=["gmail"])
app.include_router(drive.router, prefix="/drive", tags=["drive"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(todoist.router, prefix="/tasks", tags=["tasks"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])


@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Redirect root to dashboard if logged in, else to login."""
    if request.state.user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)


@app.get("/dashboard", include_in_schema=False)
async def dashboard(request: Request):
    """Main dashboard page."""
    if not request.state.user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": request.state.user, "active_page": "dashboard"},
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "app": "happy-house-manager"}
