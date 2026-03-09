"""Voice assistant router — Tyrone with tool support and OpenAI TTS."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Dict, List
from datetime import datetime, timezone
import base64
import httpx
import logging

from auth.middleware import get_current_user
from services.cosmos_client import cosmos_store
from services.claude_client import voice_chat
from services.todoist_client import TodoistClient
from services.google_client import build_calendar_service
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

TIMEZONE = "America/Los_Angeles"


async def _text_to_speech(text: str) -> str | None:
    """Convert text to speech via OpenAI TTS. Returns base64 MP3 or None."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": "tts-1", "input": text, "voice": "onyx"},
            )
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode("utf-8")
        logger.error(f"TTS error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"TTS failed: {e}")
    return None


async def _build_context(current_user: Dict[str, Any]) -> str:
    context_parts = []
    user_id = current_user["sub"]

    now = datetime.now(timezone.utc)
    context_parts.append(f"Current date/time: {now.strftime('%A, %B %d, %Y %H:%M UTC')}")

    try:
        user_doc = await cosmos_store.get_user(user_id)
        if user_doc and user_doc.get("todoist_token"):
            client = TodoistClient(user_doc["todoist_token"])
            tasks = await client.get_tasks()
            if tasks:
                task_lines = [f"- [ID:{t['id']}] {t['content']}" for t in tasks[:10]]
                context_parts.append("Open tasks:\n" + "\n".join(task_lines))
    except Exception as e:
        logger.warning(f"Could not fetch tasks for voice context: {e}")

    try:
        service = await build_calendar_service(user_id, cosmos_store)
        result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
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


async def _create_calendar_event(
    current_user: Dict, title: str, start: str, end: str, description: str = ""
) -> str:
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start, "timeZone": TIMEZONE},
            "end": {"dateTime": end, "timeZone": TIMEZONE},
        }
        service.events().insert(calendarId="primary", body=event).execute()
        return f"Created calendar event '{title}'."
    except Exception as e:
        logger.error(f"Calendar create failed: {e}")
        return f"Failed to create event: {e}"


async def _create_todoist_task(current_user: Dict, content: str, due_string: str = "") -> str:
    try:
        user_doc = await cosmos_store.get_user(current_user["sub"])
        token = user_doc.get("todoist_token") if user_doc else None
        if not token:
            return "Todoist not connected."
        payload: Dict[str, Any] = {"content": content}
        if due_string:
            payload["due_string"] = due_string
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.todoist.com/api/v1/tasks",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
        return f"Task '{content}' added." if resp.status_code in (200, 201) else f"Failed: {resp.text}"
    except Exception as e:
        logger.error(f"Todoist create failed: {e}")
        return f"Failed to add task: {e}"


async def _complete_todoist_task(current_user: Dict, task_id: str) -> str:
    try:
        user_doc = await cosmos_store.get_user(current_user["sub"])
        token = user_doc.get("todoist_token") if user_doc else None
        if not token:
            return "Todoist not connected."
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.todoist.com/api/v1/tasks/{task_id}/close",
                headers={"Authorization": f"Bearer {token}"},
            )
        return "Task completed." if resp.status_code in (200, 204) else f"Failed: {resp.text}"
    except Exception as e:
        logger.error(f"Todoist complete failed: {e}")
        return f"Failed to complete task: {e}"


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

    async def execute_tool(name: str, args: Dict) -> str:
        if name == "create_calendar_event":
            return await _create_calendar_event(current_user, **args)
        if name == "create_todoist_task":
            return await _create_todoist_task(current_user, **args)
        if name == "complete_todoist_task":
            return await _complete_todoist_task(current_user, **args)
        return "Unknown tool."

    response_text = await voice_chat(transcript, history, context, user_name, execute_tool)
    audio_b64 = await _text_to_speech(response_text) if response_text else None
    return JSONResponse({"response": response_text, "audio_b64": audio_b64})
