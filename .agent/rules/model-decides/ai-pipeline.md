# AI Pipeline Rules — Swaq AI Backend

Load this file when working on food recognition, Gemini/OpenRouter integration, or prompt engineering.

## 1. Two-Step Architecture

Food recognition is split into TWO separate AI calls:

**Step 1 — Visual Identification** (vision model):
- Input: Food photo (base64 encoded)
- Output: List of food items + estimated portions + confidence scores
- Requires vision-capable model

**Step 2 — Nutrition Estimation** (text-only):
- Input: List of identified food items with portions from Step 1
- Output: Complete nutritional profile (calories, macros, vitamins, minerals)
- Enhanced by USDA FoodData Central lookup for known foods

## 2. Provider Priority

### Vision Models (Step 1)
1. `gemini-2.0-flash` (Google, free tier: 15 RPM, 1000 RPD)
2. `qwen/qwen3-vl-30b-a3b:free` (OpenRouter)
3. `google/gemma-3-27b-it:free` (OpenRouter)
4. `nvidia/nemotron-nano-2-vl:free` (OpenRouter)
5. `openrouter/free` (auto-select)

### Text Models (Step 2)
1. `gemini-2.0-flash` (Google)
2. `qwen/qwen3-235b-a22b:free` (OpenRouter)
3. `google/gemma-3-27b-it:free` (OpenRouter)
4. `openrouter/free` (auto-select)

## 3. Prompt Requirements

Prompts live in `app/utils/prompts.py`. They MUST:
1. Start with a system role defining the AI as an expert food nutritionist
2. Demand JSON-only output — no markdown, no explanation, no backticks
3. Specify the exact JSON schema the response must follow
4. Include Indian food examples (dal, roti, biryani, paneer, dosa, idli, sambar)
5. Use low temperature (0.15) for consistent structured output
6. Use Gemini's `responseMimeType: "application/json"` to force JSON mode

## 4. Image Preprocessing

Before sending to AI:
1. Validate: JPEG, PNG, or WebP only. Max 10MB
2. Resize: If longest edge > 1536px, resize to 1536px
3. Convert: Always send as base64 with correct MIME type
4. EXIF: Strip EXIF data for privacy

## 5. JSON Response Parsing

- Parse AI response as JSON
- Validate against expected schema (list of food items with nutrition fields)
- If JSON parsing fails: log the raw response, try next provider
- If food list is empty: raise `MEAL_SCAN_FAILED`
- Store AI metadata on meal record: `ai_provider`, `ai_model`, `ai_confidence_avg`

## 6. Gemini SDK Usage

Use the `google-genai` Python SDK — **do NOT make raw REST calls via `httpx`** to the Gemini API.

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)

response = await client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=contents,
    config=types.GenerateContentConfig(
        temperature=0.15,
        max_output_tokens=4096,
        response_mime_type="application/json",
    ),
)
```

Key settings:
- **Model**: `gemini-2.0-flash`
- **Temperature**: `0.15` (low — consistent structured output)
- **Max output tokens**: `4096`
- **Response MIME type**: `application/json` (forces JSON mode)

## 7. OpenRouter API

```
Base URL: https://openrouter.ai/api/v1
API format: OpenAI-compatible (same client code as GPT)
Temperature: 0.15
Max tokens: 4096
```

## 8. Tracked Nutrients

Per food item, track:
- **Macros**: calories, protein_g, carbs_g, fat_g, fiber_g
- **Vitamins**: A (mcg), B6 (mg), B12 (mcg), C (mg), D (mcg), Folate (mcg)
- **Minerals**: Calcium (mg), Iron (mg), Magnesium (mg), Potassium (mg), Sodium (mg), Zinc (mg)
