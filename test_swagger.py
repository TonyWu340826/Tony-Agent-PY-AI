import requests
import time

url = "http://localhost:8889/api/chat/active/load-swagger"
params = {
    "swagger_url": "http://localhost:8889/openapi.json"
}

try:
    print("Sending request to load Swagger...")
    response = requests.post(url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()