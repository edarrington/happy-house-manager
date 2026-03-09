"""Voice assistant router — Eon-style conversational AI."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Dict, List
from datetime import datetime, timezone
import logging

from auth.middleware import get_current_user
from services.cosmos_client import cosmos_store
from services.claude_client import voice_chat
from services.todoist_client import TodoistClient
from services.google_client import build_calendar_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


async def _build_context(current_user: Dict[str, Any]) -> str:
    """Fetch today's tasks and upcoming calendar events as context for Claude."""
    context_parts = []
    user_id = current_user["sub"]

    # Todoist tasks
    try:
        user_doc = await cosmos_store.get_user(user_id)
        if user_doc and user_doc.get("todoist_token"):
            client = TodoistClient(user_doc["todoist_token"])
            tasks = await client.get_tasks()
            if tasks:
                task_lines = [f"- {t['content']}" for t in tasks[:10]]
                context_parts.append("Open tasks:\n" + "\n".join(task_lines))
    except Exception as e:
        logger.warning(f"Could not fetch tasks for voice context: {e}")

    # Calendar events
    try:
        service = await build_calendar_service(user_id, cosmos_store)
        now = datetime.now(timezone.utc).isoformat()
        result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        if events:
            event_lines = []
            for e in events:
                start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "")
                event_lines.append(f"- {e.get('summary', 'Untitled')} at {start}")
            context_parts.append("Upcoming calendar events:\n" + "\n".join(event_lines))
    except Exception as e:
        logger.warning(f"Could not fetch calendar for voice context: {e}")

    return "\n\n".join(context_parts)


@router.get("/", include_in_schema=False)
async def voice_page(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse(
        "voice/index.html",
        {"request": request, "user": current_user, "active_page": "voice"},
    )


@router.post("/chat", response_class=JSONResponse, include_in_schema=False)
async def voice_chat_endpoint(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    body = await request.json()
    transcript = body.get("transcript", "").strip()
    history: List[Dict[str, str]] = body.get("history", [])

    if not transcript:
        return JSONResponse({"response": ""})

    user_name = current_user.get("given_name") or current_user.get("name", "there")
    context = await _build_context(current_user)

    response_text = await voice_chat(transcript, history, context, user_name)
    return JSONResponse({"response": response_text})
