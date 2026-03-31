import requests
import json
import os

BASE_URL = os.getenv("API_URL", "http://localhost:8000")

def test_health():
    print(f"Testing Heatlh Check on {BASE_URL}/dev/health...")
    try:
        response = requests.get(f"{BASE_URL}/dev/health")
        if response.status_code == 200:
            print("✅ Health Check Passed")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")

def test_get_products():
    print(f"\nTesting Get Products on {BASE_URL}/products...")
    try:
        response = requests.get(f"{BASE_URL}/products")
        if response.status_code == 200:
            products = response.json()
            print(f"✅ Get Products Passed. Found {len(products)} products.")
        else:
            print(f"❌ Get Products Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")

def test_get_weather():
    print(f"\nTesting Get Weather on {BASE_URL}/weather...")
    try:
        # Default mock location if params empty
        response = requests.get(f"{BASE_URL}/weather")
        if response.status_code == 200:
            print("✅ Get Weather Passed")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Get Weather Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")

if __name__ == "__main__":
    test_health()
    test_get_products()
    test_get_weather()
