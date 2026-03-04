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
        # Check alembic_version table
        try:
            version = await conn.fetchval("SELECT version_num FROM alembic_version")
            print(f"Current DB revision: {version}")
        except Exception:
            print("alembic_version table not found or empty.")
            
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        print(f"Tables: {[t['table_name'] for t in tables]}")
        await conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check())
