"""Gemini REST API client for Tyrone voice assistant."""

import httpx
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
- Natural openers: "Yeah,", "Sure,", "Got it,", "On it,", "Let me think,"
- Sound human. Use contractions. Be brief.
- If you don't know something, say so plainly: "Not sure about that."
- You know both Erick and Jewel. Refer to them by name when relevant."""

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


async def voice_chat(
    transcript: str,
    history: List[Dict[str, str]],
    context: str,
    user_name: str,
) -> str:
    """Send a voice transcript to Gemini REST API and get a brief spoken response."""
    if not settings.gemini_api_key:
        return "Gemini API key not configured."

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nCurrent context for {user_name}:\n{context}"

    # Build contents from history + new message
    contents = []
    for msg in history[-6:]:  # keep last 6 turns to reduce tokens
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": transcript}]})

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 150},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GEMINI_URL,
                params={"key": settings.gemini_api_key},
                json=payload,
            )
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            logger.error(f"Gemini error {resp.status_code}: {resp.text}")
            return "Give me a second — just hit a snag. Try again."
    except Exception as e:
        logger.error(f"Gemini request failed: {e}")
        return "I ran into an issue. Try again in a moment."
