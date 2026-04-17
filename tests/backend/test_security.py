"""
QA tests — Security & cross-cutting concerns

Qamrab olinganlar:
  1. Health check          — /health endpoint
  2. Token / auth          — 401 chegaralar, expired/bad JWT
  3. Input validation      — Pydantic 422, PAN/expiry format
  4. NoSQL injection       — $gt/$ne operatorlari bloklangan
  5. Sensitive data        — hashed_password, phone_hash javobda yo'q
  6. Rate limiting         — 5 to'lov/min → 429
  7. Oversized payload     — katta JSON body
  8. XSS attempt           — <script> matnda saqlanadi, lekin "xavfli" emas
  9. Idempotency           — double-charge oldini olish
  10. CORS headers          — kerakli headerlar mavjud
"""

import uuid
import json
import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        yield c


@pytest.fixture(scope="module")
def user(client):
    phone, password = unique_phone(), "Security@Test1"
    data = register_user(client, phone, password, name="Security User")
    token = get_token(client, phone, password)
    return {**data, "phone": phone, "password": password,
            "token": token, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def seller(client):
    phone, password = unique_phone(), "Seller@Sec1"
    register_user(client, phone, password, role="seller", name="Sec Seller")
    token = get_token(client, phone, password)
    return {"headers": auth_headers(token)}


@pytest.fixture(scope="module")
def user_with_card(client, user):
    tok = client.post("/payments/tokenize", json={
        "card_number": "4111111111111111",
        "expiry": "12/28",
        "owner_name": "Security User",
    }).json()
    card = client.post("/users/me/cards", json={
        "owner_name": tok["owner_name"],
        "last4": tok["last4"],
        "expiry": tok["expiry"],
        "card_type": tok["card_type"],
        "card_token": tok["card_token"],
    }, headers=user["headers"]).json()
    return {**user, "card_id": card["id"]}


# ── 1. Health check ───────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_endpoint_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_has_status_field(self, client):
        body = client.get("/health").json()
        assert "status" in body
        assert body["status"] in ("ok", "degraded")

    def test_health_includes_all_services(self, client):
        services = client.get("/health").json()["services"]
        assert "mongodb" in services
        assert "redis" in services
        assert "storage" in services

    def test_mongodb_healthy(self, client):
        services = client.get("/health").json()["services"]
        assert services["mongodb"] == "ok"

    def test_health_is_json(self, client):
        resp = client.get("/health")
        assert resp.headers["content-type"].startswith("application/json")


# ── 2. Token / authentication ─────────────────────────────────────────────────

class TestTokenSecurity:
    PROTECTED = [
        ("GET",  "/users/me"),
        ("PUT",  "/users/me"),
        ("GET",  "/orders/"),
        ("GET",  "/chats/"),
        ("GET",  "/contracts/"),
        ("GET",  "/products/recommendations/"),
        ("GET",  "/payments/transactions"),
        ("GET",  "/payments/audit"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED)
    def test_no_token_returns_401(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} — auth talab qilinmadi"

    @pytest.mark.parametrize("method,path", PROTECTED)
    def test_bad_token_returns_401(self, client, method, path):
        resp = client.request(method, path,
                              headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert resp.status_code == 401

    def test_expired_jwt_rejected(self, client):
        # exp=1 (1970-da o'tib ketgan)
        expired = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIrMTAwMDAwMDAwMDAiLCJleHAiOjF9"
            ".fakesignature"
        )
        resp = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401

    def test_token_without_bearer_prefix_rejected(self, client, user):
        resp = client.get("/users/me", headers={"Authorization": user["token"]})
        assert resp.status_code == 401

    def test_empty_auth_header_rejected(self, client):
        resp = client.get("/users/me", headers={"Authorization": ""})
        assert resp.status_code == 401

    def test_bearer_only_no_token_rejected(self, client):
        resp = client.get("/users/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401


# ── 3. Input validation ───────────────────────────────────────────────────────

class TestInputValidation:
    def test_product_price_must_be_float(self, client, seller):
        cats = client.get("/categories/").json()
        resp = client.post("/products/", json={
            "name": "Bad Price", "price": "free", "unit": "kg",
            "image": "http://x.com/x.jpg", "description": "d",
            "category_id": cats[0]["id"], "in_stock": True,
            "certified": False, "is_b2b": False,
        }, headers=seller["headers"])
        assert resp.status_code == 422

    def test_order_quantity_string_rejected(self, client, user):
        resp = client.post("/orders/", json={
            "items": [{"product_id": "abc", "quantity": "much"}],
            "delivery_method": "courier",
        }, headers=user["headers"])
        assert resp.status_code == 422

    def test_deposit_amount_string_rejected(self, client, user):
        resp = client.post("/users/me/balance/deposit",
                           json={"amount": "lots", "card_id": "x"},
                           headers=user["headers"])
        assert resp.status_code == 422

    def test_contract_amount_string_rejected(self, client, user):
        resp = client.post("/contracts/", json={
            "buyer_id": user["id"], "title": "T", "amount": "a lot",
        }, headers=user["headers"])
        assert resp.status_code == 422

    def test_invalid_pan_too_short_rejected(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "1234",
            "expiry": "12/28",
            "owner_name": "QA",
        })
        assert resp.status_code == 422

    def test_invalid_pan_non_digits_rejected(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "abcd-efgh-ijkl-mnop",
            "expiry": "12/28",
            "owner_name": "QA",
        })
        assert resp.status_code == 422

    def test_expiry_wrong_format_rejected(self, client):
        # MM/YY o'rniga MMYY
        resp = client.post("/payments/tokenize", json={
            "card_number": "4111111111111111",
            "expiry": "1228",
            "owner_name": "QA",
        })
        assert resp.status_code == 422

    def test_expiry_letters_rejected(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "4111111111111111",
            "expiry": "AB/CD",
            "owner_name": "QA",
        })
        assert resp.status_code == 422

    def test_valid_16_digit_visa_accepted(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "4111111111111111",
            "expiry": "12/28",
            "owner_name": "Valid User",
        })
        assert resp.status_code == 200

    def test_valid_15_digit_amex_accepted(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "378282246310005",
            "expiry": "12/28",
            "owner_name": "Amex User",
        })
        assert resp.status_code == 200


# ── 4. NoSQL injection ────────────────────────────────────────────────────────

class TestNoSQLInjection:
    """
    MongoDB operator injection urinishlari.
    Pydantic str validatsiyasi ularni 422 bilan bloklashi kerak.
    """

    def test_login_operator_injection_blocked(self, client):
        """{"$gt": ""} parol sifatida → 422 (Pydantic str kutadi)."""
        resp = client.post("/token", data={
            "username": "+998901234567",
            "password": '{"$gt": ""}',
        })
        # 401 (noto'g'ri parol) yoki 422 (validation) — ikkalasi ham to'g'ri
        assert resp.status_code in (401, 422)

    def test_product_name_injection_blocked(self, client, seller):
        """Mahsulot nomida MongoDB operator → saqlanadi yoki 422."""
        cats = client.get("/categories/").json()
        resp = client.post("/products/", json={
            "name": '{"$where": "sleep(1000)"}',
            "price": 1.0, "unit": "kg",
            "image": "http://x.com/x.jpg", "description": "d",
            "category_id": cats[0]["id"],
            "in_stock": True, "certified": False, "is_b2b": False,
        }, headers=seller["headers"])
        # 200 (string sifatida saqlandi) yoki 422 — ikkalasi ham xavfsiz
        assert resp.status_code in (200, 422)

    def test_registration_phone_injection(self, client):
        """Telefon raqamida injection → 422 yoki 400."""
        resp = client.post("/users/", json={
            "phone": '{"$ne": null}',
            "password": "Valid@Pass1",
            "role": "buyer",
            "name": "Injector",
        })
        assert resp.status_code in (400, 422)

    def test_search_injection_safe(self, client):
        """Qidiruv parametrida regex injection — xavfli emas."""
        resp = client.get("/products/", params={"q": ".*"})
        assert resp.status_code == 200  # 500 bo'lmasligi kerak

    def test_object_id_injection(self, client):
        """Noto'g'ri ObjectId formatida so'rov — 404 yoki 422."""
        resp = client.get('/products/{"$gt":""}')
        assert resp.status_code in (404, 422)


# ── 5. Sensitive data exposure ────────────────────────────────────────────────

class TestSensitiveData:
    def test_hashed_password_not_in_response(self, client, user):
        body = client.get("/users/me", headers=user["headers"]).json()
        assert "hashed_password" not in body
        assert "password" not in body

    def test_phone_hash_not_in_response(self, client, user):
        body = client.get("/users/me", headers=user["headers"]).json()
        assert "phone_hash" not in body

    def test_encryption_key_not_in_response(self, client, user):
        body_str = json.dumps(client.get("/users/me", headers=user["headers"]).json())
        assert "enc:" not in body_str  # shifrlangan format ko'rinmasligi kerak

    def test_card_token_not_exposed_in_card_list(self, client, user_with_card):
        cards = client.get("/users/me/cards", headers=user_with_card["headers"]).json()
        for card in cards:
            assert "card_token" not in card, "card_token ochiq ko'rinmasin"

    def test_full_pan_not_in_any_response(self, client, user_with_card):
        """4111111111111111 hech qayerda ko'rinmasligi kerak."""
        body_str = json.dumps(
            client.get("/users/me", headers=user_with_card["headers"]).json()
        )
        assert "4111111111111111" not in body_str

    def test_public_profile_hides_private_fields(self, client, user):
        profile = client.get(f"/users/{user['id']}/public")
        if profile.status_code == 200:
            body = profile.json()
            assert "phone" not in body
            assert "balance" not in body
            assert "hashed_password" not in body


# ── 6. Rate limiting ──────────────────────────────────────────────────────────

class TestRateLimiting:
    def test_payment_rate_limit_enforced(self, client, user_with_card):
        """6-inchi to'lov so'rovi → 429 (limit: 5/min)."""
        payload = {"amount": 1.0, "card_id": user_with_card["card_id"]}
        responses = []
        for _ in range(6):
            r = client.post(
                "/payments/deposit",
                json=payload,
                headers={**user_with_card["headers"],
                         "X-Idempotency-Key": str(uuid.uuid4())},
            )
            responses.append(r.status_code)

        # Kamida bitta 429 bo'lishi kerak
        assert 429 in responses, (
            f"Rate limit ishlamadi. Barcha statuslar: {responses}"
        )

    def test_tokenization_rate_limit(self, client):
        """21-inchi tokenizatsiya → 429 (limit: 20/min)."""
        responses = []
        payload = {"card_number": "4111111111111111",
                   "expiry": "12/28", "owner_name": "Rate Test"}
        for _ in range(21):
            r = client.post("/payments/tokenize", json=payload)
            responses.append(r.status_code)
            if r.status_code == 429:
                break

        assert 429 in responses, (
            f"Tokenizatsiya rate limit ishlamadi. Statuslar: {responses}"
        )


# ── 7. Oversized payload ──────────────────────────────────────────────────────

class TestOversizedPayload:
    def test_large_product_description_rejected_or_truncated(self, client, seller):
        cats = client.get("/categories/").json()
        big_desc = "A" * 100_000  # 100 KB matn
        resp = client.post("/products/", json={
            "name": "Big Desc",
            "price": 1.0, "unit": "kg",
            "image": "http://x.com/x.jpg",
            "description": big_desc,
            "category_id": cats[0]["id"],
            "in_stock": True, "certified": False, "is_b2b": False,
        }, headers=seller["headers"])
        # 200 (qabul qilindi) yoki 413/422 (rad etildi) — 500 bo'lmasligi kerak
        assert resp.status_code != 500

    def test_very_long_search_query_safe(self, client):
        long_q = "x" * 10_000
        resp = client.get("/products/", params={"q": long_q})
        assert resp.status_code != 500

    def test_many_order_items_handled(self, client, user):
        items = [{"product_id": "fake_id", "quantity": 1}] * 200
        resp = client.post("/orders/", json={
            "items": items, "delivery_method": "courier",
        }, headers=user["headers"])
        # 404 (mahsulot yo'q) yoki 422 — 500 bo'lmasligi kerak
        assert resp.status_code != 500


# ── 8. XSS attempt ───────────────────────────────────────────────────────────

class TestXSSPrevention:
    """
    API JSON qaytaradi (HTML emas), shuning uchun XSS payload
    string sifatida saqlanishi to'g'ri. Muhim narsa: server 500
    bermaydi va Content-Type text/html bo'lmasin.
    """

    def test_xss_in_product_name_stored_safely(self, client, seller):
        cats = client.get("/categories/").json()
        xss = "<script>alert('xss')</script>"
        resp = client.post("/products/", json={
            "name": xss, "price": 1.0, "unit": "kg",
            "image": "http://x.com/x.jpg", "description": "d",
            "category_id": cats[0]["id"],
            "in_stock": True, "certified": False, "is_b2b": False,
        }, headers=seller["headers"])
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.headers["content-type"].startswith("application/json")

    def test_xss_in_user_name(self, client):
        phone, password = unique_phone(), "XSS@Test123"
        resp = client.post("/users/", json={
            "phone": phone,
            "password": password,
            "role": "buyer",
            "name": "<img src=x onerror=alert(1)>",
        })
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.headers["content-type"].startswith("application/json")

    def test_response_content_type_always_json(self, client):
        for path in ["/products/", "/categories/", "/health"]:
            resp = client.get(path)
            if resp.status_code == 200:
                assert "json" in resp.headers["content-type"], \
                    f"{path} JSON qaytarmadi"


# ── 9. Idempotency ────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_same_key_no_double_charge(self, client, user_with_card):
        key = str(uuid.uuid4())
        payload = {"amount": 50.0, "card_id": user_with_card["card_id"]}
        headers = {**user_with_card["headers"], "X-Idempotency-Key": key}

        r1 = client.post("/payments/deposit", json=payload, headers=headers)
        assert r1.status_code == 200
        balance_after_first = r1.json()["balance"]

        r2 = client.post("/payments/deposit", json=payload, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["balance"] == balance_after_first

    def test_different_keys_both_charge(self, client, user_with_card):
        before = client.get("/users/me",
                            headers=user_with_card["headers"]).json()["balance"]
        payload = {"amount": 10.0, "card_id": user_with_card["card_id"]}
        for _ in range(2):
            client.post("/payments/deposit", json=payload, headers={
                **user_with_card["headers"],
                "X-Idempotency-Key": str(uuid.uuid4()),
            })
        after = client.get("/users/me",
                           headers=user_with_card["headers"]).json()["balance"]
        assert after >= before + 20.0


# ── 10. CORS ──────────────────────────────────────────────────────────────────

class TestCORS:
    def test_cors_header_present_for_allowed_origin(self, client):
        resp = client.get("/health",
                          headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" in resp.headers

    def test_preflight_options_returns_200(self, client):
        resp = client.options("/products/", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.status_code in (200, 204)

    def test_cors_allows_authorization_header(self, client):
        resp = client.options("/users/me", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        })
        if resp.status_code in (200, 204):
            allow_headers = resp.headers.get(
                "access-control-allow-headers", ""
            ).lower()
            assert "authorization" in allow_headers
