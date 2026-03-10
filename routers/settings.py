"""Settings router: user profile and integration tokens."""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Dict
import logging

from auth.middleware import get_current_user
from services.cosmos_client import cosmos_store
from services.arcade_client import is_authorized, GMAIL_USER_ID

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/", include_in_schema=False)
async def settings_page(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_doc = await cosmos_store.get_user(current_user["sub"])
    todoist_configured = bool(user_doc and user_doc.get("todoist_token"))
    gmail_connected = await is_authorized("Gmail.ListEmails", GMAIL_USER_ID)
    calendar_connected = await is_authorized("GoogleCalendar.ListEvents", current_user.get("email", ""))
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user,
            "active_page": "settings",
            "todoist_configured": todoist_configured,
            "gmail_connected": gmail_connected,
            "calendar_connected": calendar_connected,
            "saved": False,
        },
    )


@router.post("/todoist-token", response_class=HTMLResponse, include_in_schema=False)
async def save_todoist_token(
    request: Request,
    todoist_token: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save Todoist API token to the user's Cosmos DB document."""
    error = ""
    saved = False
    try:
        await cosmos_store.update_todoist_token(current_user["sub"], todoist_token.strip())
        saved = True
    except Exception as e:
        logger.error(f"Failed to save Todoist token: {e}")
        error = "Failed to save token. Please try again."

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user,
            "active_page": "settings",
            "todoist_configured": saved,
            "saved": saved,
            "error": error,
        },
    )
