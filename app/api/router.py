"""
Central router aggregator.
All API routes are registered here and included in main.py.
"""

from fastapi import APIRouter

from app.api.v1 import auth, dashboard, meals, profile

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(meals.router)
api_router.include_router(dashboard.router)
