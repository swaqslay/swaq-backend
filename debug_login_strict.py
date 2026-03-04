import asyncio
from sqlalchemy import select
from app.core.database import engine, async_session
from app.models.user import User

async def debug_login():
    async with async_session() as db:
        try:
            email = "test@example.com"
            print(f"Executing select for {email}...")
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            print(f"COMPLETE: User found: {user}")
        except Exception as e:
            import traceback
            print("LOGIN QUERY FAILED:")
            traceback.print_exc()
    await engine.dispose() # Properly close engine

if __name__ == "__main__":
    asyncio.run(debug_login())
