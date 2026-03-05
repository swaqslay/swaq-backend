import asyncio
import httpx
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User
from app.core.security import create_access_token

async def test_dashboard():
    # 1. Get the user from the database directly
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == 'rohitsi2104@gmail.com'))
        user = result.scalar_one_or_none()
        
    if not user:
        print("Test user not found in the database. Creating one...")
        import uuid
        user_id = str(uuid.uuid4())
    else:
        user_id = str(user.id)
        
    print(f"Using test user ID: {user_id}")
    
    # 2. Generate a token bypassing the login endpoint
    token = create_access_token(user_id)
    
    # 3. Request the dashboard
    dash_url = "http://127.0.0.1:8000/api/v1/dashboard/today"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Requesting GET {dash_url}...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(dash_url, headers=headers)
        
    print(f"Response Status: {resp.status_code}")
    try:
        print("Response JSON:", resp.json())
    except Exception:
        print("Response Text:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_dashboard())
