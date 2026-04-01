"""
Swaq AI — FastAPI Application Factory

Run locally:
  uvicorn app.main:app --reload --port 8000

Docs:
  http://localhost:8000/docs   (Swagger UI)
  http://localhost:8000/redoc  (ReDoc)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import SwaqError, swaq_error_handler, unhandled_error_handler
from app.core.redis import close_redis, init_redis

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Cloud Credentials Injection ───────────────────────────────────────────────
# Vercel doesn't allow secret JSON file uploads, so we store the JSON in an env
# var (.env), write it to a temporary file, and point Google SDKs to it.
if settings.google_credentials_json:
    import os
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, 'w') as f:
        f.write(settings.google_credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info(f"Starting {settings.app_name} [{settings.effective_app_env}]")
    logger.info(f"AI Provider  : {settings.ai_provider.upper()}")
    logger.info(f"Gemini API   : {'✓ configured' if settings.gemini_api_key else '✗ NOT SET'}")
    logger.info(f"Vertex AI    : {'✓ configured' if settings.google_credentials_json else '✗ NOT SET'}")
    logger.info(f"Groq API     : {'✓ configured' if settings.groq_api_key else '✗ NOT SET'}")
    logger.info(f"OpenRouter   : {'✓ configured' if settings.openrouter_api_key else '✗ NOT SET'}")
    logger.info(f"USDA API     : {'✓ configured' if settings.usda_api_key else '✗ NOT SET'}")
    logger.info(
        f"Redis        : {'✓ configured' if settings.redis_url else '✗ not set (caching disabled)'}"
    )
    logger.info(
        f"R2 Storage   : {'✓ configured' if settings.cloudflare_r2_endpoint else '✗ not set (images not stored)'}"
    )

    try:
        await init_db()
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")

    try:
        await init_redis()
    except Exception as exc:
        logger.error(f"Failed to initialize Redis: {exc}")

    logger.info("Startup sequence complete.")

    yield  # Application is running

    await close_redis()
    logger.info("Shutdown complete.")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Swaq AI",
    description=(
        "AI-Powered Food Photo Nutrition Analyzer.\n\n"
        "Snap a meal photo → get instant calorie, macro, vitamin & mineral breakdown "
        "with BMI-based personalized daily targets and recommendations.\n\n"
        "**Health disclaimer**: Nutritional estimates are approximate and not a "
        "substitute for professional medical or dietary advice."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject OWASP-recommended security headers on every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── CORS ──────────────────────────────────────────────────────────────────────
# Handle '*' origin with credentials restriction (FastAPI requirement)
cors_origins = settings.cors_origin_list
allow_all = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else cors_origins,
    allow_credentials=not allow_all,  # can't use * with credentials
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(SwaqError, swaq_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Health endpoints ──────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    return {"app": settings.app_name, "version": "1.0.0", "status": "running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    """Basic health check — always returns 200 if the process is running."""
    return {
        "status": "healthy",
        "ai_provider": settings.ai_provider,
        "services": {
            "gemini": "configured" if settings.gemini_api_key else "missing",
            "groq": "configured" if settings.groq_api_key else "missing",
            "openrouter": "configured" if settings.openrouter_api_key else "missing",
            "usda": "configured" if settings.usda_api_key else "missing",
            "redis": "configured" if settings.redis_url else "disabled",
            "r2_storage": "configured" if settings.cloudflare_r2_endpoint else "disabled",
        },
    }


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """
    Full readiness check: verifies DB and Redis connectivity.
    Returns 503 if any critical dependency is unavailable.
    """
    from app.core.database import engine
    from app.core.redis import get_redis

    checks: dict[str, str] = {}
    all_ok = True

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        all_ok = False

    # Redis check (optional — not critical)
    redis = get_redis()
    if redis:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
    else:
        checks["redis"] = "disabled"

    # AI keys presence (not connectivity — avoids billing)
    checks["ai_provider"] = settings.ai_provider
    checks["gemini"] = "configured" if settings.gemini_api_key else "missing"
    checks["groq"] = "configured" if settings.groq_api_key else "missing"
    checks["openrouter"] = "configured" if settings.openrouter_api_key else "missing"

    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )
