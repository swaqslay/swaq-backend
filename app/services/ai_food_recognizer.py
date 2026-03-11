"""
AI Food Recognition Service
- Configurable provider via AI_PROVIDER env var:
    "gemini" → Google Gemini 2.0 Flash via google-genai SDK
    "groq"   → Groq API (Llama 4 Maverick) via groq SDK
- Automatic fallback to alternate provider on failure.
- JSON mode enforced via response_mime_type (Gemini) or response_format (Groq).

Handles image preprocessing: EXIF stripping, resize to 1536px max.
"""

import base64
import json
import logging
from io import BytesIO

from google import genai
from google.genai import types
from groq import AsyncGroq
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

GEMINI_MODEL = "gemini-2.0-flash-001"


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
    Supports Gemini (google-genai) and Groq (groq SDK).
    Active provider is selected via settings.ai_provider.
    Falls back to the alternate provider on failure.
    """

    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        self.groq_api_key = settings.groq_api_key
        self.groq_model = settings.groq_model
        self.ai_provider = settings.ai_provider.lower()

        self._gemini_client: genai.Client | None = None
        self._groq_client: AsyncGroq | None = None

    # ── Client factories ──────────────────────────────────────────────────────

    def _get_gemini_client(self) -> genai.Client:
        """Lazy-init the genai Client (reused across calls)."""
        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=self.gemini_api_key)
        return self._gemini_client

    def _get_groq_client(self) -> AsyncGroq:
        """Lazy-init the Groq async client (reused across calls)."""
        if self._groq_client is None:
            self._groq_client = AsyncGroq(api_key=self.groq_api_key)
        return self._groq_client

    async def close(self) -> None:
        """Clean up resources."""
        self._gemini_client = None
        if self._groq_client is not None:
            await self._groq_client.close()
            self._groq_client = None

    # ── Provider ordering ─────────────────────────────────────────────────────

    def _provider_order(self) -> list[str]:
        """Return [primary, fallback] based on config."""
        if self.ai_provider == "groq":
            return ["groq", "gemini"]
        return ["gemini", "groq"]

    def _has_provider_key(self, provider: str) -> bool:
        if provider == "gemini":
            return bool(self.gemini_api_key)
        if provider == "groq":
            return bool(self.groq_api_key)
        return False

    # ── High-level entry points ───────────────────────────────────────────────

    async def analyze_food_image_with_nutrition(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> dict:
        """
        Combined single-call: identify food items AND estimate nutrition in one AI call.
        Falls back to the two-step pipeline if the combined response is incomplete.
        Falls back to alternate provider if primary fails.

        Returns:
            dict with keys: food_items (with nutrition), meal_description, cuisine_type,
                            _ai_provider, _ai_model
        """
        processed_bytes, processed_mime = preprocess_image(image_bytes, mime_type)

        for provider in self._provider_order():
            if not self._has_provider_key(provider):
                continue
            try:
                combined_fn = (
                    self._combined_gemini if provider == "gemini" else self._combined_groq
                )
                result = await combined_fn(processed_bytes, processed_mime)
                if result and self._has_nutrition_data(result):
                    logger.info(
                        f"Combined recognition+nutrition succeeded via {provider}"
                        f" ({result.get('_ai_model')})"
                    )
                    return result
            except Exception as exc:
                logger.warning(f"{provider} combined call failed: {exc}")

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
        Tries primary provider, falls back to alternate.

        Returns:
            dict with keys: food_items, meal_description, cuisine_type,
                            _ai_provider, _ai_model

        Raises:
            ServiceUnavailableError: If all providers fail.
        """
        processed_bytes, processed_mime = preprocess_image(image_bytes, mime_type)

        for provider in self._provider_order():
            if not self._has_provider_key(provider):
                continue
            try:
                analyze_fn = (
                    self._analyze_with_gemini if provider == "gemini" else self._analyze_with_groq
                )
                result = await analyze_fn(processed_bytes, processed_mime)
                if result:
                    logger.info(
                        f"Food recognition succeeded via {provider} ({result.get('_ai_model')})"
                    )
                    return result
            except Exception as exc:
                logger.error(f"{provider} vision model failed: {exc}")

        raise ai_all_providers_failed()

    async def estimate_nutrition(self, food_items: list[dict]) -> dict:
        """
        Given identified food items, estimate nutrition.
        Tries primary provider, falls back to alternate.

        Returns:
            dict with key food_items, each containing full macro + micro nutrition.

        Raises:
            ServiceUnavailableError: If all providers fail.
        """
        prompt = NUTRITION_ESTIMATION_PROMPT.format(
            food_items_json=json.dumps(food_items, indent=2)
        )

        for provider in self._provider_order():
            if not self._has_provider_key(provider):
                continue
            try:
                text_fn = (
                    self._text_query_gemini if provider == "gemini" else self._text_query_groq
                )
                result = await text_fn(prompt)
                if result:
                    return result
            except Exception as exc:
                logger.error(f"{provider} nutrition estimation failed: {exc}")

        raise ai_all_providers_failed()

    # ── Gemini implementations ──────────────────────────────────────────────────

    async def _analyze_with_gemini(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Call Gemini vision API for food recognition."""
        if not self.gemini_api_key:
            logger.debug("GEMINI_API_KEY not set, skipping Gemini")
            return None

        client = self._get_gemini_client()

        prompt_text = (
            FOOD_RECOGNITION_SYSTEM_PROMPT
            + "\n\n"
            + FOOD_RECOGNITION_USER_PROMPT
        )

        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=prompt_text),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.15,
                    max_output_tokens=1024,
                ),
            )
            text = response.text
            result = self._parse_json_response(text)
            if result:
                result["_ai_provider"] = "gemini"
                result["_ai_model"] = GEMINI_MODEL
                return result
        except Exception as exc:
            logger.warning(f"Gemini vision model failed: {exc}")
            raise exc

        return None

    async def _text_query_gemini(self, prompt: str) -> dict | None:
        """Text-only Gemini call for nutrition estimation."""
        if not self.gemini_api_key:
            return None

        client = self._get_gemini_client()

        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[types.Part.from_text(text=prompt)],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.15,
                    max_output_tokens=8192,
                ),
            )
            text = response.text
            result = self._parse_json_response(text)
            if result:
                return result
        except Exception as exc:
            logger.warning(f"Gemini text model failed: {exc}")
            raise exc

        return None

    async def _combined_gemini(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Single Gemini call for recognition + nutrition."""
        if not self.gemini_api_key:
            logger.debug("GEMINI_API_KEY not set, skipping Gemini combined")
            return None

        client = self._get_gemini_client()

        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=SIMPLE_COMBINED_PROMPT),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.15,
                    max_output_tokens=1000,
                ),
            )
            text = response.text
            parsed = self._parse_json_response(text)
            if parsed is not None:
                result = self._normalize_simple_response(parsed)
                result["_ai_provider"] = "gemini"
                result["_ai_model"] = GEMINI_MODEL
                return result
        except Exception as exc:
            logger.warning(f"Gemini combined model failed: {exc}")
            raise exc

        return None

    # ── Groq implementations ────────────────────────────────────────────────────

    async def _analyze_with_groq(self, image_bytes: bytes, mime_type: str) -> dict | None:
        """Call Groq vision API for food recognition."""
        if not self.groq_api_key:
            logger.debug("GROQ_API_KEY not set, skipping Groq")
            return None

        client = self._get_groq_client()
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{b64_image}"

        prompt_text = (
            FOOD_RECOGNITION_SYSTEM_PROMPT
            + "\n\n"
            + FOOD_RECOGNITION_USER_PROMPT
        )

        try:
            response = await client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": prompt_text},
                        ],
                    }
                ],
                temperature=0.15,
                max_completion_tokens=1024,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content
            result = self._parse_json_response(text)
            if result:
                result["_ai_provider"] = "groq"
                result["_ai_model"] = self.groq_model
                return result
        except Exception as exc:
            logger.warning(f"Groq vision model failed: {exc}")
            raise exc

        return None

    async def _text_query_groq(self, prompt: str) -> dict | None:
        """Text-only Groq call for nutrition estimation."""
        if not self.groq_api_key:
            return None

        client = self._get_groq_client()

        try:
            response = await client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.15,
                max_completion_tokens=8192,
                response_format={"type": "json_object"},
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

        client = self._get_groq_client()
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{b64_image}"

        try:
            response = await client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": SIMPLE_COMBINED_PROMPT},
                        ],
                    }
                ],
                temperature=0.15,
                max_completion_tokens=1000,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content
            parsed = self._parse_json_response(text)
            if parsed is not None:
                result = self._normalize_simple_response(parsed)
                result["_ai_provider"] = "groq"
                result["_ai_model"] = self.groq_model
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
