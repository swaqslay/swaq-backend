import asyncio
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

async def test_vertex_with_key():
    try:
        print("Testing Vertex AI with correct API key...")
        # Actually pass the api_key this time!
        client = genai.Client(
            vertexai=True, 
            project="swaq-489621", 
            location="us-central1",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-001",
            contents="Hello, reply with exactly 'ok'.",
        )
        print("Success:", response.text)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(test_vertex_with_key())
