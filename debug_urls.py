from app.core.config import get_settings
from app.core.database import _db_url

settings = get_settings()
print(f"Original URL: {settings.database_url}")
print(f"Built URL: {_db_url}")
