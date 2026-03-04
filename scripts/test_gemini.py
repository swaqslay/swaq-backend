#!/usr/bin/env python3
"""Quick connectivity test for Gemini API."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.gemini_api_key:
        print("✗ GEMINI_API_KEY not set in .env")
        return

    import httpx
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": "Say 'Swaq AI is alive!' in JSON: {\"message\": \"...\"}"}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 50, "responseMimeType": "application/json"},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"✓ Gemini OK: {text.strip()}")
    except Exception as exc:
        print(f"✗ Gemini failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
