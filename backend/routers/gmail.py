from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import base64
import logging

from auth.middleware import get_current_user
from services.google_client import build_gmail_service
from services.cosmos_client import cosmos_store

router = APIRouter()
logger = logging.getLogger(__name__)


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None


class ReplyEmailRequest(BaseModel):
    thread_id: str
    message_id: str
    body: str
    to: str


def _build_raw_message(to: str, subject: str, body: str, sender: str, cc: Optional[str] = None) -> str:
    headers = f"To: {to}\nFrom: {sender}\nSubject: {subject}"
    if cc:
        headers += f"\nCc: {cc}"
    raw = f"{headers}\nContent-Type: text/plain; charset=utf-8\n\n{body}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


@router.get("/messages")
async def list_messages(
    request: Request,
    max_results: int = 20,
    query: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List Gmail messages from the authenticated user's inbox."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        params: Dict[str, Any] = {"userId": "me", "maxResults": max_results, "labelIds": ["INBOX"]}
        if query:
            params["q"] = query

        result = service.users().messages().list(**params).execute()
        messages = result.get("messages", [])

        # Fetch snippet and subject for each message
        detailed = []
        for msg in messages:
            detail = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )
            headers_list = detail.get("payload", {}).get("headers", [])
            headers_map = {h["name"]: h["value"] for h in headers_list}
            detailed.append({
                "id": detail["id"],
                "threadId": detail["threadId"],
                "snippet": detail.get("snippet", ""),
                "subject": headers_map.get("Subject", "(no subject)"),
                "from": headers_map.get("From", ""),
                "date": headers_map.get("Date", ""),
                "labelIds": detail.get("labelIds", []),
            })
        return {"messages": detailed, "count": len(detailed)}
    except Exception as e:
        logger.error(f"Gmail list_messages error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/message/{message_id}")
async def get_message(
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get full content of a specific Gmail message."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        detail = service.users().messages().get(userId="me", id=message_id, format="full").execute()

        headers_list = detail.get("payload", {}).get("headers", [])
        headers_map = {h["name"]: h["value"] for h in headers_list}

        # Extract body
        body = ""
        payload = detail.get("payload", {})
        if payload.get("body", {}).get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif payload.get("parts"):
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break

        return {
            "id": detail["id"],
            "threadId": detail["threadId"],
            "subject": headers_map.get("Subject", "(no subject)"),
            "from": headers_map.get("From", ""),
            "to": headers_map.get("To", ""),
            "date": headers_map.get("Date", ""),
            "body": body,
            "labelIds": detail.get("labelIds", []),
        }
    except Exception as e:
        logger.error(f"Gmail get_message error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/send")
async def send_email(
    payload: SendEmailRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Send an email from the authenticated user."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        profile = service.users().getProfile(userId="me").execute()
        sender = profile.get("emailAddress", "me")

        raw = _build_raw_message(payload.to, payload.subject, payload.body, sender, payload.cc)
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"message_id": result["id"], "thread_id": result["threadId"]}
    except Exception as e:
        logger.error(f"Gmail send_email error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/reply")
async def reply_to_email(
    payload: ReplyEmailRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Reply to an existing Gmail thread."""
    try:
        service = await build_gmail_service(current_user["sub"], cosmos_store)
        profile = service.users().getProfile(userId="me").execute()
        sender = profile.get("emailAddress", "me")

        subject = "Re: (reply)"
        raw_message = base64.urlsafe_b64encode(
            f"To: {payload.to}\nFrom: {sender}\nSubject: {subject}\n"
            f"In-Reply-To: {payload.message_id}\nReferences: {payload.message_id}\n"
            f"Content-Type: text/plain; charset=utf-8\n\n{payload.body}".encode()
        ).decode()

        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message, "threadId": payload.thread_id})
            .execute()
        )
        return {"message_id": result["id"], "thread_id": result["threadId"]}
    except Exception as e:
        logger.error(f"Gmail reply error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
