import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"OpenRouter: FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
