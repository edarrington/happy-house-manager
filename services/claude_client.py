"""Anthropic Claude client for Tyrone voice assistant."""

import anthropic
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
- Shopping list rule: if the user asks to add anything to the shopping list, you MUST call create_shopping_list. Never say you added items without calling the tool first.
- Recipe workflow: when asked for a recipe and to add ingredients — (1) call web_search to find it, (2) call fetch_page on the recipe URL to get the full ingredient list, (3) call create_shopping_list with all ingredients. Always include the recipe URL in your reply."""

TOOLS = [
    {
        "name": "create_calendar_event",
        "description": "Create a new event on the user's Google Calendar.",
        "input_schema": {
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
    {
        "name": "create_todoist_task",
        "description": "Add a single task to Todoist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Task content/title"},
                "due_string": {"type": "string", "description": "Due date in natural language, e.g. 'today', 'tomorrow', 'next Monday'"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "create_shopping_list",
        "description": "Add items to the household shopping list. MUST be called whenever the user asks to add anything to the shopping list — never skip this tool and claim items were added.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of items to add, e.g. [\"2 lbs chicken thighs\", \"1 cup yogurt\", \"garlic\"]",
                },
                "label": {"type": "string", "description": "Optional label/recipe name to group items, e.g. 'Grilled Cheese'"},
            },
            "required": ["items"],
        },
    },
    {
        "name": "complete_todoist_task",
        "description": "Mark an existing Todoist task as complete using its ID from context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The ID of the task to mark complete"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "read_email",
        "description": "Read the full content of a specific email using its ID from context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "The email message ID from context"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for current information. Use for news, prices, weather, recipes, sports, or general knowledge. If the user mentions a specific website, pass it as 'site' to search within that domain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "site": {"type": "string", "description": "Optional domain to restrict search to, e.g. 'seriouseats.com' or 'allrecipes.com'"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch and read the full content of a specific URL. Use to get recipe ingredients/instructions from a recipe page URL found via web_search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL of a specific page"},
            },
            "required": ["url"],
        },
    },
]

_SHOPPING_KEYWORDS = {"shopping list", "shopping", "grocery", "groceries", "add to my list", "add to the list"}


def _wants_shopping_list(transcript: str) -> bool:
    t = transcript.lower()
    return any(kw in t for kw in _SHOPPING_KEYWORDS)


async def voice_chat(
    transcript: str,
    history: List[Dict[str, str]],
    context: str,
    user_name: str,
    execute_tool: Optional[Callable] = None,
) -> str:
    """Send a voice transcript to Claude with multi-step tool support."""
    if not settings.anthropic_api_key:
        return "Anthropic API key not configured."

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nCurrent context for {user_name}:\n{context}"

    shopping_request = _wants_shopping_list(transcript) and execute_tool is not None
    if shopping_request:
        system += "\n\nIMPORTANT: This request involves the shopping list. You MUST call create_shopping_list before giving your final response."

    messages: List[Dict[str, Any]] = []
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": transcript})

    tools = TOOLS if execute_tool else []
    # Force tool use on shopping requests so Claude can't skip straight to a text reply
    tool_choice: Any = {"type": "any"} if shopping_request else {"type": "auto"}

    try:
        shopping_list_called = False

        for round_num in range(6):
            kwargs: Dict[str, Any] = {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "system": system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            response = await client.messages.create(**kwargs)

            if response.stop_reason == "tool_use" and execute_tool:
                # Serialize content for the messages list
                serialized = []
                for block in response.content:
                    if block.type == "tool_use":
                        serialized.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                    elif block.type == "text":
                        serialized.append({"type": "text", "text": block.text})
                messages.append({"role": "assistant", "content": serialized})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.info(f"Tyrone tool [{round_num+1}]: {block.name} {block.input}")
                        if block.name == "create_shopping_list":
                            shopping_list_called = True
                        result = await execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})

                # After first forced round, switch to auto
                tool_choice = {"type": "auto"}
                continue

            # Final text response
            text = next((b.text for b in response.content if b.type == "text"), "")

            # Safety net: if shopping was wanted but tool was never called, force it
            if shopping_request and not shopping_list_called:
                logger.warning("create_shopping_list was never called — forcing it")
                messages.append({"role": "assistant", "content": text or "Let me add those to the list."})
                messages.append({"role": "user", "content": "You haven't added the items to the shopping list yet. Please call create_shopping_list now."})
                force_resp = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=500,
                    system=system,
                    tools=tools,
                    tool_choice={"type": "tool", "name": "create_shopping_list"},
                    messages=messages,
                )
                for block in force_resp.content:
                    if block.type == "tool_use" and block.name == "create_shopping_list":
                        logger.info(f"Tyrone forced create_shopping_list: {block.input}")
                        await execute_tool(block.name, block.input)

            return text

        return "Done."

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "I ran into an issue. Try again in a moment."
