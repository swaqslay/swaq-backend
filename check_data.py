import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    url = os.getenv("DATABASE_URL")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(url)
        count = await conn.fetchval("SELECT count(*) FROM users")
        print(f"User count: {count}")
        await conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check())
