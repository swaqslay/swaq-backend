import os
import vertexai
from vertexai.generative_models import GenerativeModel

# === CONFIGURATION ===
PROJECT_ID = "swaq-489621" 
LOCATION = "us-central1" 
JSON_FILE_NAME = "swaq-key.json" # The name of the file in your codebase

def setup_credentials():
    # 1. Find the folder where this Python script currently lives
    current_directory = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Build the full path to the JSON file dynamically
    json_path = os.path.join(current_directory, JSON_FILE_NAME)
    
    # 3. Check if the file actually exists to prevent confusing errors
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Could not find the credential file at: {json_path}")
        
    # 4. Set the environment variable INSIDE the script
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
    print(f"Credentials loaded dynamically from: {json_path}")

def test_vertex_connection():
    try:
        # Load the credentials first
        setup_credentials()
        
        print("\n1. Initializing Vertex AI...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        print(f"   Success: Initialized for project '{PROJECT_ID}'")
        
        print("\n2. Loading Gemini model...")
        model = GenerativeModel(model_name="gemini-2.5-flash")
        print("   Success: Model loaded")
        
        prompt = "Write a one-sentence confirmation that the API connection is working."
        print(f"\n3. Sending test prompt to Vertex AI...")
        response = model.generate_content(prompt)
        
        print("\n================ SUCCESS ================")
        print("Response from Vertex AI:")
        print(response.text.strip())
        print("=========================================")

    except Exception as e:
        print("\n================ ERROR ================")
        print(f"Something went wrong:\n{e}")
        print("=======================================")

if __name__ == "__main__":
    test_vertex_connection()