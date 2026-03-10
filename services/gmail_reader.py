"""Gmail inbox reader — uses the user's HHM Google credentials from Cosmos DB."""

import base64
import logging
from typing import Any

from services.google_client import build_gmail_service
from services.cosmos_client import cosmos_store

logger = logging.getLogger(__name__)


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from message payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return ""


def _header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


async def list_inbox(user_id: str, max_results: int = 20) -> list[dict]:
    """Return inbox messages (newest first) for the given HHM user."""
    service = await build_gmail_service(user_id, cosmos_store)
    result = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max_results
    ).execute()

    messages = []
    for item in result.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=item["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = msg.get("payload", {}).get("headers", [])
        label_ids = msg.get("labelIds", [])
        messages.append({
            "id": msg["id"],
            "from": _header(headers, "From"),
            "subject": _header(headers, "Subject") or "(no subject)",
            "date": _header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
            "unread": "UNREAD" in label_ids,
        })

    return messages


async def get_message(user_id: str, message_id: str) -> dict | None:
    """Fetch full message and mark it as read."""
    service = await build_gmail_service(user_id, cosmos_store)
    try:
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
    except Exception as e:
        logger.error(f"Failed to fetch message {message_id}: {e}")
        return None

    headers = msg.get("payload", {}).get("headers", [])
    body = _extract_body(msg.get("payload", {}))

    label_ids = msg.get("labelIds", [])
    if "UNREAD" in label_ids:
        try:
            service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
        except Exception as e:
            logger.warning(f"Could not mark message {message_id} as read: {e}")

    return {
        "id": message_id,
        "from": _header(headers, "From"),
        "to": _header(headers, "To"),
        "subject": _header(headers, "Subject") or "(no subject)",
        "date": _header(headers, "Date"),
        "body": body or msg.get("snippet", ""),
    }
