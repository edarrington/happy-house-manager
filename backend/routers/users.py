from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Any, Dict, List
import logging

from auth.middleware import get_current_user, create_session_token
from auth.google_oauth import get_authorization_url, exchange_code_for_tokens, get_user_info
from services.cosmos_client import cosmos_store
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class LinkTodoistRequest(BaseModel):
    todoist_token: str


@router.get("/auth/login")
async def login():
    """Return the Google OAuth authorization URL for the frontend to redirect to."""
    url = get_authorization_url()
    return {"authorization_url": url}


@router.get("/auth/callback")
async def oauth_callback(code: str, state: str = ""):
    """
    Handle Google OAuth callback. Exchanges code for tokens,
    upserts user in Cosmos DB, and returns a session JWT.
    """
    try:
        token_data = await exchange_code_for_tokens(code)
        access_token = token_data["access_token"]
        user_info = await get_user_info(access_token)

        user_id = user_info["sub"]
        user_doc = {
            "id": user_id,
            "email": user_info.get("email", ""),
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
            "google_tokens": {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "scopes": token_data.get("scope", "").split(),
            },
        }
        await cosmos_store.upsert_user(user_doc)

        session_token = create_session_token(user_info)
        return {
            "session_token": session_token,
            "user": {
                "id": user_id,
                "email": user_doc["email"],
                "name": user_doc["name"],
                "picture": user_doc["picture"],
            },
        }
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    try:
        user_doc = await cosmos_store.get_user(current_user["sub"])
        if not user_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {
            "id": user_doc["id"],
            "email": user_doc.get("email"),
            "name": user_doc.get("name"),
            "picture": user_doc.get("picture"),
            "has_todoist": bool(user_doc.get("todoist_token")),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_me error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/family")
async def get_family(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return all family members (both users) for the family view."""
    try:
        users = await cosmos_store.list_all_users()
        return {
            "family": [
                {
                    "id": u["id"],
                    "email": u.get("email"),
                    "name": u.get("name"),
                    "picture": u.get("picture"),
                    "has_todoist": bool(u.get("todoist_token")),
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"get_family error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/link-todoist")
async def link_todoist(
    payload: LinkTodoistRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Link a Todoist API token to the current user's profile."""
    try:
        await cosmos_store.update_todoist_token(current_user["sub"], payload.todoist_token)
        return {"linked": True}
    except Exception as e:
        logger.error(f"link_todoist error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
