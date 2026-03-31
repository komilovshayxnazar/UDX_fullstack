from fastapi.testclient import TestClient
from main import app

if __name__ == "__main__":
    try:
        with TestClient(app) as client:
            response = client.get("/docs")
            print("Docs status:", response.status_code)
    except Exception as e:
        import traceback
        traceback.print_exc()
