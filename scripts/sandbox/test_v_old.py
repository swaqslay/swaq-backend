import os
import vertexai
from vertexai.generative_models import GenerativeModel

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'e:\\swaq\\swaq_backend\\swaq-backend\\swaq-key.json'

try:
    vertexai.init(project="swaq-489621", location="us-central1")
    model = GenerativeModel("gemini-1.5-flash-001")
    response = model.generate_content("Hello")
    print("SUCCESS vertexai library:", response.text)
except Exception as e:
    print("ERROR vertexai library:", str(e))
