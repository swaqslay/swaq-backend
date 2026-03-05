import asyncio
import httpx
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

async def test_gemini():
    print(f"\n--- Testing Gemini ({GEMINI_API_KEY[:6]}...) ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": "Say hello!"}]}]
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                print("Gemini: SUCCESS")
                # print(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
            else:
                print(f"Gemini: FAILED ({resp.status_code})")
                print(resp.text)
        except Exception as e:
            print(f"Gemini: ERROR: {e}")

async def test_openrouter():
    print(f"\n--- Testing OpenRouter ({OPENROUTER_API_KEY[:6]}...) ---")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    try:
        response = await client.chat.completions.create(
            model="openrouter/free",
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=10
        )
        print("OpenRouter: SUCCESS")
        # print(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenRouter: FAILED: {e}")

async def main():
    await test_gemini()
    await test_openrouter()

if __name__ == "__main__":
    asyncio.run(main())
