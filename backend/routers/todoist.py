from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from auth.middleware import get_current_user
from services.cosmos_client import cosmos_store
from services.todoist_client import TodoistClient

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskCreate(BaseModel):
    content: str
    project_id: Optional[str] = None
    due_string: Optional[str] = None
    priority: Optional[int] = None  # 1-4
    description: Optional[str] = None


class TaskUpdate(BaseModel):
    content: Optional[str] = None
    due_string: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None


async def _get_todoist_client(current_user: Dict[str, Any]) -> TodoistClient:
    """Load user's Todoist token from Cosmos DB and return a client."""
    user_doc = await cosmos_store.get_user(current_user["sub"])
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    todoist_token = user_doc.get("todoist_token")
    if not todoist_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todoist token not linked. Use POST /users/link-todoist first.",
        )
    return TodoistClient(todoist_token)


@router.get("/projects")
async def get_projects(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all Todoist projects for the authenticated user."""
    try:
        client = await _get_todoist_client(current_user)
        return {"projects": await client.get_projects()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Todoist get_projects error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tasks")
async def get_tasks(
    project_id: Optional[str] = None,
    filter_str: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List tasks, optionally filtered by project or a Todoist filter string."""
    try:
        client = await _get_todoist_client(current_user)
        return {"tasks": await client.get_tasks(project_id=project_id, filter_str=filter_str)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Todoist get_tasks error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/tasks")
async def create_task(
    payload: TaskCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new Todoist task."""
    try:
        client = await _get_todoist_client(current_user)
        task_data: Dict[str, Any] = {"content": payload.content}
        if payload.project_id:
            task_data["project_id"] = payload.project_id
        if payload.due_string:
            task_data["due_string"] = payload.due_string
        if payload.priority:
            task_data["priority"] = payload.priority
        if payload.description:
            task_data["description"] = payload.description
        return await client.create_task(task_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Todoist create_task error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update an existing Todoist task."""
    try:
        client = await _get_todoist_client(current_user)
        task_data: Dict[str, Any] = {}
        if payload.content:
            task_data["content"] = payload.content
        if payload.due_string:
            task_data["due_string"] = payload.due_string
        if payload.priority:
            task_data["priority"] = payload.priority
        if payload.description is not None:
            task_data["description"] = payload.description
        return await client.update_task(task_id, task_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Todoist update_task error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete (or close) a Todoist task."""
    try:
        client = await _get_todoist_client(current_user)
        deleted = await client.delete_task(task_id)
        return {"deleted": deleted, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Todoist delete_task error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
