"""Auth router: Google OAuth login/callback/logout + user switching."""

import secrets
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.google_oauth import get_authorization_url, exchange_code_for_tokens, get_user_info, revoke_token
from auth.middleware import create_session_token
from services.cosmos_client import cosmos_store
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/login", include_in_schema=False)
async def login_page(request: Request):
    """Show login page or redirect to Google if 'go' param present."""
    if request.state.user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/google", include_in_schema=False)
async def google_login(request: Request, switch: bool = False):
    """Redirect to Google OAuth consent screen."""
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    if switch:
        request.session["oauth_switch"] = True
    auth_url = get_authorization_url(state=state)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback", include_in_schema=False)
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """Handle Google OAuth callback."""
    if error:
        logger.warning(f"OAuth error: {error}")
        return RedirectResponse(url="/auth/login?error=oauth_denied", status_code=302)

    # Validate state
    expected_state = request.session.pop("oauth_state", None)
    if not state or state != expected_state:
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    try:
        tokens = await exchange_code_for_tokens(code)
        user_info = await get_user_info(tokens["access_token"])
        user_id = user_info.get("sub") or user_info.get("id")
        if not user_id:
            logger.error(f"Google userinfo missing sub/id: {user_info}")
            return RedirectResponse(url="/auth/login?error=token_exchange_failed", status_code=302)
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(url="/auth/login?error=token_exchange_failed", status_code=302)

    # Upsert user in Cosmos DB
    try:
        existing = await cosmos_store.get_user(user_id)
        user_doc = existing or {
            "id": user_id,
            "sub": user_id,
        }
        user_doc.update({
            "email": user_info.get("email", ""),
            "name": user_info.get("name", ""),
            "given_name": user_info.get("given_name", ""),
            "picture": user_info.get("picture", ""),
            "google_tokens": {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in"),
                "scopes": tokens.get("scope", "").split(),
            },
        })
        await cosmos_store.upsert_user(user_doc)
    except Exception as e:
        logger.error(f"Failed to persist user to Cosmos DB: {e}")
        # Continue without persisting — session will still work

    session_token = create_session_token(user_info)
    request.session["token"] = session_token
    request.session.pop("oauth_switch", None)

    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/logout", include_in_schema=False)
async def logout(request: Request):
    """Clear session and redirect to login."""
    # Optionally revoke Google token
    user = request.state.user
    if user:
        try:
            user_doc = await cosmos_store.get_user(user["sub"])
            if user_doc and user_doc.get("google_tokens", {}).get("access_token"):
                await revoke_token(user_doc["google_tokens"]["access_token"])
        except Exception:
            pass

    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/switch", include_in_schema=False)
async def switch_user(request: Request):
    """Initiate Google OAuth for a different user account."""
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    request.session["oauth_switch"] = True
    # Use select_account to force Google account picker
    from urllib.parse import urlencode
    from config import settings
    from auth.google_oauth import GOOGLE_AUTH_URL, SCOPES
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "select_account consent",
        "state": state,
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=302)
