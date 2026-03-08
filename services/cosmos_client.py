"""Azure Cosmos DB client for user profiles and tokens."""

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from typing import Optional, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)


class CosmosUserStore:
    """
    Azure Cosmos DB user store.
    Each document is one user (Erick or Jewel), keyed by Google sub.
    """

    def __init__(self):
        self._client: Optional[CosmosClient] = None
        self._container = None

    async def _get_container(self):
        if self._container is None:
            self._client = CosmosClient(
                url=settings.cosmos_endpoint,
                credential=settings.cosmos_key,
            )
            db = self._client.get_database_client(settings.cosmos_database_name)
            self._container = db.get_container_client(settings.cosmos_users_container)
        return self._container

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user document by Google sub."""
        try:
            container = await self._get_container()
            item = await container.read_item(item=user_id, partition_key=user_id)
            return item
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            raise

    async def upsert_user(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a user document. user_doc must include 'id' field."""
        try:
            container = await self._get_container()
            result = await container.upsert_item(body=user_doc)
            return result
        except Exception as e:
            logger.error(f"Error upserting user {user_doc.get('id')}: {e}")
            raise

    async def update_user_tokens(self, user_id: str, google_tokens: Dict[str, Any]) -> None:
        """Update the google_tokens field for a user."""
        user_doc = await self.get_user(user_id)
        if not user_doc:
            raise ValueError(f"User {user_id} not found")
        user_doc["google_tokens"] = google_tokens
        await self.upsert_user(user_doc)

    async def update_todoist_token(self, user_id: str, todoist_token: str) -> None:
        """Store a user's Todoist API token."""
        user_doc = await self.get_user(user_id)
        if not user_doc:
            raise ValueError(f"User {user_id} not found")
        user_doc["todoist_token"] = todoist_token
        await self.upsert_user(user_doc)

    async def list_all_users(self) -> list[Dict[str, Any]]:
        """Return all user documents (family members)."""
        try:
            container = await self._get_container()
            items = []
            async for item in container.read_all_items():
                items.append(item)
            return items
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise

    async def close(self):
        if self._client:
            await self._client.close()


# Singleton
cosmos_store = CosmosUserStore()
