"""Gmail router: full pages + HTMX partials.

Uses gmail.metadata scope (sensitive, not restricted) — can list messages and
read headers/labels but NOT message body content.
"""

import base64
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Any, Dict
import logging

from auth.middleware import get_current_user
from services.google_client import build_gmail_service
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


# --- Full page views ---

@router.get("/", include_in_schema=False)
async def gmail_index(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Gmail inbox full page."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        result = (
            service.users().messages().list(
                userId="me", maxResults=30, labelIds=["INBOX"]
            ).execute()
        )
        messages_raw = result.get("messages", [])
        messages = []
        for msg in messages_raw:
            detail = (
                service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"]
                ).execute()
            )
            headers_map = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            messages.append({
                "id": detail["id"],
                "threadId": detail["threadId"],
                "subject": headers_map.get("Subject", "(no subject)"),
                "from": headers_map.get("From", ""),
                "date": headers_map.get("Date", ""),
                "unread": "UNREAD" in detail.get("labelIds", []),
            })
    except Exception as e:
        logger.error(f"Gmail index error: {e}")
        messages = []

    return templates.TemplateResponse(
        "gmail/index.html",
        {"request": request, "user": current_user, "active_page": "gmail", "messages": messages},
    )


# --- HTMX partials ---

@router.get("/message/{message_id}", response_class=HTMLResponse, include_in_schema=False)
async def get_message_partial(
    message_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return message detail as HTMX partial (metadata only — no body with current scopes)."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        detail = service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["Subject", "From", "To", "Date"]
        ).execute()
        headers_map = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        message = {
            "id": detail["id"],
            "threadId": detail["threadId"],
            "subject": headers_map.get("Subject", "(no subject)"),
            "from": headers_map.get("From", ""),
            "to": headers_map.get("To", ""),
            "date": headers_map.get("Date", ""),
            "body": None,  # gmail.metadata scope does not allow reading body content
        }
    except Exception as e:
        logger.error(f"Gmail get_message error: {e}")
        message = None

    return templates.TemplateResponse(
        "gmail/message.html",
        {"request": request, "message": message},
    )


@router.get("/compose", response_class=HTMLResponse, include_in_schema=False)
async def compose_partial(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return compose form as HTMX partial."""
    return templates.TemplateResponse(
        "gmail/compose.html",
        {"request": request, "user": current_user},
    )


@router.post("/send", response_class=HTMLResponse, include_in_schema=False)
async def send_email(
    request: Request,
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    cc: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Send email and return a success/error partial."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        profile = service.users().getProfile(userId="me").execute()
        sender = profile.get("emailAddress", "me")
        raw = _build_raw_message(to, subject, body, sender, cc)
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        success = True
        error_msg = ""
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        success = False
        error_msg = str(e)
        result = {}

    return templates.TemplateResponse(
        "gmail/send_result.html",
        {"request": request, "success": success, "error": error_msg},
    )


# --- JSON API endpoints (for programmatic access) ---

@router.get("/api/messages")
async def api_list_messages(
    max_results: int = 20,
    query: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        params: Dict[str, Any] = {"userId": "me", "maxResults": max_results, "labelIds": ["INBOX"]}
        if query:
            params["q"] = query
        result = service.users().messages().list(**params).execute()
        messages = result.get("messages", [])
        detailed = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()
            headers_map = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            detailed.append({
                "id": detail["id"],
                "threadId": detail["threadId"],
                "subject": headers_map.get("Subject", "(no subject)"),
                "from": headers_map.get("From", ""),
                "date": headers_map.get("Date", ""),
                "labelIds": detail.get("labelIds", []),
            })
        return {"messages": detailed, "count": len(detailed)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
