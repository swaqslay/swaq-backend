import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

async def run():
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        response = await client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="}}
                ]
            }],
        )
        with open("scout_test_out.txt", "w", encoding="utf-8") as f:
            f.write(response.choices[0].message.content)
    except Exception as e:
        with open("scout_test_out.txt", "w", encoding="utf-8") as f:
            f.write(str(e))

if __name__ == "__main__":
    asyncio.run(run())
