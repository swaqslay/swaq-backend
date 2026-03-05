import requests

API_KEY = "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"

response = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {API_KEY}"})
data = response.json()

free_vision_models = []
all_free_models = []

for model in data.get("data", []):
    model_id = model["id"]
    is_free = False
    
    # Check pricing
    pricing = model.get("pricing", {})
    if float(pricing.get("prompt", 1)) == 0 and float(pricing.get("completion", 1)) == 0:
        is_free = True
    
    if "free" in model_id.lower() or is_free:
        all_free_models.append(model_id)
        # Often architecture describes multimodel support
        arch = model.get("architecture", {})
        if arch and arch.get("modality") == "text+image->text":
            free_vision_models.append(model_id)

print(f"Total free models found: {len(all_free_models)}")
print("\nLikely Vision Models:")
for m in set(free_vision_models):
    print(m)

print("\nOther free models with 'vl', 'vision', or 'gemini' in name:")
for m in all_free_models:
    if "vl" in m.lower() or "vision" in m.lower() or "gemini" in m.lower():
        print(m)
