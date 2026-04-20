"""
Shared fixtures for the UDX backend integration test suite.

Prerequisites:
    pip install pytest httpx

Usage:
    cd tests/backend
    pytest -v

Environment variables (optional):
    API_URL   — override base URL (default: http://localhost:8000)

NOTE: These are integration tests — the backend must be running before you run them.

    Terminal 1:
        cd /path/to/UDX
        python -m uvicorn backend.main:app --reload --port 8000

    Terminal 2:
        cd tests/backend
        pytest -v
"""

import uuid
import os
import pytest
import httpx

BASE_URL = os.getenv("API_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Connectivity guard — skip the entire suite if the server is not reachable
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Check backend reachability once at collection time."""
    try:
        httpx.get(f"{BASE_URL}/health", timeout=5)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.TimeoutException,
            httpx.RemoteProtocolError, OSError):
        config._backend_unreachable = True
    else:
        config._backend_unreachable = False


@pytest.fixture(autouse=True, scope="function")
def require_backend(request):
    # Unit testlar (pytest.mark.unit) server talab qilmaydi — skip qilinmaydi
    if request.node.get_closest_marker("unit"):
        return
    if getattr(request.config, "_backend_unreachable", False):
        pytest.skip(
            f"Backend not reachable at {BASE_URL}. "
            "Start the server first:\n"
            "  cd android_app/backend && uvicorn main:app --reload --port 8000"
        )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def unique_phone() -> str:
    """Return a unique phone string so tests never collide."""
    return f"+1{uuid.uuid4().int % 10_000_000_000:010d}"


def register_user(client: httpx.Client, phone: str, password: str, role: str = "buyer", name: str = "Test User") -> dict:
    # OTP bypass — faqat dev muhitida (ENVIRONMENT != production)
    client.post("/dev/verify-phone", params={"phone": phone})
    resp = client.post("/users/", json={"phone": phone, "password": password, "role": role, "name": name})
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    return resp.json()


def get_token(client: httpx.Client, phone: str, password: str) -> str:
    resp = client.post("/token", data={"username": phone, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Session-scoped client (one per test session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


# ---------------------------------------------------------------------------
# Buyer fixture — registered + authenticated
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def buyer(client):
    phone = unique_phone()
    password = "Buyer@12345"
    register_user(client, phone, password, role="buyer", name="QA Buyer")
    token = get_token(client, phone, password)
    return {"phone": phone, "password": password, "token": token, "headers": auth_headers(token)}


# ---------------------------------------------------------------------------
# Seller fixture — registered + authenticated
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seller(client):
    phone = unique_phone()
    password = "Seller@12345"
    register_user(client, phone, password, role="seller", name="QA Seller")
    token = get_token(client, phone, password)
    return {"phone": phone, "password": password, "token": token, "headers": auth_headers(token)}


# ---------------------------------------------------------------------------
# A product created by the seller — reused across product/order/contract tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seller_product(client, seller):
    # Ensure a category exists first
    cats = client.get("/categories/").json()
    category_id = cats[0]["id"] if cats else "test-cat"

    resp = client.post(
        "/products/",
        json={
            "name": "QA Test Tomatoes",
            "price": 2.50,
            "unit": "kg",
            "image": "http://example.com/tomato.jpg",
            "description": "Fresh red tomatoes for QA",
            "category_id": category_id,
            "in_stock": True,
            "certified": False,
            "is_b2b": False,
        },
        headers=seller["headers"],
    )
    assert resp.status_code == 200, f"Product creation failed: {resp.text}"
    return resp.json()
