"""Drive router: full pages + HTMX partials + file upload."""

import io
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Any, Dict
from googleapiclient.http import MediaIoBaseUpload
import logging

from auth.middleware import get_current_user
from services.google_client import build_drive_service
from services.cosmos_client import cosmos_store

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/", include_in_schema=False)
async def drive_index(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Drive file browser full page."""
    try:
        service = await build_drive_service(current_user["sub"], cosmos_store)
        result = (
            service.files().list(
                q="trashed = false",
                pageSize=40,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
                orderBy="modifiedTime desc",
            ).execute()
        )
        files = result.get("files", [])
    except Exception as e:
        logger.error(f"Drive index error: {e}")
        files = []

    return templates.TemplateResponse(
        "drive/index.html",
        {"request": request, "user": current_user, "active_page": "drive", "files": files},
    )


@router.get("/upload", response_class=HTMLResponse, include_in_schema=False)
async def upload_partial(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Upload form HTMX partial."""
    return templates.TemplateResponse(
        "drive/upload.html",
        {"request": request, "user": current_user},
    )


@router.post("/upload", response_class=HTMLResponse, include_in_schema=False)
async def do_upload(
    request: Request,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload file to Drive, return result partial."""
    try:
        service = await build_drive_service(current_user["sub"], cosmos_store)
        file_metadata: Dict[str, Any] = {"name": file.filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        content = await file.read()
        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype=file.content_type or "application/octet-stream",
            resumable=True,
        )
        result = (
            service.files().create(
                body=file_metadata, media_body=media, fields="id, name, webViewLink"
            ).execute()
        )
        success = True
        uploaded_file = result
        error_msg = ""
    except Exception as e:
        logger.error(f"Drive upload error: {e}")
        success = False
        uploaded_file = {}
        error_msg = str(e)

    return templates.TemplateResponse(
        "drive/upload_result.html",
        {"request": request, "success": success, "file": uploaded_file, "error": error_msg},
    )


@router.get("/api/files")
async def api_list_files(
    page_size: int = 20,
    query: Optional[str] = None,
    folder_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        service = await build_drive_service(current_user["sub"], cosmos_store)
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"name contains '{query}'")
        result = (
            service.files().list(
                q=" and ".join(q_parts),
                pageSize=page_size,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink, parents)",
            ).execute()
        )
        return {"files": result.get("files", [])}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
