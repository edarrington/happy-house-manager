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
from services.arcade_client import call_tool as arcade_call
from services.gmail_reader import list_inbox, get_message
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

TIMEZONE = "America/Los_Angeles"


def _weather_code_to_desc(code: int) -> str:
    if code == 0:
        return "Clear sky"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (45, 48):
        return "Foggy"
    if code in (51, 53, 55):
        return "Drizzle"
    if code in (61, 63, 65):
        return "Rain"
    if code in (71, 73, 75):
        return "Snow"
    if code in (80, 81, 82):
        return "Rain showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Cloudy"


async def _fetch_weather() -> str:
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={settings.weather_lat}&longitude={settings.weather_lon}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
            f"&timezone=America%2FLos_Angeles"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"Weather fetch returned {resp.status_code}")
            return ""
        data = resp.json()
        current = data.get("current", {})
        temp = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        code = current.get("weather_code", 0)
        condition = _weather_code_to_desc(code)
        return f"Current weather: {condition}, {temp}\u00b0F, {humidity}% humidity, wind {wind} mph"
    except Exception as e:
        logger.warning(f"Could not fetch weather: {e}")
        return ""


async def _web_search(query: str) -> str:
    if not settings.tavily_api_key:
        return "Web search is not configured."
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": True,
                },
            )
        if resp.status_code != 200:
            logger.warning(f"Tavily returned {resp.status_code}: {resp.text}")
            return "Search failed."
        data = resp.json()
        # Prefer the pre-summarized answer; fall back to top result snippets
        if data.get("answer"):
            return data["answer"]
        results = data.get("results", [])
        if results:
            snippets = [f"{r['title']}: {r['content'][:200]}" for r in results[:2]]
            return "\n".join(snippets)
        return "No results found."
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return "Search failed."


async def _text_to_speech(text: str) -> str | None:
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

    weather = await _fetch_weather()
    if weather:
        context_parts.append(weather)

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
        user_email = current_user.get("email", "")
        result = await arcade_call(
            "GoogleCalendar.ListEvents",
            user_email,
            calendar_id="primary",
            time_min=now.isoformat(),
            max_results=5,
        )
        events = result if isinstance(result, list) else (result or {}).get("items", [])
        if events:
            event_lines = []
            for e in events:
                start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "")
                event_lines.append(f"- {e.get('summary', 'Untitled')} at {start}")
            context_parts.append("Upcoming calendar events:\n" + "\n".join(event_lines))
    except Exception as e:
        logger.warning(f"Could not fetch calendar for voice context: {e}")

    try:
        recent = await list_inbox(max_results=5)
        if recent:
            lines = [
                f"- [ID:{m['id']}] {'(unread) ' if m['unread'] else ''}From: {m['from']} | Subject: {m['subject']} | Date: {m['date']}"
                for m in recent
            ]
            context_parts.append("Recent emails (newest first):\n" + "\n".join(lines))
        else:
            context_parts.append("No emails in inbox.")
    except Exception as e:
        logger.warning(f"Could not fetch emails for voice context: {e}")

    return "\n\n".join(context_parts)


async def _create_calendar_event(
    current_user: Dict, title: str, start: str, end: str, description: str = ""
) -> str:
    try:
        user_email = current_user.get("email", "")
        await arcade_call(
            "GoogleCalendar.CreateEvent", user_email,
            summary=title,
            start_datetime=start,
            end_datetime=end,
            description=description,
        )
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


async def _read_email(message_id: str) -> str:
    try:
        msg = await get_message(message_id)
        if not msg:
            return "Could not fetch that email."
        return (
            f"From: {msg['from']}\n"
            f"Subject: {msg['subject']}\n"
            f"Date: {msg['date']}\n\n"
            f"{msg['body'][:1000]}"
        )
    except Exception as e:
        logger.error(f"Email read failed: {e}")
        return f"Failed to read email: {e}"


@router.get("/", include_in_schema=False)
async def voice_page(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse(
        "voice/index.html",
        {"request": request, "user": current_user, "active_page": "voice"},
    )


@router.get("/weather", response_class=JSONResponse, include_in_schema=False)
async def weather_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={settings.weather_lat}&longitude={settings.weather_lon}"
            f"&current=temperature_2m,weather_code"
            f"&temperature_unit=fahrenheit"
            f"&timezone=America%2FLos_Angeles"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return JSONResponse({"error": "unavailable"}, status_code=503)
        data = resp.json()
        current = data.get("current", {})
        temp = round(current.get("temperature_2m", 0))
        code = current.get("weather_code", 0)
        return JSONResponse({"temp": temp, "condition": _weather_code_to_desc(code)})
    except Exception as e:
        logger.warning(f"Weather endpoint error: {e}")
        return JSONResponse({"error": "unavailable"}, status_code=503)


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
        if name == "read_email":
            return await _read_email(**args)
        if name == "web_search":
            return await _web_search(**args)
        return "Unknown tool."

    response_text = await voice_chat(transcript, history, context, user_name, execute_tool)
    audio_b64 = await _text_to_speech(response_text) if response_text else None
    return JSONResponse({"response": response_text, "audio_b64": audio_b64})
