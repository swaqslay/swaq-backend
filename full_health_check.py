import httpx
import json

def check():
    try:
        response = httpx.get("http://localhost:8000/health/ready", timeout=10.0)
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    check()
