"""Tests for AI food recognizer — mocking external API calls."""

from unittest.mock import AsyncMock, patch, PropertyMock

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.services.ai_food_recognizer import AIFoodRecognizer

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


# ── Gemini provider tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gemini_success():
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock,
    ):
        mock.return_value = MOCK_RECOGNITION_RESULT
        result = await recognizer.analyze_food_image(b"fake_image_bytes", "image/jpeg")

    assert mock.call_count == 1
    assert result["food_items"][0]["name"] == "chicken biryani"
    assert len(result["food_items"]) == 1


@pytest.mark.asyncio
async def test_gemini_vision_fails_raises_error():
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    recognizer.groq_api_key = ""  # disable fallback
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock_gemini,
    ):
        mock_gemini.side_effect = Exception("Gemini down")

        with pytest.raises(ServiceUnavailableError):
            await recognizer.analyze_food_image(b"fake", "image/jpeg")


# ── Groq provider tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_groq_success():
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "groq"
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_groq", new_callable=AsyncMock) as mock,
    ):
        mock.return_value = {**MOCK_RECOGNITION_RESULT, "_ai_provider": "groq", "_ai_model": "llama-3.2-90b-vision-preview"}
        result = await recognizer.analyze_food_image(b"fake_image_bytes", "image/jpeg")

    assert mock.call_count == 1
    assert result["food_items"][0]["name"] == "chicken biryani"
    assert result["_ai_provider"] == "groq"


@pytest.mark.asyncio
async def test_groq_vision_fails_falls_back_to_gemini():
    """If Groq fails and Gemini is configured, fallback to Gemini."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "groq"
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_groq", new_callable=AsyncMock) as mock_groq,
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock_gemini,
    ):
        mock_groq.side_effect = Exception("Groq down")
        mock_gemini.return_value = {**MOCK_RECOGNITION_RESULT, "_ai_provider": "gemini", "_ai_model": "gemini-2.0-flash-001"}
        result = await recognizer.analyze_food_image(b"fake", "image/jpeg")

    assert mock_groq.call_count == 1
    assert mock_gemini.call_count == 1
    assert result["_ai_provider"] == "gemini"


@pytest.mark.asyncio
async def test_gemini_fails_falls_back_to_groq():
    """If Gemini is primary and fails, fallback to Groq."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock) as mock_gemini,
        patch.object(recognizer, "_analyze_with_groq", new_callable=AsyncMock) as mock_groq,
    ):
        mock_gemini.side_effect = Exception("Gemini down")
        mock_groq.return_value = {**MOCK_RECOGNITION_RESULT, "_ai_provider": "groq", "_ai_model": "llama-3.2-90b-vision-preview"}
        result = await recognizer.analyze_food_image(b"fake", "image/jpeg")

    assert mock_gemini.call_count == 1
    assert mock_groq.call_count == 1
    assert result["_ai_provider"] == "groq"


@pytest.mark.asyncio
async def test_all_providers_fail_raises_error():
    """If both providers fail, raises ServiceUnavailableError."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    with (
        patch("app.services.ai_food_recognizer.preprocess_image", return_value=(b"processed", "image/jpeg")),
        patch.object(recognizer, "_analyze_with_gemini", new_callable=AsyncMock, side_effect=Exception("fail")),
        patch.object(recognizer, "_analyze_with_groq", new_callable=AsyncMock, side_effect=Exception("fail")),
    ):
        with pytest.raises(ServiceUnavailableError):
            await recognizer.analyze_food_image(b"fake", "image/jpeg")


# ── Combined call tests ───────────────────────────────────────────────────────

MOCK_COMBINED_RESULT = {
    "food_items": [
        {
            "name": "chicken biryani",
            "confidence": 0.92,
            "estimated_portion": "1 bowl",
            "estimated_weight_g": 300,
            "calories": 555,
            "protein_g": 31,
            "carbs_g": 59,
            "fat_g": 22,
            "fiber_g": 2.4,
            "vitamins": [],
            "minerals": [],
        },
    ],
    "meal_description": "Chicken biryani with raita",
    "cuisine_type": "Indian",
}


@pytest.mark.asyncio
async def test_combined_gemini_success():
    """Combined call returns food items with nutrition in one call."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    with (
        patch(
            "app.services.ai_food_recognizer.preprocess_image",
            return_value=(b"processed", "image/jpeg"),
        ),
        patch.object(
            recognizer, "_combined_gemini", new_callable=AsyncMock
        ) as mock_combined,
    ):
        mock_combined.return_value = MOCK_COMBINED_RESULT
        result = await recognizer.analyze_food_image_with_nutrition(b"fake", "image/jpeg")

    assert mock_combined.call_count == 1
    assert result["food_items"][0]["calories"] == 555
    assert result["food_items"][0]["protein_g"] == 31


@pytest.mark.asyncio
async def test_combined_groq_success():
    """Combined call via Groq returns food items with nutrition."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "groq"
    with (
        patch(
            "app.services.ai_food_recognizer.preprocess_image",
            return_value=(b"processed", "image/jpeg"),
        ),
        patch.object(
            recognizer, "_combined_groq", new_callable=AsyncMock
        ) as mock_combined,
    ):
        mock_combined.return_value = {**MOCK_COMBINED_RESULT, "_ai_provider": "groq", "_ai_model": "llama-3.2-90b-vision-preview"}
        result = await recognizer.analyze_food_image_with_nutrition(b"fake", "image/jpeg")

    assert mock_combined.call_count == 1
    assert result["food_items"][0]["calories"] == 555
    assert result["_ai_provider"] == "groq"


@pytest.mark.asyncio
async def test_combined_falls_back_to_two_step():
    """If combined call returns no nutrition data, falls back to two-step."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    incomplete_result = {
        "food_items": [
            {
                "name": "rice",
                "confidence": 0.9,
                "estimated_portion": "1 bowl",
                "estimated_weight_g": 200,
            }
        ],
        "meal_description": "Rice",
        "cuisine_type": "Indian",
    }
    with (
        patch(
            "app.services.ai_food_recognizer.preprocess_image",
            return_value=(b"processed", "image/jpeg"),
        ),
        patch.object(
            recognizer,
            "_combined_gemini",
            new_callable=AsyncMock,
            return_value=incomplete_result,
        ),
        # Also mock the Groq variant since it will be tried as fallback
        patch.object(
            recognizer,
            "_combined_groq",
            new_callable=AsyncMock,
            return_value=incomplete_result,
        ),
        patch.object(
            recognizer, "_two_step_fallback", new_callable=AsyncMock
        ) as mock_fallback,
    ):
        mock_fallback.return_value = {
            **MOCK_COMBINED_RESULT,
            "_ai_provider": "gemini",
            "_ai_model": "gemini-2.0-flash-001",
        }
        result = await recognizer.analyze_food_image_with_nutrition(b"fake", "image/jpeg")

    mock_fallback.assert_called_once()
    assert result["food_items"][0]["calories"] == 555


@pytest.mark.asyncio
async def test_combined_all_fail_raises():
    """If combined + two-step all fail, raises ServiceUnavailableError."""
    recognizer = AIFoodRecognizer()
    recognizer.ai_provider = "gemini"
    with (
        patch(
            "app.services.ai_food_recognizer.preprocess_image",
            return_value=(b"processed", "image/jpeg"),
        ),
        patch.object(
            recognizer,
            "_combined_gemini",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ),
        patch.object(
            recognizer,
            "_combined_groq",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ),
        patch.object(
            recognizer,
            "_two_step_fallback",
            new_callable=AsyncMock,
            side_effect=ServiceUnavailableError("all failed", "AI_ALL_PROVIDERS_FAILED"),
        ),
    ):
        with pytest.raises(ServiceUnavailableError):
            await recognizer.analyze_food_image_with_nutrition(b"fake", "image/jpeg")


# ── Utility tests ─────────────────────────────────────────────────────────────


def test_has_nutrition_data_with_nutrition():
    """_has_nutrition_data returns True when food items have calories+protein."""
    result = {"food_items": [{"name": "rice", "calories": 200, "protein_g": 4}]}
    assert AIFoodRecognizer._has_nutrition_data(result) is True


def test_has_nutrition_data_without_nutrition():
    """_has_nutrition_data returns False when food items lack nutrition fields."""
    result = {"food_items": [{"name": "rice", "confidence": 0.9}]}
    assert AIFoodRecognizer._has_nutrition_data(result) is False


def test_has_nutrition_data_empty():
    """_has_nutrition_data returns False for empty food list."""
    assert AIFoodRecognizer._has_nutrition_data({"food_items": []}) is False


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


def test_parse_json_truncated_array():
    """Truncated JSON with missing closing ] and } should be recovered."""
    truncated = '{"food_items": [{"name": "rice", "calories": 200}, {"name": "dal", "calories": 150}'
    # Missing: ]}
    result = AIFoodRecognizer._parse_json_response(truncated)
    assert result is not None
    assert len(result["food_items"]) == 2
    assert result["food_items"][0]["name"] == "rice"
    assert result["food_items"][1]["name"] == "dal"


def test_parse_json_truncated_mid_value_no_exception():
    """Truncated mid-string — function must not raise; result is None or partial dict."""
    truncated = '{"food_items": [{"name": "chic'
    result = AIFoodRecognizer._parse_json_response(truncated)
    # Function must not raise — return value may be None or partial dict
    assert result is None or "food_items" in result


def test_parse_json_truncated_with_markdown():
    """Truncated JSON inside markdown fences should still attempt recovery."""
    truncated = '```json\n{"food_items": [{"name": "paneer", "calories": 300}'
    # Missing: ]} and closing ```
    result = AIFoodRecognizer._parse_json_response(truncated)
    assert result is not None
    assert result["food_items"][0]["name"] == "paneer"


def test_confidence_string_to_float():
    """_normalize_simple_response converts confidence strings to floats."""
    recognizer = AIFoodRecognizer
    for conf_str, expected in [("high", 0.9), ("medium", 0.7), ("low", 0.5)]:
        parsed = {
            "items": [{
                "name": "test",
                "estimated_weight_grams": 100,
                "calories": 200,
                "protein_g": 10,
                "carbs_g": 20,
                "fat_g": 5,
                "fiber_g": 2,
                "confidence": conf_str,
            }],
        }
        result = recognizer._normalize_simple_response(parsed)
        assert result["food_items"][0]["confidence"] == expected

    # Unrecognised value defaults to 0.7
    parsed_unknown = {
        "items": [{
            "name": "test",
            "estimated_weight_grams": 100,
            "calories": 200,
            "protein_g": 10,
            "carbs_g": 20,
            "fat_g": 5,
            "fiber_g": 2,
            "confidence": "unrecognised_value",
        }],
    }
    result = recognizer._normalize_simple_response(parsed_unknown)
    assert result["food_items"][0]["confidence"] == 0.7


def test_simple_prompt_empty_vitamins_minerals():
    """Normalised output has empty vitamins/minerals dicts when AI omits them."""
    parsed = {
        "items": [{
            "name": "paneer tikka",
            "hindi_name": "पनीर टिक्का",
            "estimated_portion": "6 pieces",
            "estimated_weight_grams": 200,
            "calories": 350,
            "protein_g": 22,
            "carbs_g": 8,
            "fat_g": 26,
            "fiber_g": 1,
            "confidence": "high",
        }],
        "meal_description": "Paneer tikka",
        "cuisine_type": "Indian",
        "assumptions": "Standard restaurant serving",
    }
    result = AIFoodRecognizer._normalize_simple_response(parsed)
    assert result["food_items"][0]["vitamins"] == {}
    assert result["food_items"][0]["minerals"] == {}
    assert result["food_items"][0]["estimated_weight_g"] == 200
    assert result["food_items"][0]["confidence"] == 0.9
    assert result["meal_description"] == "Paneer tikka"
