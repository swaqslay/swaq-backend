import asyncio
import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

async def test_gemini():
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        print("Testing Gemini...")
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=[types.Part.from_text(text="Hi, reply with exactly 'ok' in JSON: {\"status\": \"ok\"}")],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        print("Gemini response:", response.text)
    except Exception as e:
        print("Gemini error:", repr(e))

async def test_groq():
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
        print(f"Testing Groq with model {model}...")
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi, reply with exactly 'ok' in JSON: {\"status\": \"ok\"}"}],
            response_format={"type": "json_object"}
        )
        print("Groq response:", response.choices[0].message.content)
    except Exception as e:
        print("Groq error:", repr(e))

async def run():
    print("Testing Providers...")
    await test_gemini()
    print("-" * 40)
    await test_groq()

if __name__ == "__main__":
    asyncio.run(run())
