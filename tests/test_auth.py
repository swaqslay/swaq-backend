"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@swaq.app", "name": "New User", "password": "secure123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"
    assert data["data"]["user"]["email"] == "new@swaq.app"
    assert data["data"]["user"]["name"] == "New User"
    assert data["data"]["user"]["is_premium"] is False
    assert "id" in data["data"]["user"]
    assert data["data"]["profile"] is None
    assert data["data"]["profile_required"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@swaq.app", "name": "User", "password": "secure123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "AUTH_EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "x@x.com", "name": "X", "password": "short"},
    )
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@swaq.app", "name": "User", "password": "mypassword"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@swaq.app", "password": "mypassword"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]
    assert resp.json()["data"]["user"]["email"] == "login@swaq.app"
    assert resp.json()["data"]["profile"] is None
    assert resp.json()["data"]["profile_required"] is True


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "auth@swaq.app", "name": "User", "password": "correct123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "auth@swaq.app", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@swaq.app", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@swaq.app", "name": "User", "password": "refresh123"},
    )
    refresh_token = reg.json()["data"]["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


@pytest.mark.asyncio
async def test_access_protected_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/profile/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_protected_endpoint_with_invalid_token(client: AsyncClient):
    resp = await client.get("/api/v1/profile/", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_returns_profile_when_exists(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "profiled@swaq.app", "name": "Profiled User", "password": "secure123"},
    )
    token = reg.json()["data"]["access_token"]

    await client.post(
        "/api/v1/profile/",
        json={
            "age": 25,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 70,
            "activity_level": "moderate",
            "health_goal": "maintain",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "profiled@swaq.app", "password": "secure123"},
    )
    data = resp.json()["data"]
    assert data["profile"] is not None
    assert data["profile"]["age"] == 25
    assert data["profile"]["bmi"] > 0
    assert data["profile"]["bmi_category"] in ("Underweight", "Normal weight", "Overweight", "Obese")
    assert data["profile"]["daily_calorie_target"] > 0
    assert data["profile_required"] is False


@pytest.mark.asyncio
async def test_login_returns_null_profile_when_missing(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "noprofile@swaq.app", "name": "No Profile", "password": "secure123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "noprofile@swaq.app", "password": "secure123"},
    )
    data = resp.json()["data"]
    assert data["profile"] is None
    assert data["profile_required"] is True
    assert data["user"]["email"] == "noprofile@swaq.app"
