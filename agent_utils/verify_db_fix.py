import os
import asyncio
import logging
from sqlalchemy import text

# Simulate Vercel environment
os.environ["VERCEL"] = "1"

# Force reload settings or ensure they are loaded
from app.core.database import get_db, init_db

logging.basicConfig(level=logging.INFO)

async def verify():
    print("Testing database connection with Vercel simulation (psycopg sync-in-thread + ClientCursor)...")
    try:
        await init_db()
        
        async for db in get_db():
            # Run a raw SQL query with parameters
            email = "rohitsi2104@gmail.com"
            print(f"Executing raw query for email: {email}")
            result = await db.execute(text("SELECT email FROM users WHERE email = :email"), {"email": email})
            row = result.fetchone()
            print(f"Query successful. Found: {row[0] if row else 'None'}")
            
            # Run it again to check for prepared statement reuse conflict
            print("Executing query again to check for collisions...")
            result = await db.execute(text("SELECT email FROM users WHERE email = :email"), {"email": email})
            row = result.fetchone()
            print("Second query successful.")
            break
            
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
