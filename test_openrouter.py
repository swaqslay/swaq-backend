import requests
import json
import base64

API_KEY = "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"

# Create a small dummy image
from PIL import Image
import io
img = Image.new('RGB', (100, 100), color = 'red')
buf = io.BytesIO()
img.save(buf, format='JPEG')
b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")
image_data_url = f"data:image/jpeg;base64,{b64_image}"

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={"Authorization": f"Bearer {API_KEY}"},
  json={
    "model": "nvidia/nemotron-3-nano-30b-a3b:free", 
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "What color is this image?"},
          {"type": "image_url", "image_url": {"url": image_data_url}}
        ]
      }
    ]
  }
)

print(f"Status: {response.status_code}")
try:
    print(json.dumps(response.json(), indent=2))
except:
    print(response.text)
