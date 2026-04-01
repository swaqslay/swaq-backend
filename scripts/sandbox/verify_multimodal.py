import asyncio
import os
from app.services.ai_food_recognizer import AIFoodRecognizer
from dotenv import load_dotenv

load_dotenv()

async def verify():
    print("Testing multimodal input: Image + Text Notes")
    recognizer = AIFoodRecognizer()
    
    # Read food.jpg
    image_path = "food.jpg"
    if not os.path.exists(image_path):
        print(f"{image_path} not found.")
        return
        
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        
    user_notes = "This is a strictly vegan alternative, pretend it's completely plant-based."
    print(f"User Notes passed to the model: {user_notes}\n")
    
    try:
        result = await recognizer.analyze_food_image_with_nutrition(
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            notes=user_notes
        )
        print("Success! Response from AI:")
        print(result.get("food_items", []))
    except Exception as e:
        print(f"Error during AI call: {e}")
    finally:
        await recognizer.close()

if __name__ == "__main__":
    asyncio.run(verify())
