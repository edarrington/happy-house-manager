"""Todoist REST API v1 client."""

import httpx
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

TODOIST_API_BASE = "https://api.todoist.com/rest/v1"


class TodoistClient:
    """Scoped to one user's API token."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    async def get_projects(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{TODOIST_API_BASE}/projects", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def get_tasks(
        self, project_id: Optional[str] = None, filter_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if project_id:
            params["project_id"] = project_id
        if filter_str:
            params["filter"] = filter_str
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{TODOIST_API_BASE}/tasks", headers=self.headers, params=params
            )
            r.raise_for_status()
            return r.json()

    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{TODOIST_API_BASE}/tasks", headers=self.headers, json=task_data
            )
            r.raise_for_status()
            return r.json()

    async def update_task(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{TODOIST_API_BASE}/tasks/{task_id}", headers=self.headers, json=task_data
            )
            r.raise_for_status()
            return r.json()

    async def close_task(self, task_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{TODOIST_API_BASE}/tasks/{task_id}/close", headers=self.headers
            )
            return r.status_code == 204

    async def delete_task(self, task_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{TODOIST_API_BASE}/tasks/{task_id}", headers=self.headers
            )
            return r.status_code == 204
