"""Tests for profile endpoints and BMI/target calculation."""

import pytest
from httpx import AsyncClient


PROFILE_DATA = {
    "age": 25,
    "gender": "male",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "activity_level": "moderate",
    "health_goal": "maintain",
}


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/profile/", json=PROFILE_DATA, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    # BMI = 70 / (1.75^2) = 22.9
    assert data["bmi"] == pytest.approx(22.9, abs=0.1)
    assert data["bmi_category"] == "Normal weight"
    assert data["daily_calorie_target"] > 0
    assert data["daily_protein_target_g"] > 0


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers: dict):
    # No profile yet
    resp = await client.get("/api/v1/profile/", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PROFILE_NOT_FOUND"

    # Create then get
    await client.post("/api/v1/profile/", json=PROFILE_DATA, headers=auth_headers)
    resp = await client.get("/api/v1/profile/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["age"] == 25


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/profile/", json=PROFILE_DATA, headers=auth_headers)
    resp = await client.patch("/api/v1/profile/", json={"weight_kg": 75.0}, headers=auth_headers)
    assert resp.status_code == 200
    # New BMI = 75 / (1.75^2) = 24.5
    assert resp.json()["data"]["bmi"] == pytest.approx(24.5, abs=0.1)


@pytest.mark.asyncio
async def test_bmi_underweight(client: AsyncClient, auth_headers: dict):
    data = {**PROFILE_DATA, "weight_kg": 45.0, "height_cm": 175.0}
    resp = await client.post("/api/v1/profile/", json=data, headers=auth_headers)
    assert resp.json()["data"]["bmi_category"] == "Underweight"


@pytest.mark.asyncio
async def test_bmi_overweight(client: AsyncClient, auth_headers: dict):
    data = {**PROFILE_DATA, "weight_kg": 90.0, "height_cm": 175.0}
    resp = await client.post("/api/v1/profile/", json=data, headers=auth_headers)
    assert resp.json()["data"]["bmi_category"] == "Overweight"


@pytest.mark.asyncio
async def test_bmi_obese(client: AsyncClient, auth_headers: dict):
    data = {**PROFILE_DATA, "weight_kg": 110.0, "height_cm": 165.0}
    resp = await client.post("/api/v1/profile/", json=data, headers=auth_headers)
    assert resp.json()["data"]["bmi_category"] == "Obese"


@pytest.mark.asyncio
async def test_lose_weight_goal_reduces_calories(client: AsyncClient, auth_headers: dict):
    maintain = {**PROFILE_DATA, "health_goal": "maintain"}
    lose = {**PROFILE_DATA, "health_goal": "lose_weight"}
    r1 = await client.post("/api/v1/profile/", json=maintain, headers=auth_headers)
    r2 = await client.post("/api/v1/profile/", json=lose, headers=auth_headers)
    cal_maintain = r1.json()["data"]["daily_calorie_target"]
    cal_lose = r2.json()["data"]["daily_calorie_target"]
    assert cal_lose == cal_maintain - 500


@pytest.mark.asyncio
async def test_female_bmr_lower_than_male(client: AsyncClient, auth_headers: dict, auth_headers_2: dict):
    male_data = {**PROFILE_DATA, "gender": "male"}
    female_data = {**PROFILE_DATA, "gender": "female"}
    r_male = await client.post("/api/v1/profile/", json=male_data, headers=auth_headers)
    r_female = await client.post("/api/v1/profile/", json=female_data, headers=auth_headers_2)
    assert r_male.json()["data"]["daily_calorie_target"] > r_female.json()["data"]["daily_calorie_target"]
