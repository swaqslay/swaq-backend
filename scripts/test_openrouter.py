#!/usr/bin/env python3
"""Quick connectivity test for OpenRouter API."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.openrouter_api_key:
        print("✗ OPENROUTER_API_KEY not set in .env")
        return

    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.openrouter_api_key)

    try:
        resp = await client.chat.completions.create(
            model="qwen/qwen3-235b-a22b:free",
            messages=[{"role": "user", "content": "Reply with exactly: {\"status\": \"ok\"}"}],
            temperature=0,
            max_tokens=20,
        )
        text = resp.choices[0].message.content
        print(f"✓ OpenRouter OK: {text.strip()}")
    except Exception as exc:
        print(f"✗ OpenRouter failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
