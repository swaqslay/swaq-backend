import sys
import asyncio

sys.path.append('e:\\swaq\\swaq_backend\\swaq-backend')

from app.api.deps import get_current_user
from app.core.exceptions import AuthenticationError

async def dummy_db():
    pass

async def test_auth(header_val):
    print(f"Testing header: '{header_val}'")
    try:
        await get_current_user(authorization=header_val, db=dummy_db())
    except AuthenticationError as e:
        print(f"-> AuthenticationError: {e.code} / {e.message}")
    except Exception as e:
        print(f"-> Other Exception: {e}")

async def main():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5YjE1MGVmZC02YzAwLTRmZDctOGUyNS04YjIyYTE2OGM3OTQiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyODg1MDc4LCJpc3MiOiJzd2FxLWFwaSJ9.RGb_zoFhUQe8cUzxv8CDUxJuvszA9_Nwa0fHLd5yBEI"
    await test_auth(f"Bearer {token}")
    await test_auth(f"Bearer Bearer {token}")

asyncio.run(main())
