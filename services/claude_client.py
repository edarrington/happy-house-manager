"""OpenAI client for Tyrone voice assistant."""

import httpx
import json
from typing import List, Dict, Any, Callable, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Tyrone, the voice assistant for Happy House Manager — Erick and Jewel Darrington's household AI.

You help them manage their calendar, tasks, home life, and daily plans.

Rules:
- Respond in 1-2 sentences maximum. Be brief. Voice responses must be short.
- Be direct and warm. Never formal or corporate.
- NEVER say: "Certainly!", "Absolutely!", "Great question!", "I'd be happy to help!", "Is there anything else?"
- Natural openers: "Yeah,", "Sure,", "Got it,", "On it,", "Let me think,"
- When you complete a tool action, confirm briefly: "Done, added that." or "Marked it done."
- Sound human. Use contractions. Be brief.
- If you don't know something, say so plainly: "Not sure about that."
- You know both Erick and Jewel. Refer to them by name when relevant."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a new event on the user's Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "start": {"type": "string", "description": "Start datetime in ISO 8601, e.g. 2026-03-10T14:00:00"},
                    "end": {"type": "string", "description": "End datetime in ISO 8601, e.g. 2026-03-10T15:00:00"},
                    "description": {"type": "string", "description": "Optional event description"},
                },
                "required": ["title", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_todoist_task",
            "description": "Add a new task to Todoist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Task content/title"},
                    "due_string": {"type": "string", "description": "Due date in natural language, e.g. 'today', 'tomorrow', 'next Monday'"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todoist_task",
            "description": "Mark an existing Todoist task as complete using its ID from context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The ID of the task to mark complete"},
                },
                "required": ["task_id"],
            },
        },
    },
]


async def voice_chat(
    transcript: str,
    history: List[Dict[str, str]],
    context: str,
    user_name: str,
    execute_tool: Optional[Callable] = None,
) -> str:
    """Send a voice transcript to OpenAI with optional tool support."""
    if not settings.openai_api_key:
        return "OpenAI API key not configured."

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nCurrent context for {user_name}:\n{context}"

    messages = [{"role": "system", "content": system}]
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": transcript})

    payload: Dict[str, Any] = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 200,
    }
    if execute_tool:
        payload["tools"] = TOOLS

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )

        if resp.status_code != 200:
            logger.error(f"OpenAI error {resp.status_code}: {resp.text}")
            return "Give me a second \u2014 just hit a snag. Try again."

        data = resp.json()
        choice = data["choices"][0]
        assistant_message = choice["message"]

        # Handle tool calls
        if choice["finish_reason"] == "tool_calls" and execute_tool:
            messages.append(assistant_message)

            for tool_call in assistant_message.get("tool_calls", []):
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                logger.info(f"Tyrone calling tool: {tool_name} with {tool_args}")
                tool_result = await execute_tool(tool_name, tool_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result,
                })

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp2 = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": "gpt-4o-mini", "messages": messages, "max_tokens": 150},
                )
            if resp2.status_code == 200:
                return resp2.json()["choices"][0]["message"]["content"]
            return "Done."

        return assistant_message.get("content", "")

    except Exception as e:
        logger.error(f"OpenAI request failed: {e}")
        return "I ran into an issue. Try again in a moment."
