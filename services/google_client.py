"""Build authenticated Google API service objects for a user."""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from typing import Any
import logging

from config import settings
from services.cosmos_client import CosmosUserStore

logger = logging.getLogger(__name__)


async def get_google_credentials(user_id: str, cosmos: CosmosUserStore) -> Credentials:
    """
    Load Google credentials for a user from Cosmos DB.
    Auto-refreshes the access token if expired and persists updated tokens.
    """
    user_doc = await cosmos.get_user(user_id)
    if not user_doc:
        raise ValueError(f"No user document found for user_id={user_id}")

    google_tokens = user_doc.get("google_tokens")
    if not google_tokens:
        raise ValueError(f"No Google tokens stored for user_id={user_id}")

    creds = Credentials(
        token=google_tokens.get("access_token"),
        refresh_token=google_tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=google_tokens.get("scopes", []),
    )

    if creds.expired and creds.refresh_token:
        logger.info(f"Refreshing Google token for user {user_id}")
        creds.refresh(GoogleRequest())
        updated_tokens = {**google_tokens, "access_token": creds.token}
        await cosmos.update_user_tokens(user_id, updated_tokens)

    return creds


async def build_gmail_service(user_id: str, cosmos: CosmosUserStore) -> Any:
    creds = await get_google_credentials(user_id, cosmos)
    return build("gmail", "v1", credentials=creds)


async def build_drive_service(user_id: str, cosmos: CosmosUserStore) -> Any:
    creds = await get_google_credentials(user_id, cosmos)
    return build("drive", "v3", credentials=creds)


async def build_calendar_service(user_id: str, cosmos: CosmosUserStore) -> Any:
    creds = await get_google_credentials(user_id, cosmos)
    return build("calendar", "v3", credentials=creds)
