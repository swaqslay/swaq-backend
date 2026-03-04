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
