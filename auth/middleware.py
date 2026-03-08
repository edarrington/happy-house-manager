"""Auth middleware: reads session cookie and injects user into request state."""

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from typing import Optional, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)

# Paths that never require auth
PUBLIC_PATHS = {
    "/auth/login",
    "/auth/callback",
    "/auth/logout",
    "/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/static",
}


def create_session_token(user_data: Dict[str, Any]) -> str:
    """Create a JWT from user data to store in the session."""
    payload = {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data.get("name", ""),
        "picture": user_data.get("picture", ""),
        "given_name": user_data.get("given_name", ""),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a session JWT. Returns payload or None."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        return None


class AuthMiddleware(BaseHTTPMiddleware):
    """Read JWT from Starlette session, attach user to request.state."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always inject user (None if not logged in)
        request.state.user = None

        session_token = request.session.get("token")
        if session_token:
            user = decode_session_token(session_token)
            request.state.user = user

        # Redirect unauthenticated users away from protected pages
        is_public = any(
            path == p or path.startswith(p + "/") for p in PUBLIC_PATHS
        )
        if not is_public and request.state.user is None:
            return RedirectResponse(url="/auth/login", status_code=302)

        return await call_next(request)


def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: returns the authenticated user or raises 401."""
    from fastapi import HTTPException, status
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
