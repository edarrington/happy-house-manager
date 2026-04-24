"""Calendar router: full pages + HTMX partials."""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Any, Dict
from datetime import datetime, timezone
import logging

from auth.middleware import get_current_user
from services.google_client import build_calendar_service
from services.cosmos_client import cosmos_store

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/", include_in_schema=False)
async def calendar_index(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Calendar events full page."""
    events = []
    needs_reauth = False
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        now = datetime.now(timezone.utc).isoformat()
        result = (
            service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=30,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        )
        events = result.get("items", [])
    except Exception as e:
        logger.error(f"Calendar index error: {e}")
        if "invalid_grant" in str(e):
            needs_reauth = True

    return templates.TemplateResponse(
        "calendar/index.html",
        {"request": request, "user": current_user, "active_page": "calendar", "events": events, "needs_reauth": needs_reauth},
    )


@router.get("/event/new", response_class=HTMLResponse, include_in_schema=False)
async def new_event_form(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """New event form as HTMX partial."""
    return templates.TemplateResponse(
        "calendar/event_form.html",
        {"request": request, "user": current_user, "event": None},
    )


@router.post("/event", response_class=HTMLResponse, include_in_schema=False)
async def create_event(
    request: Request,
    summary: str = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    description: Optional[str] = Form(None),
    attendees: Optional[str] = Form(None),
    time_zone: str = Form("America/Chicago"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create event and return result partial."""
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        event_body: Dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": time_zone},
            "end": {"dateTime": end, "timeZone": time_zone},
        }
        if description:
            event_body["description"] = description
        if attendees:
            event_body["attendees"] = [{"email": e.strip()} for e in attendees.split(",") if e.strip()]
        result = service.events().insert(calendarId="primary", body=event_body).execute()
        success = True
        created_event = result
        error_msg = ""
    except Exception as e:
        logger.error(f"Calendar create_event error: {e}")
        success = False
        created_event = {}
        error_msg = str(e)

    return templates.TemplateResponse(
        "calendar/event_result.html",
        {"request": request, "success": success, "event": created_event, "error": error_msg},
    )


@router.delete("/event/{event_id}", response_class=HTMLResponse, include_in_schema=False)
async def delete_event(
    event_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete event, return empty (HTMX will remove the element)."""
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except Exception as e:
        logger.error(f"Calendar delete_event error: {e}")
    return HTMLResponse(content="", status_code=200)


@router.get("/api/events")
async def api_list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    max_results: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        now = datetime.now(timezone.utc).isoformat()
        result = (
            service.events().list(
                calendarId=calendar_id,
                timeMin=time_min or now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        )
        return {"events": result.get("items", [])}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
