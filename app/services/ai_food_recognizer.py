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

from openai import AsyncOpenAI
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import ai_all_providers_failed
from app.utils.constants import MAX_IMAGE_DIMENSION_PX
from app.utils.prompts import (
    FOOD_RECOGNITION_SYSTEM_PROMPT,
    FOOD_RECOGNITION_USER_PROMPT,
    NUTRITION_ESTIMATION_PROMPT,
    SIMPLE_COMBINED_PROMPT,
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

    # Strip EXIF by copying pixel data without metadata (fast path)
    clean_img = img.copy()
    clean_img.info = {}
    if hasattr(clean_img, "_exif"):
        del clean_img._exif

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
    clean_img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"


class AIFoodRecognizer:
    """
    Handles food recognition from images using AI vision models.
    Strictly uses meta-llama/llama-4-maverick-17b-128e-instruct via Groq API.
    """

    def __init__(self):
        self.groq_api_key = settings.groq_api_key

    async def close(self) -> None:
        """No persistent httpx client needed for AsyncOpenAI wrapper."""
        pass

    async def analyze_food_image_with_nutrition(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> dict:
        """
        Combined single-call: identify food items AND estimate nutrition in one AI call.
        Falls back to the two-step pipeline if the combined response is incomplete.

        Returns:
            dict with keys: food_items (with nutrition), meal_description, cuisine_type,
                            _ai_provider, _ai_model
        """
        processed_bytes, processed_mime = preprocess_image(image_bytes, mime_type)

        try:
            result = await self._combined_groq(processed_bytes, processed_mime)
            if result and self._has_nutrition_data(result):
                logger.info(
                    f"Combined recognition+nutrition succeeded via Groq"
                    f" ({result.get('_ai_model')})"
                )
                return result
        except Exception as exc:
            logger.warning(f"Groq combined call failed: {exc}")

        # Fallback: two-step pipeline
        logger.info("Combined call failed/incomplete, falling back to two-step pipeline")
        return await self._two_step_fallback(image_bytes, mime_type)

    async def _two_step_fallback(self, image_bytes: bytes, mime_type: str) -> dict:
        """Run the two-step pipeline: vision -> nutrition."""
        recognition = await self.analyze_food_image(image_bytes, mime_type)
        raw_items = recognition.get("food_items", [])
        if not raw_items:
            return recognition
        nutrition_result = await self.estimate_nutrition(raw_items)
        nutrition_items = nutrition_result.get("food_items", []) if nutrition_result else raw_items
        recognition["food_items"] = nutrition_items
        return recognition

    @staticmethod
    def _normalize_simple_response(parsed: dict) -> dict:
        """Convert SIMPLE_COMBINED_PROMPT schema to internal food_items format."""
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        raw_items = parsed.get("items", [])
        food_items = []
        for item in raw_items:
            food_items.append({
                "name": item.get("name", "unknown"),
                "hindi_name": item.get("hindi_name", ""),
                "estimated_portion": item.get("estimated_portion", "1 serving"),
                "estimated_weight_g": item.get("estimated_weight_grams", item.get("estimated_weight_g", 100)),
                "calories": item.get("calories", 0),
                "protein_g": item.get("protein_g", 0),
                "carbs_g": item.get("carbs_g", 0),
                "fat_g": item.get("fat_g", 0),
                "fiber_g": item.get("fiber_g", 0),
                "confidence": confidence_map.get(str(item.get("confidence", "medium")).lower(), 0.7),
                "vitamins": {},
                "minerals": {},
            })
        return {
            "food_items": food_items,
            "meal_description": parsed.get("meal_description", ""),
            "cuisine_type": parsed.get("cuisine_type", ""),
            "assumptions": parsed.get("assumptions", ""),
        }

    @staticmethod
    def _has_nutrition_data(result: dict) -> bool:
        """Check if food items include nutrition fields (calories, protein_g, etc.)."""
        items = result.get("food_items", [])
        if not items:
            return False
        first = items[0]
        return "calories" in first and "protein_g" in first

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """
        Main entry point: preprocess image and identify food items.
        Uses Groq vision API exclusively.

        Returns:
            dict with keys: food_items, meal_description, cuisine_type,
                            _ai_provider, _ai_model

        Raises:
            ServiceUnavailableError: If Groq fails.
        """
        processed_bytes, processed_mime = preprocess_image(image_bytes, mime_type)

        try:
            result = await self._analyze_with_groq(processed_bytes, processed_mime)
            if result:
                logger.info(
                    f"Food recognition succeeded via Groq ({result.get('_ai_model')})"
                )
                return result
        except Exception as exc:
            logger.error(f"Groq vision model failed: {exc}")

        raise ai_all_providers_failed()

    async def estimate_nutrition(self, food_items: list[dict]) -> dict:
        """
        Given identified food items, estimate nutrition.
        Uses text-only Groq API call.

        Returns:
            dict with key food_items, each containing full macro + micro nutrition.

        Raises:
            ServiceUnavailableError: If Groq fails.
        """
        prompt = NUTRITION_ESTIMATION_PROMPT.format(
            food_items_json=json.dumps(food_items, indent=2)
        )

        try:
            result = await self._text_query_groq(prompt)
            if result:
                return result
        except Exception as exc:
            logger.error(f"Groq nutrition estimation failed: {exc}")

        raise ai_all_providers_failed()

    # ── Groq implementations ──────────────────────────────────────────────────

    async def _analyze_with_groq(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Call Groq vision API."""
        if not self.groq_api_key:
            logger.debug("GROQ_API_KEY not set, skipping Groq")
            return None

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{mime_type};base64,{b64_image}"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": FOOD_RECOGNITION_SYSTEM_PROMPT
                        + "\n\n"
                        + FOOD_RECOGNITION_USER_PROMPT,
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ]

        async with AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.groq_api_key,
        ) as client:
            try:
                response = await client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=messages,
                    temperature=0.15,
                    max_tokens=1024,
                )
                text = response.choices[0].message.content
                result = self._parse_json_response(text)
                if result:
                    result["_ai_provider"] = "groq"
                    result["_ai_model"] = "meta-llama/llama-4-maverick-17b-128e-instruct"
                    return result
            except Exception as exc:
                logger.warning(f"Groq vision model failed: {exc}")
                raise exc

        return None

    async def _text_query_groq(self, prompt: str) -> dict | None:
        """Text-only Groq call for nutrition estimation."""
        if not self.groq_api_key:
            return None

        async with AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.groq_api_key,
        ) as client:
            try:
                response = await client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.15,
                    max_tokens=8192,
                )
                text = response.choices[0].message.content
                result = self._parse_json_response(text)
                if result:
                    return result
            except Exception as exc:
                logger.warning(f"Groq text model failed: {exc}")
                raise exc

        return None

    async def _combined_groq(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Single Groq call for recognition + nutrition."""
        if not self.groq_api_key:
            logger.debug("GROQ_API_KEY not set, skipping Groq combined")
            return None

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{mime_type};base64,{b64_image}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SIMPLE_COMBINED_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ]

        async with AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.groq_api_key,
        ) as client:
            try:
                response = await client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=messages,
                    temperature=0.15,
                    max_tokens=1000,
                )
                text = response.choices[0].message.content
                parsed = self._parse_json_response(text)
                if parsed is not None:
                    result = self._normalize_simple_response(parsed)
                    result["_ai_provider"] = "groq"
                    result["_ai_model"] = "meta-llama/llama-4-maverick-17b-128e-instruct"
                    return result
            except Exception as exc:
                logger.warning(f"Groq combined model failed: {exc}")
                raise exc

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
            while repaired and repaired[-1] not in '{}[],"0123456789':
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
