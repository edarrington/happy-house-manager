from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

from auth.middleware import get_current_user
from services.google_client import build_calendar_service
from services.cosmos_client import cosmos_store

router = APIRouter()
logger = logging.getLogger(__name__)


class EventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start: str  # ISO 8601 datetime string
    end: str    # ISO 8601 datetime string
    time_zone: str = "America/Chicago"
    attendees: Optional[List[str]] = None  # list of email addresses
    calendar_id: str = "primary"


class EventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    time_zone: Optional[str] = None
    calendar_id: str = "primary"


@router.get("/events")
async def list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List calendar events. Defaults to upcoming events from now."""
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        now = datetime.now(timezone.utc).isoformat()
        params: Dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": time_min or now,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_max:
            params["timeMax"] = time_max

        result = service.events().list(**params).execute()
        return {"events": result.get("items", [])}
    except Exception as e:
        logger.error(f"Calendar list_events error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/events")
async def create_event(
    payload: EventCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new calendar event."""
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        event_body: Dict[str, Any] = {
            "summary": payload.summary,
            "start": {"dateTime": payload.start, "timeZone": payload.time_zone},
            "end": {"dateTime": payload.end, "timeZone": payload.time_zone},
        }
        if payload.description:
            event_body["description"] = payload.description
        if payload.attendees:
            event_body["attendees"] = [{"email": e} for e in payload.attendees]

        result = (
            service.events()
            .insert(calendarId=payload.calendar_id, body=event_body)
            .execute()
        )
        return result
    except Exception as e:
        logger.error(f"Calendar create_event error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    payload: EventUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update an existing calendar event."""
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        existing = service.events().get(calendarId=payload.calendar_id, eventId=event_id).execute()

        if payload.summary:
            existing["summary"] = payload.summary
        if payload.description is not None:
            existing["description"] = payload.description
        if payload.start:
            tz = payload.time_zone or existing["start"].get("timeZone", "UTC")
            existing["start"] = {"dateTime": payload.start, "timeZone": tz}
        if payload.end:
            tz = payload.time_zone or existing["end"].get("timeZone", "UTC")
            existing["end"] = {"dateTime": payload.end, "timeZone": tz}

        result = (
            service.events()
            .update(calendarId=payload.calendar_id, eventId=event_id, body=existing)
            .execute()
        )
        return result
    except Exception as e:
        logger.error(f"Calendar update_event error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    calendar_id: str = "primary",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a calendar event."""
    try:
        service = await build_calendar_service(current_user["sub"], cosmos_store)
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"deleted": True, "event_id": event_id}
    except Exception as e:
        logger.error(f"Calendar delete_event error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
