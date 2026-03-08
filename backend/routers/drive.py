from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from typing import Any, Dict, List, Optional
import io
import logging
from googleapiclient.http import MediaIoBaseUpload

from auth.middleware import get_current_user
from services.google_client import build_drive_service
from services.cosmos_client import cosmos_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/files")
async def list_files(
    page_size: int = 20,
    query: Optional[str] = None,
    folder_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List files from Google Drive."""
    try:
        service = await build_drive_service(current_user["sub"], cosmos_store)
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"name contains '{query}'")
        q = " and ".join(q_parts)

        result = (
            service.files()
            .list(
                q=q,
                pageSize=page_size,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink, parents)",
            )
            .execute()
        )
        return {"files": result.get("files", [])}
    except Exception as e:
        logger.error(f"Drive list_files error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/file/{file_id}")
async def get_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get metadata for a specific Drive file."""
    try:
        service = await build_drive_service(current_user["sub"], cosmos_store)
        result = (
            service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, webViewLink, description, parents",
            )
            .execute()
        )
        return result
    except Exception as e:
        logger.error(f"Drive get_file error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload a file to Google Drive."""
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
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
        return result
    except Exception as e:
        logger.error(f"Drive upload error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
