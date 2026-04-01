import sys
import os
from google import genai

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'e:\\swaq\\swaq_backend\\swaq-backend\\swaq-key.json'
project = 'swaq-489621'
location = 'us-central1'
try:
    print("Testing Vertex AI with gemini-2.0-flash-001...")
    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents='Hello, this is a test.'
    )
    print('Success gemini-2.0-flash-001:', response.text)
except Exception as e:
    print('FULL_ERROR gemini-2.0-flash-001:', str(e))

try:
    print("Testing Vertex AI with gemini-1.5-flash...")
    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='Hello, this is a test.'
    )
    print('Success gemini-1.5-flash:', response.text)
except Exception as e:
    print('FULL_ERROR gemini-1.5-flash:', str(e))
