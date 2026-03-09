"""Claude API client for Eon voice assistant."""

import anthropic
from typing import List, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Eon, the voice assistant for Happy House Manager — Erick and Jewel Darrington's household AI.

You help them manage their calendar, tasks, home life, and daily plans.

Rules:
- Respond in 1-2 sentences maximum. Be brief. Voice responses must be short.
- Be direct and warm. Never formal or corporate.
- NEVER say: "Certainly!", "Absolutely!", "Great question!", "I'd be happy to help!", "Is there anything else?"
- Natural openers: "Yeah,", "Sure,", "Got it,", "On it,", "Let me think,", "Mm,"
- Express opinions. Suggest things proactively. Challenge gently if something seems off.
- Reference their tasks and calendar naturally — you already know their day.
- Sound human. Use contractions. Be brief.
- If you don't know something, say so plainly: "Not sure about that."
- You know both Erick and Jewel. Refer to them by name when relevant."""


async def voice_chat(
    transcript: str,
    history: List[Dict[str, str]],
    context: str,
    user_name: str,
) -> str:
    """Send a voice transcript to Claude and get a brief spoken response."""
    if not settings.anthropic_api_key:
        return "Anthropic API key not configured. Add it in settings."

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nCurrent context for {user_name}:\n{context}"

    messages = history[-10:]  # keep last 10 turns for context
    messages.append({"role": "user", "content": transcript})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "I ran into an issue. Try again in a moment."
