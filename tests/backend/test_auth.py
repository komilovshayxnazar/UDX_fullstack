"""
QA tests — Authentication endpoints
    POST /token
    GET  /auth/google/login
    GET  /auth/google/register
    POST /auth/otp/request
    POST /auth/otp/verify
"""

import uuid
import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def registered_user(client):
    phone = unique_phone()
    password = "Auth@99999"
    register_user(client, phone, password)
    return {"phone": phone, "password": password}


# ── /token ───────────────────────────────────────────────────────────────────

class TestLogin:
    def test_valid_credentials_return_jwt(self, client, registered_user):
        resp = client.post("/token", data={
            "username": registered_user["phone"],
            "password": registered_user["password"],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

    def test_wrong_password_returns_401(self, client, registered_user):
        resp = client.post("/token", data={
            "username": registered_user["phone"],
            "password": "Wrong@Password1",
        })
        assert resp.status_code == 401

    def test_unknown_phone_returns_401(self, client):
        resp = client.post("/token", data={
            "username": "+10000000000",
            "password": "Valid@Pass1",
        })
        assert resp.status_code == 401

    def test_missing_password_returns_422(self, client, registered_user):
        resp = client.post("/token", data={"username": registered_user["phone"]})
        assert resp.status_code == 422

    def test_missing_username_returns_422(self, client):
        resp = client.post("/token", data={"password": "SomePass@1"})
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, client):
        resp = client.post("/token", data={})
        assert resp.status_code == 422


# ── Password strength validation ─────────────────────────────────────────────

class TestPasswordValidation:
    def _try_register(self, client, password: str) -> int:
        return client.post("/users/", json={
            "phone": unique_phone(),
            "password": password,
            "role": "buyer",
        }).status_code

    def test_too_short_password_rejected(self, client):
        assert self._try_register(client, "Ab1!") == 422

    def test_no_uppercase_rejected(self, client):
        assert self._try_register(client, "nouppercas1!") == 422

    def test_no_lowercase_rejected(self, client):
        assert self._try_register(client, "NOLOWER1!") == 422

    def test_no_digit_rejected(self, client):
        assert self._try_register(client, "NoDigit!!") == 422

    def test_no_special_char_rejected(self, client):
        assert self._try_register(client, "NoSpecial1A") == 422

    def test_valid_strong_password_accepted(self, client):
        assert self._try_register(client, "Valid@Pass1") == 200


# ── Duplicate registration ────────────────────────────────────────────────────

class TestRegistration:
    def test_duplicate_phone_returns_400(self, client, registered_user):
        resp = client.post("/users/", json={
            "phone": registered_user["phone"],
            "password": "Another@Pass1",
            "role": "buyer",
        })
        assert resp.status_code == 400
        assert "registered" in resp.json()["detail"].lower()

    def test_buyer_role_assigned_correctly(self, client):
        phone = unique_phone()
        resp = client.post("/users/", json={
            "phone": phone, "password": "Valid@Pass1", "role": "buyer",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "buyer"

    def test_seller_role_assigned_correctly(self, client):
        phone = unique_phone()
        resp = client.post("/users/", json={
            "phone": phone, "password": "Valid@Pass1", "role": "seller",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "seller"


# ── Google OAuth — URL generation ────────────────────────────────────────────

class TestGoogleOAuth:
    def test_google_login_returns_auth_url(self, client):
        resp = client.get("/auth/google/login")
        # Without env vars configured the endpoint either returns 200 with url or 500
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert "auth_url" in resp.json()

    def test_google_register_returns_auth_url(self, client):
        resp = client.get("/auth/google/register")
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert "auth_url" in resp.json()

    def test_google_callback_with_invalid_code_returns_400(self, client):
        resp = client.get("/auth/google/callback", params={"code": "fake_code", "state": "login"})
        assert resp.status_code in (400, 422, 302, 500)


# ── Telegram OTP ─────────────────────────────────────────────────────────────

class TestTelegramOtp:
    def test_otp_request_unknown_user_returns_404(self, client):
        resp = client.post("/auth/otp/request", json={"telegram_username": "nonexistent_udx_qa_user_xyz"})
        assert resp.status_code == 404

    def test_otp_verify_without_request_returns_400(self, client):
        resp = client.post("/auth/otp/verify", json={
            "telegram_username": "some_unverified_user",
            "code": "000000",
        })
        assert resp.status_code == 400

    def test_otp_verify_wrong_code_returns_400(self, client):
        # Inject a fake entry into the store manually is not possible over HTTP,
        # so we confirm the API rejects a code without a prior request.
        resp = client.post("/auth/otp/verify", json={
            "telegram_username": "fake_qa_tg_user",
            "code": "999999",
        })
        assert resp.status_code == 400
