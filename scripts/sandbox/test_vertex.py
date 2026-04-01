import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def test_vertex():
    try:
        project = "swaq-489621"
        location = "us-central1"
        
        print("Testing Vertex AI...")
        client = genai.Client(vertexai=True, project=project, location=location)
        
        response = client.models.generate_content(
            model="gemini-1.5-flash-002",
            contents="Hello, this is a test.",
        )
        print("Success:", response.text)
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    test_vertex()
