"""OpenAI client for Tyrone voice assistant."""

import httpx
import json
from typing import List, Dict, Any, Callable, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Tyrone, the voice assistant for Happy House Manager — Erick and Jewel Darrington's household AI.

You help them manage their calendar, tasks, home life, and daily plans.

You have access to:
- Their open Todoist tasks (listed in context with IDs)
- Their upcoming Google Calendar events (listed in context)
- Their unread emails from thedarringtons20@gmail.com (listed in context with IDs and sender/subject)
- Tools to create calendar events, add/complete tasks, read full email content, search the web, and read specific URLs

Rules:
- Respond in 1-2 sentences maximum. Be brief. Voice responses must be short.
- Be direct and warm. Never formal or corporate.
- NEVER say: "Certainly!", "Absolutely!", "Great question!", "I'd be happy to help!", "Is there anything else?"
- Natural openers: "Yeah,", "Sure,", "Got it,", "On it,", "Let me think,"
- When you complete a tool action, confirm briefly: "Done, added that." or "Marked it done."
- Sound human. Use contractions. Be brief.
- When asked about emails, use the unread email list in context. If they want more detail on a specific one, use read_email.
- When summarizing emails, list who they're from and the subject — keep it short.
- You know both Erick and Jewel. Refer to them by name when relevant.
- ALWAYS use web_search before saying you don't know something. Never say "Not sure" or "I don't know" for factual questions without searching first.
- Use web_search for recipes, news, weather, prices, sports scores, general knowledge — anything not in context.
- If the user mentions a specific website (e.g. "from seriouseats.com"), pass that domain as the site parameter to web_search.
- Use fetch_page only when given a direct link to a specific page — never on a homepage.
- Recipe workflow: when asked to find a recipe and add ingredients, use web_search to find it, then fetch_page on the recipe URL to get the full ingredients list, then call create_shopping_list with all the ingredients at once. Always include the recipe URL in your final response."""

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
            "description": "Add a single task to Todoist.",
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
            "name": "create_shopping_list",
            "description": "Add multiple grocery or shopping items to Todoist at once. Use this when adding recipe ingredients or any list of items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of items to add, e.g. [\"2 lbs chicken thighs\", \"1 cup yogurt\", \"garlic\"]",
                    },
                    "label": {"type": "string", "description": "Optional label prefix for all items, e.g. 'Chicken Tikka Masala'"},
                },
                "required": ["items"],
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
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read the full content of a specific email using its ID from context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The email message ID from context"},
                },
                "required": ["message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use for news, prices, weather, recipes, sports, or general knowledge. If the user mentions a specific website, pass it as 'site' to search within that domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "site": {"type": "string", "description": "Optional domain to restrict search to, e.g. 'seriouseats.com' or 'allrecipes.com'"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch and read the full content of a specific URL. Use to get recipe ingredients/instructions from a recipe page URL found via web_search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL of a specific page, e.g. https://www.seriouseats.com/chicken-tikka-masala"},
                },
                "required": ["url"],
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
    """Send a voice transcript to OpenAI with multi-step tool support."""
    if not settings.openai_api_key:
        return "OpenAI API key not configured."

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nCurrent context for {user_name}:\n{context}"

    messages = [{"role": "system", "content": system}]
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": transcript})

    base_payload: Dict[str, Any] = {
        "model": "gpt-4o-mini",
        "tools": TOOLS if execute_tool else [],
        "tool_choice": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Multi-round tool loop — up to 5 rounds
            for round_num in range(5):
                payload = {**base_payload, "messages": messages, "max_tokens": 300 if round_num == 0 else 200}
                if not execute_tool:
                    payload.pop("tools", None)
                    payload.pop("tool_choice", None)

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

                if choice["finish_reason"] != "tool_calls" or not execute_tool:
                    return assistant_message.get("content", "")

                # Execute tool calls
                messages.append(assistant_message)
                for tool_call in assistant_message.get("tool_calls", []):
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    logger.info(f"Tyrone tool [{round_num+1}]: {tool_name} {tool_args}")
                    tool_result = await execute_tool(tool_name, tool_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    })

        return "Done."

    except Exception as e:
        logger.error(f"OpenAI request failed: {e}")
        return "I ran into an issue. Try again in a moment."
