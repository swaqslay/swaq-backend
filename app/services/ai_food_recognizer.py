"""
AI Food Recognition Service
- Primary: Google Gemini 2.0 Flash (free tier)
- Fallback: OpenRouter free vision models (Qwen3-VL, Gemma 3, etc.)

Both are free. Gemini is tried first (faster, higher quality).
If Gemini fails (rate limit / downtime), OpenRouter is tried automatically.

Also handles image preprocessing: EXIF stripping, resize to 1536px max.
"""

import base64
import json
import logging
from io import BytesIO

import httpx
from openai import AsyncOpenAI
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import ai_all_providers_failed
from app.utils.constants import MAX_IMAGE_DIMENSION_PX
from app.utils.prompts import (
    FOOD_RECOGNITION_SYSTEM_PROMPT,
    FOOD_RECOGNITION_USER_PROMPT,
    NUTRITION_ESTIMATION_PROMPT,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def preprocess_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """
    Prepare an image for AI analysis:
    1. Strip EXIF metadata (privacy — removes GPS location data).
    2. Resize if longest edge > 1536px (saves tokens, no quality loss).
    3. Convert to JPEG for consistent encoding.

    Returns:
        Tuple of (processed_bytes, effective_mime_type).
    """
    img = Image.open(BytesIO(image_bytes))

    # Strip EXIF by re-creating a clean image (no metadata)
    clean_img = Image.new(img.mode, img.size)
    clean_img.putdata(list(img.getdata()))

    # Resize if too large
    max_dim = MAX_IMAGE_DIMENSION_PX
    if max(clean_img.size) > max_dim:
        clean_img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        logger.debug(f"Resized image to {clean_img.size}")

    # Ensure RGB (convert RGBA/P to RGB for JPEG compatibility)
    if clean_img.mode not in ("RGB", "L"):
        clean_img = clean_img.convert("RGB")

    # Save as JPEG
    buf = BytesIO()
    clean_img.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"


class AIFoodRecognizer:
    """
    Handles food recognition from images using AI vision models.
    Implements automatic fallback: Gemini → OpenRouter models (4 attempts).
    """

    # OpenRouter free vision models (tried in order)
    OPENROUTER_VISION_MODELS = [
        "google/gemini-2.5-flash:free",
        "google/gemini-2.0-flash-001:free",
        "openai/gpt-4o-mini:free",
        "openrouter/free",
    ]

    OPENROUTER_TEXT_MODELS = [
        "google/gemini-2.5-flash:free",
        "deepseek/deepseek-v3.2-20251201:free",
        "openai/gpt-4o-mini:free",
        "openrouter/free",
    ]

    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """
        Main entry point: preprocess image and identify food items.

        Tries Gemini first, then each OpenRouter model in order.

        Returns:
            dict with keys: food_items, meal_description, cuisine_type,
                            _ai_provider, _ai_model

        Raises:
            ServiceUnavailableError: If all providers fail.
        """
        processed_bytes, processed_mime = preprocess_image(image_bytes, mime_type)

        # 1. Try Gemini (primary)
        try:
            result = await self._analyze_with_gemini(processed_bytes, processed_mime)
            if result:
                result["_ai_provider"] = "gemini"
                result["_ai_model"] = "gemini-2.0-flash"
                logger.info("Food recognition succeeded via Gemini")
                return result
        except Exception as exc:
            logger.warning(f"Gemini vision failed: {exc}")

        # 2. Fallback to OpenRouter
        try:
            result = await self._analyze_with_openrouter(processed_bytes, processed_mime)
            if result:
                logger.info(f"Food recognition succeeded via OpenRouter ({result.get('_ai_model')})")
                return result
        except Exception as exc:
            logger.error(f"All OpenRouter vision models failed: {exc}")

        raise ai_all_providers_failed()

    async def estimate_nutrition(self, food_items: list[dict]) -> dict:
        """
        Given identified food items (from analyze_food_image), estimate nutrition.
        Uses text-only AI call — cheaper and faster than vision.

        Returns:
            dict with key food_items, each containing full macro + micro nutrition.

        Raises:
            ServiceUnavailableError: If all providers fail.
        """
        prompt = NUTRITION_ESTIMATION_PROMPT.format(
            food_items_json=json.dumps(food_items, indent=2)
        )

        # 1. Try Gemini text
        try:
            result = await self._text_query_gemini(prompt)
            if result:
                return result
        except Exception as exc:
            logger.warning(f"Gemini nutrition estimation failed: {exc}")

        # 2. Fallback to OpenRouter text
        try:
            result = await self._text_query_openrouter(prompt)
            if result:
                return result
        except Exception as exc:
            logger.error(f"OpenRouter nutrition estimation failed: {exc}")

        raise ai_all_providers_failed()

    # ── Gemini implementations ────────────────────────────────────────────────

    async def _analyze_with_gemini(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Call Gemini Flash vision API via REST."""
        if not self.gemini_api_key:
            logger.debug("GEMINI_API_KEY not set, skipping Gemini")
            return None

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": FOOD_RECOGNITION_SYSTEM_PROMPT + "\n\n" + FOOD_RECOGNITION_USER_PROMPT},
                        {"inline_data": {"mime_type": mime_type, "data": b64_image}},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.15,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json_response(text)

    async def _text_query_gemini(self, prompt: str) -> dict | None:
        """Text-only Gemini call for nutrition estimation."""
        if not self.gemini_api_key:
            return None

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.15,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json_response(text)

    # ── OpenRouter implementations ────────────────────────────────────────────

    async def _analyze_with_openrouter(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Try each OpenRouter free vision model until one succeeds."""
        if not settings.openrouter_api_key:
            logger.debug("OPENROUTER_API_KEY not set, skipping OpenRouter")
            return None

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{mime_type};base64,{b64_image}"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": FOOD_RECOGNITION_SYSTEM_PROMPT + "\n\n" + FOOD_RECOGNITION_USER_PROMPT
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ]

        async with AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        ) as client:
            for model in self.OPENROUTER_VISION_MODELS:
                try:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.15,
                        max_tokens=2048,
                    )
                    text = response.choices[0].message.content
                    result = self._parse_json_response(text)
                    if result:
                        result["_ai_provider"] = "openrouter"
                        result["_ai_model"] = model
                        return result
                except Exception as exc:
                    logger.warning(f"OpenRouter vision model '{model}' failed: {exc}")

        return None

    async def _text_query_openrouter(self, prompt: str) -> dict | None:
        """Text-only OpenRouter call for nutrition estimation."""
        if not settings.openrouter_api_key:
            return None

        async with AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        ) as client:
            for model in self.OPENROUTER_TEXT_MODELS:
                try:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.15,
                        max_tokens=8192,
                    )
                    text = response.choices[0].message.content
                    result = self._parse_json_response(text)
                    if result:
                        return result
                except Exception as exc:
                    logger.warning(f"OpenRouter text model '{model}' failed: {exc}")

        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(text: str) -> dict | None:
        """
        Safely parse JSON from AI response.
        Strips markdown code fences (```json ... ```) if present.
        Attempts to recover truncated JSON by closing unclosed brackets.
        """
        if not text:
            return None

        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # 1. Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. Attempt truncated JSON recovery
        #    Count unclosed brackets and append closers
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape_next = False

        for char in cleaned:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                if in_string:
                    escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                open_braces += 1
            elif char == "}":
                open_braces -= 1
            elif char == "[":
                open_brackets += 1
            elif char == "]":
                open_brackets -= 1

        if open_braces > 0 or open_brackets > 0:
            # Strip trailing incomplete value (e.g., truncated mid-string or mid-number)
            # Find last complete JSON element delimiter
            repaired = cleaned.rstrip()
            # Remove trailing partial tokens: partial strings, numbers, etc.
            while repaired and repaired[-1] not in "{}[],\"0123456789":
                repaired = repaired[:-1]
            # If ends mid-string, remove back to the opening quote of that string
            # and the key before it (best-effort)
            if repaired and repaired[-1] == '"':
                # Likely a truncated string value or key — remove it
                repaired = repaired[:-1]
                last_quote = repaired.rfind('"')
                if last_quote >= 0:
                    repaired = repaired[:last_quote]
            # Strip trailing comma or colon (incomplete key-value)
            repaired = repaired.rstrip(", \t\n:")

            # Append closers in reverse order of what's open
            # Re-count after stripping
            open_braces = 0
            open_brackets = 0
            in_string = False
            escape_next = False
            for char in repaired:
                if escape_next:
                    escape_next = False
                    continue
                if char == "\\":
                    if in_string:
                        escape_next = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == "{":
                    open_braces += 1
                elif char == "}":
                    open_braces -= 1
                elif char == "[":
                    open_brackets += 1
                elif char == "]":
                    open_brackets -= 1

            repaired += "]" * open_brackets + "}" * open_braces

            try:
                result = json.loads(repaired)
                logger.warning("Recovered truncated AI JSON response")
                return result
            except json.JSONDecodeError:
                pass

        # 3. Unrecoverable
        logger.error(f"AI JSON parse failed | Raw (500 chars): {text[:500]}")
        return None
