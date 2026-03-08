"""Todoist router: full pages + HTMX partials."""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Any, Dict
import logging

from auth.middleware import get_current_user
from services.cosmos_client import cosmos_store
from services.todoist_client import TodoistClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


async def _get_todoist_client(current_user: Dict[str, Any]) -> TodoistClient:
    user_doc = await cosmos_store.get_user(current_user["sub"])
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    todoist_token = user_doc.get("todoist_token")
    if not todoist_token:
        raise HTTPException(
            status_code=400,
            detail="Todoist token not configured. Add TODOIST_TOKEN to your profile.",
        )
    return TodoistClient(todoist_token)


@router.get("/", include_in_schema=False)
async def tasks_index(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Tasks full page with projects and tasks."""
    try:
        client = await _get_todoist_client(current_user)
        projects = await client.get_projects()
        tasks = await client.get_tasks()
        todoist_configured = True
        error_msg = ""
    except HTTPException as e:
        projects = []
        tasks = []
        todoist_configured = False
        error_msg = e.detail
    except Exception as e:
        logger.error(f"Todoist index error: {e}")
        projects = []
        tasks = []
        todoist_configured = False
        error_msg = str(e)

    return templates.TemplateResponse(
        "tasks/index.html",
        {
            "request": request,
            "user": current_user,
            "active_page": "tasks",
            "projects": projects,
            "tasks": tasks,
            "todoist_configured": todoist_configured,
            "error": error_msg,
        },
    )


@router.get("/project/{project_id}/tasks", response_class=HTMLResponse, include_in_schema=False)
async def project_tasks_partial(
    project_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Tasks for a specific project as HTMX partial."""
    try:
        client = await _get_todoist_client(current_user)
        tasks = await client.get_tasks(project_id=project_id)
    except Exception as e:
        logger.error(f"Todoist project tasks error: {e}")
        tasks = []

    return templates.TemplateResponse(
        "tasks/task_list.html",
        {"request": request, "tasks": tasks},
    )


@router.get("/new", response_class=HTMLResponse, include_in_schema=False)
async def new_task_form(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """New task form as HTMX partial."""
    try:
        client = await _get_todoist_client(current_user)
        projects = await client.get_projects()
    except Exception:
        projects = []
    return templates.TemplateResponse(
        "tasks/task_form.html",
        {"request": request, "projects": projects},
    )


@router.post("/", response_class=HTMLResponse, include_in_schema=False)
async def create_task(
    request: Request,
    content: str = Form(...),
    project_id: Optional[str] = Form(None),
    due_string: Optional[str] = Form(None),
    priority: int = Form(1),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create task and return result partial."""
    try:
        client = await _get_todoist_client(current_user)
        task_data: Dict[str, Any] = {"content": content, "priority": priority}
        if project_id:
            task_data["project_id"] = project_id
        if due_string:
            task_data["due_string"] = due_string
        created_task = await client.create_task(task_data)
        success = True
        error_msg = ""
    except Exception as e:
        logger.error(f"Todoist create_task error: {e}")
        created_task = {}
        success = False
        error_msg = str(e)

    return templates.TemplateResponse(
        "tasks/task_result.html",
        {"request": request, "success": success, "task": created_task, "error": error_msg},
    )


@router.post("/close/{task_id}", response_class=HTMLResponse, include_in_schema=False)
async def close_task(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Close (complete) a task, return empty to remove from DOM."""
    try:
        client = await _get_todoist_client(current_user)
        await client.close_task(task_id)
    except Exception as e:
        logger.error(f"Todoist close_task error: {e}")
    return HTMLResponse(content="", status_code=200)


@router.get("/api/projects")
async def api_get_projects(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        client = await _get_todoist_client(current_user)
        return {"projects": await client.get_projects()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/tasks")
async def api_get_tasks(
    project_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        client = await _get_todoist_client(current_user)
        return {"tasks": await client.get_tasks(project_id=project_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
