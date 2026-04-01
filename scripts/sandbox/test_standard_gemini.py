import asyncio
import os
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

async def test_standard_gemini():
    print("Testing Standard Gemini API with current key (Waiting 6 seconds to clear RPM limit)...")
    time.sleep(6)
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents="Hello, reply with exactly 'ok'.",
        )
        print("Success:", response.text)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(test_standard_gemini())
