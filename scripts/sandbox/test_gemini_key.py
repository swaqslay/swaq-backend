import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY", "")

def test_gemini_api():
    try:
        print("Testing Google Core Gemini API with the provided API key...")
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say 'API connection successful!'",
        )
        print("\n================ SUCCESS ================")
        print(response.text)
        print("=========================================")

    except Exception as e:
        print("\n================ ERROR ================")
        print(f"Something went wrong:\n{e}")
        print("=======================================")

if __name__ == "__main__":
    test_gemini_api()
