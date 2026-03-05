import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_dashboard():
    # Attempt login to get token
    login_url = "http://127.0.0.1:8000/api/v1/auth/login"
    login_data = {
        "email": "rohitsi2104@gmail.com",
        "password": "Password1!"  # Trying typical password, though we may need a new test user
    }
    
    async with httpx.AsyncClient() as client:
        print("1. Attempting login...")
        resp = await client.post(login_url, json=login_data)
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code}")
            print(resp.text)
            
            print("\nRegistering a test user instead...")
            resp = await client.post("http://127.0.0.1:8000/api/v1/auth/register", json={
                "email": "testdashboard@example.com",
                "name": "Test User",
                "password": "Password123!"
            })
            if resp.status_code != 201 and resp.status_code != 200:
                print(f"Registration failed: {resp.status_code}")
                # Try login again if it existed
                resp = await client.post(login_url, json={"email": "testdashboard@example.com", "password": "Password123!"})

        if resp.status_code not in [200, 201]:
            print("Could not get auth token")
            return
            
        data = resp.json()
        token = data.get("data", {}).get("access_token")
        if not token:
            print("No token in response:", data)
            return
            
        print("2. Requesting /dashboard/today...")
        dash_url = "http://127.0.0.1:8000/api/v1/dashboard/today"
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = await client.get(dash_url, headers=headers)
        print(f"Dashboard Response: {resp.status_code}")
        print(resp.json())

if __name__ == "__main__":
    asyncio.run(test_dashboard())
