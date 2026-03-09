"""Drive router.

All Drive scopes (including drive.metadata.readonly) are restricted and require
Google verification. Drive functionality is unavailable until the app is verified.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from typing import Any, Dict

from auth.middleware import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", include_in_schema=False)
async def drive_index(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Drive page — unavailable until Google verification is complete."""
    return templates.TemplateResponse(
        "drive/index.html",
        {"request": request, "user": current_user, "active_page": "drive", "files": None},
    )
