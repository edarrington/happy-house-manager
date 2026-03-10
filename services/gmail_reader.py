"""Gmail inbox reader using desktop OAuth credentials stored in Cosmos DB.

The refresh token is persisted back to Cosmos DB after each use so that
Google's refresh token rotation never leaves us with an invalid token.
"""

import base64
import logging
from typing import Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

from services.cosmos_client import cosmos_store

logger = logging.getLogger(__name__)


async def _build_service() -> Any:
    """Build Gmail service, refreshing and persisting the token as needed."""
    creds_doc = await cosmos_store.get_gmail_credentials()
    if not creds_doc:
        raise RuntimeError("Gmail credentials not found in Cosmos DB. Seed them via the admin endpoint.")

    creds = Credentials(
        token=None,
        refresh_token=creds_doc["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_doc["client_id"],
        client_secret=creds_doc["client_secret"],
        scopes=["https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify"],
    )

    old_refresh_token = creds_doc["refresh_token"]
    creds.refresh(GoogleRequest())

    # Persist rotated refresh token so the next call still works
    if creds.refresh_token and creds.refresh_token != old_refresh_token:
        logger.info("Gmail refresh token rotated — saving new token to Cosmos DB")
        await cosmos_store.update_gmail_refresh_token(creds.refresh_token)

    return build("gmail", "v1", credentials=creds)


def _extract_body(payload: dict) -> str:
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


async def list_inbox(max_results: int = 20) -> list[dict]:
    """Return inbox messages (newest first)."""
    service = await _build_service()
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


async def get_message(message_id: str) -> dict | None:
    """Fetch full message and mark it as read."""
    service = await _build_service()
    try:
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
    except Exception as e:
        logger.error(f"Failed to fetch message {message_id}: {e}")
        return None

    headers = msg.get("payload", {}).get("headers", [])
    body = _extract_body(msg.get("payload", {}))

    if "UNREAD" in msg.get("labelIds", []):
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
