"""
Swaq AI — Application Configuration
Loads all settings from environment variables using Pydantic v2 Settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "Swaq AI"
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # ── Vercel Overrides ──────────────────────────────────────────────────────
    @property
    def effective_app_env(self) -> str:
        """Force production mode on Vercel."""
        import os

        if "VERCEL" in os.environ:
            return "production"
        return self.app_env

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # ── Business rules ────────────────────────────────────────────────────────
    free_daily_scan_limit: int = 3

    # ── AI APIs ───────────────────────────────────────────────────────────────
    ai_provider: str = "gemini"  # "gemini" or "groq"
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # ── Nutrition DB ──────────────────────────────────────────────────────────
    usda_api_key: str = ""

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = ""

    # ── Backblaze B2 (active image storage) ──────────────────────────────────
    backblaze_b2_endpoint: str = ""  # e.g. https://s3.us-west-004.backblazeb2.com
    backblaze_b2_access_key: str = ""  # Application Key ID
    backblaze_b2_secret_key: str = ""  # Application Key
    backblaze_b2_bucket: str = "swaq-images"
    backblaze_b2_region: str = ""  # e.g. us-west-004

    # ── Cloudflare R2 (reserved for future use) ───────────────────────────────
    cloudflare_r2_endpoint: str = ""
    cloudflare_r2_access_key: str = ""
    cloudflare_r2_secret_key: str = ""
    cloudflare_r2_bucket: str = "swaq-images"

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.effective_app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
