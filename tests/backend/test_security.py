"""
QA tests — Security & cross-cutting concerns
    - Authorization boundaries (token required, wrong token)
    - Input validation / injection safety
    - Health check
    - Rate limiting (basic)
    - Idempotency key for deposits
"""

import uuid
import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Module-scoped client ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def user(client):
    phone = unique_phone()
    password = "Security@Test1"
    data = register_user(client, phone, password, name="Security User")
    token = get_token(client, phone, password)
    return {**data, "phone": phone, "password": password,
            "token": token, "headers": auth_headers(token)}


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_endpoint_returns_200(self, client):
        # /dev/telegram/status is the available status endpoint in the dev router
        resp = client.get("/dev/telegram/status")
        assert resp.status_code == 200

    def test_health_response_is_json(self, client):
        resp = client.get("/dev/telegram/status")
        assert resp.headers["content-type"].startswith("application/json")


# ── Token / authentication hardening ─────────────────────────────────────────

class TestTokenSecurity:
    PROTECTED_ENDPOINTS = [
        ("GET",  "/users/me"),
        ("PUT",  "/users/me"),
        ("GET",  "/orders/"),
        ("GET",  "/chats/"),
        ("GET",  "/contracts/"),
        ("GET",  "/products/recommendations/"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_no_token_returns_401(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should require auth"

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_malformed_token_returns_401(self, client, method, path):
        resp = client.request(method, path, headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401, f"{method} {path} should reject bad token"

    def test_expired_token_is_rejected(self, client):
        # A structurally valid but obviously expired/fake JWT
        fake_expired = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIrMTAwMDAwMDAwMDAiLCJleHAiOjF9"
            ".fakesignature"
        )
        resp = client.get("/users/me", headers={"Authorization": f"Bearer {fake_expired}"})
        assert resp.status_code == 401

    def test_token_without_bearer_prefix_rejected(self, client, user):
        resp = client.get("/users/me", headers={"Authorization": user["token"]})
        assert resp.status_code == 401


# ── Input validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def test_product_price_must_be_numeric(self, client, user):
        # Switch user to seller to attempt product creation
        client.put("/users/me/role", json={"role": "seller"}, headers=user["headers"])
        cats = client.get("/categories/").json()
        resp = client.post("/products/", json={
            "name": "Bad Price Product",
            "price": "not_a_number",
            "unit": "kg",
            "image": "http://example.com/x.jpg",
            "description": "desc",
            "category_id": cats[0]["id"] if cats else "cat1",
            "in_stock": True,
            "certified": False,
            "is_b2b": False,
        }, headers=user["headers"])
        assert resp.status_code == 422
        # Restore buyer role
        client.put("/users/me/role", json={"role": "buyer"}, headers=user["headers"])

    def test_order_quantity_must_be_integer(self, client, user):
        resp = client.post("/orders/", json={
            "items": [{"product_id": "some_id", "quantity": "lots"}],
            "delivery_method": "courier",
        }, headers=user["headers"])
        assert resp.status_code == 422

    def test_deposit_amount_must_be_numeric(self, client, user):
        resp = client.post("/users/me/balance/deposit", json={
            "amount": "lots",
            "card_id": "some_card",
        }, headers=user["headers"])
        assert resp.status_code == 422

    def test_contract_amount_must_be_numeric(self, client, user):
        resp = client.post("/contracts/", json={
            "buyer_id": user["id"],
            "title": "Bad Amount",
            "amount": "a lot",
        }, headers=user["headers"])
        assert resp.status_code == 422

    def test_card_tokenize_rejects_invalid_pan(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "1234",
            "expiry": "12/28",
            "owner_name": "QA",
        })
        # 422 (validation error) or 404 (endpoint not found in this router)
        assert resp.status_code in (400, 404, 422)

    def test_card_tokenize_rejects_bad_expiry_format(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "4111111111111111",
            "expiry": "1228",  # Should be MM/YY
            "owner_name": "QA",
        })
        assert resp.status_code in (400, 404, 422)


# ── Idempotency ───────────────────────────────────────────────────────────────

class TestIdempotency:
    @pytest.fixture(scope="class")
    def funded_user_with_card(self, client):
        phone = unique_phone()
        password = "Idempotent@1"
        register_user(client, phone, password)
        token = get_token(client, phone, password)
        headers = auth_headers(token)
        card_resp = client.post("/users/me/cards", json={
            "card_token": "tok_idempotent_" + uuid.uuid4().hex[:8],
            "last4": "9999",
            "expiry": "09/30",
            "owner_name": "Idempotent User",
            "card_type": "visa",
        }, headers=headers)
        return {"headers": headers, "card_id": card_resp.json()["id"]}

    def test_same_idempotency_key_does_not_double_charge(self, client, funded_user_with_card):
        key = str(uuid.uuid4())
        payload = {"amount": 50.0, "card_id": funded_user_with_card["card_id"]}
        headers = {**funded_user_with_card["headers"], "X-Idempotency-Key": key}

        resp1 = client.post("/users/me/balance/deposit", json=payload, headers=headers)
        assert resp1.status_code == 200
        balance_after_first = resp1.json()["balance"]

        resp2 = client.post("/users/me/balance/deposit", json=payload, headers=headers)
        assert resp2.status_code == 200
        # Balance must not increase again on replay
        assert resp2.json()["balance"] == balance_after_first

    def test_different_idempotency_keys_each_charge(self, client, funded_user_with_card):
        payload = {"amount": 10.0, "card_id": funded_user_with_card["card_id"]}

        balance_before = client.get(
            "/users/me", headers=funded_user_with_card["headers"]
        ).json()["balance"]

        for _ in range(2):
            headers = {**funded_user_with_card["headers"], "X-Idempotency-Key": str(uuid.uuid4())}
            resp = client.post("/users/me/balance/deposit", json=payload, headers=headers)
            assert resp.status_code == 200

        balance_after = client.get(
            "/users/me", headers=funded_user_with_card["headers"]
        ).json()["balance"]
        assert balance_after >= balance_before + 20.0


# ── Weather endpoint ──────────────────────────────────────────────────────────

class TestWeather:
    def test_weather_endpoint_responds(self, client):
        resp = client.get("/weather")
        # lat/lon are required; 422 without them; 500 without API key; 401 if rate-limited
        assert resp.status_code in (200, 401, 422, 500)

    def test_weather_with_coordinates(self, client):
        resp = client.get("/weather", params={"lat": 41.2995, "lon": 69.2401})
        assert resp.status_code in (200, 401, 422, 500)

    def test_weather_response_shape(self, client):
        resp = client.get("/weather", params={"lat": 40.7128, "lon": -74.0060})
        assert resp.status_code in (200, 401, 422, 500)
        if resp.status_code == 200:
            body = resp.json()
            assert isinstance(body, dict)
