import asyncio
import os
from sqlalchemy import text
from app.core.database import engine, async_session
from dotenv import load_dotenv

load_dotenv()

async def test_raw():
    try:
        async with engine.connect() as conn:
            print("Connecting...")
            result = await conn.execute(text("SELECT email FROM users LIMIT 1"))
            row = result.fetchone()
            print(f"SUCCESS! Found user: {row[0] if row else 'None'}")
    except Exception as e:
        import traceback
        print("RAW QUERY FAILED:")
        traceback.print_exc()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_raw())
