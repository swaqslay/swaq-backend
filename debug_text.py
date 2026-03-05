import asyncio
import logging
from app.services.ai_food_recognizer import AIFoodRecognizer

logging.basicConfig(level=logging.DEBUG)

async def main():
    recognizer = AIFoodRecognizer()
    try:
        # Pass a mock food item list to estimation
        items = [{"name": "Paneer Tikka"}]
        res = await recognizer.estimate_nutrition(items)
        print("RESULT:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
