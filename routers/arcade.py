"""Arcade auth flow — connect Gmail and Calendar via Arcade managed OAuth."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Dict

from auth.middleware import get_current_user
from services.arcade_client import is_authorized, get_auth_url, GMAIL_USER_ID

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/connect-gmail", include_in_schema=False)
async def connect_gmail(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Redirect user to Arcade Google auth for the shared Gmail inbox."""
    if await is_authorized("Gmail.ListEmails", GMAIL_USER_ID):
        return RedirectResponse("/settings?gmail=connected")
    auth_url = await get_auth_url("Gmail.ListEmails", GMAIL_USER_ID)
    return RedirectResponse(auth_url)


@router.get("/connect-calendar", include_in_schema=False)
async def connect_calendar(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Redirect user to Arcade Google auth for their personal Calendar."""
    user_email = current_user.get("email", "")
    if await is_authorized("GoogleCalendar.ListEvents", user_email):
        return RedirectResponse("/settings?calendar=connected")
    auth_url = await get_auth_url("GoogleCalendar.ListEvents", user_email)
    return RedirectResponse(auth_url)


@router.get("/gmail-done", include_in_schema=False)
async def gmail_done(request: Request):
    return RedirectResponse("/settings")

@router.get("/calendar-done", include_in_schema=False)
async def calendar_done(request: Request):
    return RedirectResponse("/settings")
