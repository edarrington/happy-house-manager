"""Gmail router: inbox reading + compose/send."""

import base64
import logging
from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from auth.middleware import get_current_user
from services.google_client import build_gmail_service
from services.gmail_reader import list_inbox, get_message
from services.cosmos_client import cosmos_store

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


def _build_raw_message(
    to: str, subject: str, body: str, sender: str, cc: Optional[str] = None
) -> str:
    headers = f"To: {to}\nFrom: {sender}\nSubject: {subject}"
    if cc:
        headers += f"\nCc: {cc}"
    raw = f"{headers}\nContent-Type: text/plain; charset=utf-8\n\n{body}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


@router.get("/", include_in_schema=False)
async def gmail_index(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Gmail page with inbox."""
    messages = []
    error = None
    try:
        messages = await list_inbox(current_user["sub"], max_results=25)
    except Exception as e:
        logger.error(f"Inbox fetch error: {e}")
        error = "Could not load inbox. Re-login to grant inbox permissions if this is your first time."

    return templates.TemplateResponse(
        "gmail/index.html",
        {"request": request, "user": current_user, "active_page": "gmail",
         "messages": messages, "error": error},
    )


@router.get("/message/{message_id}", response_class=HTMLResponse, include_in_schema=False)
async def get_message_partial(
    message_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return message detail as HTMX partial (also marks as read)."""
    message = await get_message(current_user["sub"], message_id)
    return templates.TemplateResponse(
        "gmail/message.html",
        {"request": request, "message": message},
    )


@router.get("/compose", response_class=HTMLResponse, include_in_schema=False)
async def compose_partial(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse("gmail/compose.html", {"request": request, "user": current_user})


@router.post("/send", response_class=HTMLResponse, include_in_schema=False)
async def send_email(
    request: Request,
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    cc: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        profile = service.users().getProfile(userId="me").execute()
        sender = profile.get("emailAddress", "me")
        raw = _build_raw_message(to, subject, body, sender, cc)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        success = True
        error_msg = ""
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        success = False
        error_msg = str(e)

    return templates.TemplateResponse(
        "gmail/send_result.html",
        {"request": request, "success": success, "error": error_msg},
    )
