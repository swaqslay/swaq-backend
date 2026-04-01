import asyncio
import logging
from app.services.ai_food_recognizer import AIFoodRecognizer

logging.basicConfig(level=logging.DEBUG)

async def main():
    recognizer = AIFoodRecognizer()
    try:
        with open('paneer_tikka.jpg', 'rb') as f:
            image_bytes = f.read()
        res = await recognizer.analyze_food_image(image_bytes, "image/jpeg")
        print("RESULT:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
