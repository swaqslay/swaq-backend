import asyncio
from sqlalchemy import select
from app.core.database import async_session
from app.models.user import User
from app.api.v1.auth import login
from app.schemas.auth import UserLogin
from pydantic import ValidationError

async def debug_login():
    async with async_session() as db:
        try:
            # We don't need real password verification to see if the DB query fails
            email = "test@example.com" # or any email the user is using
            print(f"Executing select for {email}...")
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            print(f"User found: {user}")
        except Exception as e:
            import traceback
            print("LOGIN QUERY FAILED:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_login())
