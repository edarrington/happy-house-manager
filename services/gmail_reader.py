"""Gmail inbox reader via Arcade — no token management needed."""

import logging
from services.arcade_client import call_tool, GMAIL_USER_ID

logger = logging.getLogger(__name__)


def _pick(d: dict, *keys: str, default="") -> str:
    """Return the first non-empty value from a dict for any of the given keys."""
    for k in keys:
        v = d.get(k)
        if v:
            return str(v)
    return default


async def list_inbox(max_results: int = 20) -> list[dict]:
    """Return inbox messages (newest first)."""
    result = await call_tool("Gmail.ListEmails", GMAIL_USER_ID, n_emails=max_results)
    logger.debug(f"Gmail.ListEmails raw keys: {list(result.keys()) if result else 'empty'}")

    emails = []
    for email in result.get("emails", []):
        emails.append({
            "id": _pick(email, "id", "thread_id", "message_id"),
            "from": _pick(email, "sender", "from"),
            "subject": _pick(email, "subject") or "(no subject)",
            "date": _pick(email, "date"),
            "snippet": (_pick(email, "body", "snippet"))[:150],
            "unread": not email.get("is_read", True),
        })
    return emails


async def get_message(message_id: str) -> dict | None:
    """Fetch the full content of a message by ID."""
    try:
        result = await call_tool("Gmail.GetThread", GMAIL_USER_ID, thread_id=message_id)
        logger.debug(f"Gmail.GetThread raw keys: {list(result.keys()) if result else 'empty'}")
        if not result:
            return None

        # GetThread returns a thread; grab the last message
        messages = result.get("messages", [])
        msg = messages[-1] if messages else result

        return {
            "id": message_id,
            "from": _pick(msg, "sender", "from"),
            "to": _pick(msg, "to"),
            "subject": _pick(msg, "subject") or "(no subject)",
            "date": _pick(msg, "date"),
            "body": _pick(msg, "body", "snippet"),
        }
    except Exception as e:
        logger.error(f"Gmail.GetThread failed for {message_id}: {e}")
        return None
