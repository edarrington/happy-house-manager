from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from typing import Optional, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)

# Paths that do not require authentication
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/callback",
}


def create_session_token(user_data: Dict[str, Any]) -> str:
    """Create a JWT session token from user data."""
    payload = {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data.get("name", ""),
        "picture": user_data.get("picture", ""),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


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


class SessionMiddleware(BaseHTTPMiddleware):
    """Extract JWT from Authorization header and attach user to request state."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/auth/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        user = decode_session_token(token)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired session token"},
            )

        request.state.user = user
        return await call_next(request)


def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: returns the authenticated user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
