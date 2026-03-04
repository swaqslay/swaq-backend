"""Tests for AI food recognizer — mocking external API calls."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_food_recognizer import AIFoodRecognizer
from app.core.exceptions import ServiceUnavailableError


MOCK_RECOGNITION_RESULT = {
    "food_items": [
        {"name": "chicken biryani", "confidence": 0.92, "estimated_portion": "1 bowl", "estimated_weight_g": 300},
    ],
    "meal_description": "Chicken biryani with raita",
    "cuisine_type": "Indian",
}

MOCK_NUTRITION_RESULT = {
    "food_items": [
        {
            "name": "chicken biryani",
            "estimated_weight_g": 300,
            "calories": 555,
            "protein_g": 31,
            "carbs_g": 59,
            "fat_g": 22,
            "fiber_g": 2.4,
            "vitamins": [],
            "minerals": [],
        }
    ]
}


@pytest.mark.asyncio
async def test_gemini_success():
    recognizer = AIFoodRecognizer()
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock,
    ):
        mock.return_value = MOCK_RECOGNITION_RESULT
        result = await recognizer.analyze_food_image(b"fake_image_bytes", "image/jpeg")
    assert result["_ai_provider"] == "gemini"
    assert result["_ai_model"] == "gemini-2.0-flash"
    assert len(result["food_items"]) == 1


@pytest.mark.asyncio
async def test_gemini_fails_falls_back_to_openrouter():
    recognizer = AIFoodRecognizer()
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock_gemini,
        patch.object(recognizer, "_analyze_with_openrouter", new_callable=AsyncMock) as mock_or,
    ):
        mock_gemini.side_effect = Exception("Gemini 429 rate limit")
        or_result = {**MOCK_RECOGNITION_RESULT, "_ai_provider": "openrouter", "_ai_model": "qwen/qwen3-vl-30b-a3b:free"}
        mock_or.return_value = or_result

        result = await recognizer.analyze_food_image(b"fake", "image/jpeg")

    assert result["_ai_provider"] == "openrouter"


@pytest.mark.asyncio
async def test_all_providers_fail_raises_error():
    recognizer = AIFoodRecognizer()
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock_g,
        patch.object(recognizer, "_analyze_with_openrouter", new_callable=AsyncMock) as mock_or,
    ):
        mock_g.side_effect = Exception("Gemini down")
        mock_or.side_effect = Exception("OpenRouter down")

        with pytest.raises(ServiceUnavailableError):
            await recognizer.analyze_food_image(b"fake", "image/jpeg")


def test_parse_json_clean():
    result = AIFoodRecognizer._parse_json_response('{"food_items": []}')
    assert result == {"food_items": []}


def test_parse_json_with_markdown():
    text = '```json\n{"food_items": []}\n```'
    result = AIFoodRecognizer._parse_json_response(text)
    assert result == {"food_items": []}


def test_parse_json_invalid():
    result = AIFoodRecognizer._parse_json_response("This is not JSON at all!")
    assert result is None


def test_parse_json_empty():
    result = AIFoodRecognizer._parse_json_response("")
    assert result is None
