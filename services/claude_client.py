"""Gemini API client for Tyrone voice assistant."""

import google.generativeai as genai
from typing import List, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Tyrone, the voice assistant for Happy House Manager — Erick and Jewel Darrington's household AI.

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
    """Send a voice transcript to Gemini and get a brief spoken response."""
    if not settings.gemini_api_key:
        return "Gemini API key not configured."

    genai.configure(api_key=settings.gemini_api_key)

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nCurrent context for {user_name}:\n{context}"

    # Build Gemini chat history (exclude last user message — sent separately)
    gemini_history = []
    for msg in history[-10:]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system,
        )
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(
            transcript,
            generation_config=genai.types.GenerationConfig(max_output_tokens=150),
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "I ran into an issue. Try again in a moment."
