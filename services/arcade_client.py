"""Arcade AI client — handles Gmail and Calendar tool calls with managed OAuth."""

import logging
from arcadepy import AsyncArcade
from config import settings

logger = logging.getLogger(__name__)

# Fixed user ID for the shared household Gmail inbox
GMAIL_USER_ID = "thedarringtons20@gmail.com"


def _client() -> AsyncArcade:
    return AsyncArcade(api_key=settings.arcade_api_key)


async def is_authorized(tool_name: str, user_id: str) -> bool:
    """Check whether a user has already authorized a tool."""
    try:
        tool = await _client().tools.get(tool_name, user_id=user_id)
        if tool.requirements and tool.requirements.authorization:
            return tool.requirements.authorization.token_status == "completed"
        return True
    except Exception as e:
        logger.warning(f"Arcade auth check failed for {tool_name}/{user_id}: {e}")
        return False


async def get_auth_url(tool_name: str, user_id: str, next_uri: str | None = None) -> str:
    """Return the URL the user must visit to authorize a tool."""
    kwargs: dict = {"tool_name": tool_name, "user_id": user_id}
    if next_uri:
        kwargs["next_uri"] = next_uri
    resp = await _client().tools.authorize(**kwargs)
    return resp.url


async def call_tool(tool_name: str, user_id: str, **inputs) -> dict:
    """Execute an Arcade tool and return the output value."""
    resp = await _client().tools.execute(
        tool_name=tool_name,
        input=inputs,
        user_id=user_id,
    )
    if resp.output and resp.output.value:
        return resp.output.value
    return {}
