import asyncio
import logging
import os
from PIL import Image
from app.services.ai_food_recognizer import AIFoodRecognizer
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)

# Allow standard get_settings() to load the Gemini API key

async def main():
    if not os.path.exists("paneer_tikka.jpg"):
        print("Creating a dummy orange image since download failed...")
        img = Image.new('RGB', (400, 400), color = (255, 120, 0))
        img.save('paneer_tikka.jpg')

    with open("paneer_tikka.jpg", "rb") as f:
        image_bytes = f.read()

    print(f"Loaded image. Size: {len(image_bytes)} bytes")
    recognizer = AIFoodRecognizer()
    
    print("Sending image to AIFoodRecognizer...")
    result = await recognizer.analyze_food_image(image_bytes, "image/jpeg")
    
    print("\n--- RECOGNITION RESULT ---")
    import json
    print(json.dumps(result, indent=2))
    
    if result.get("food_items"):
        print("\nSending items for Nutrition Estimation...")
        nutrition = await recognizer.estimate_nutrition(result["food_items"])
        print("\n--- NUTRITION RESULT ---")
        print(json.dumps(nutrition, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
