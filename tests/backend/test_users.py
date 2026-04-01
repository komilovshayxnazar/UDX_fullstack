"""
QA tests — User management endpoints
    GET  /users/me
    PUT  /users/me
    PUT  /users/me/password
    PUT  /users/me/phone
    PUT  /users/me/role
    PUT  /users/me/2fa
    GET  /users/me/cards
    POST /users/me/cards
    DELETE /users/me/cards/{card_id}
    POST /users/me/balance/deposit
    POST /users/me/balance/withdraw
"""

import uuid
import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Module-scoped user fixture ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def user(client):
    phone = unique_phone()
    password = "User@Secure1"
    data = register_user(client, phone, password, name="Profile User")
    token = get_token(client, phone, password)
    return {**data, "phone": phone, "password": password,
            "token": token, "headers": auth_headers(token)}


# ── GET /users/me ─────────────────────────────────────────────────────────────

class TestGetProfile:
    def test_authenticated_user_can_fetch_profile(self, client, user):
        resp = client.get("/users/me", headers=user["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["phone"] == user["phone"]
        assert "id" in body
        assert "balance" in body

    def test_unauthenticated_request_returns_401(self, client):
        resp = client.get("/users/me")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/users/me", headers={"Authorization": "Bearer totally_invalid"})
        assert resp.status_code == 401


# ── PUT /users/me ─────────────────────────────────────────────────────────────

class TestUpdateProfile:
    def test_update_name_succeeds(self, client, user):
        resp = client.put("/users/me", json={"name": "Updated QA Name"}, headers=user["headers"])
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated QA Name"

    def test_update_description_succeeds(self, client, user):
        resp = client.put("/users/me", json={"description": "QA test description"}, headers=user["headers"])
        assert resp.status_code == 200

    def test_update_avatar_succeeds(self, client, user):
        resp = client.put("/users/me", json={"avatar": "http://example.com/avatar.jpg"}, headers=user["headers"])
        assert resp.status_code == 200
        assert resp.json()["avatar"] == "http://example.com/avatar.jpg"

    def test_partial_update_leaves_other_fields_intact(self, client, user):
        # Set a known name first
        client.put("/users/me", json={"name": "Known Name"}, headers=user["headers"])
        # Update only avatar
        resp = client.put("/users/me", json={"avatar": "http://example.com/new.jpg"}, headers=user["headers"])
        assert resp.status_code == 200
        assert resp.json()["name"] == "Known Name"

    def test_unauthenticated_update_returns_401(self, client):
        resp = client.put("/users/me", json={"name": "Hacker"})
        assert resp.status_code == 401


# ── PUT /users/me/password ────────────────────────────────────────────────────

class TestUpdatePassword:
    def test_wrong_current_password_returns_400(self, client, user):
        resp = client.put("/users/me/password", json={
            "current_password": "WrongPass@1",
            "new_password": "New@Password1",
        }, headers=user["headers"])
        assert resp.status_code == 400

    def test_correct_password_change_succeeds(self, client, user):
        new_pass = "Changed@Pass1"
        resp = client.put("/users/me/password", json={
            "current_password": user["password"],
            "new_password": new_pass,
        }, headers=user["headers"])
        assert resp.status_code == 200
        # Restore original password so other tests remain valid
        client.put("/users/me/password", json={
            "current_password": new_pass,
            "new_password": user["password"],
        }, headers=user["headers"])

    def test_unauthenticated_password_change_returns_401(self, client):
        resp = client.put("/users/me/password", json={
            "current_password": "Any@Pass1",
            "new_password": "New@Pass1",
        })
        assert resp.status_code == 401


# ── PUT /users/me/role ────────────────────────────────────────────────────────

class TestUpdateRole:
    def test_switch_to_seller_succeeds(self, client, user):
        resp = client.put("/users/me/role", json={"role": "seller"}, headers=user["headers"])
        assert resp.status_code == 200
        assert resp.json()["role"] == "seller"

    def test_switch_back_to_buyer_succeeds(self, client, user):
        resp = client.put("/users/me/role", json={"role": "buyer"}, headers=user["headers"])
        assert resp.status_code == 200
        assert resp.json()["role"] == "buyer"

    def test_invalid_role_returns_422(self, client, user):
        resp = client.put("/users/me/role", json={"role": "admin"}, headers=user["headers"])
        assert resp.status_code == 422


# ── PUT /users/me/2fa ─────────────────────────────────────────────────────────

class TestTwoFactor:
    def test_enable_2fa(self, client, user):
        resp = client.put("/users/me/2fa", json={"is_2fa_enabled": True}, headers=user["headers"])
        assert resp.status_code == 200

    def test_disable_2fa(self, client, user):
        resp = client.put("/users/me/2fa", json={"is_2fa_enabled": False}, headers=user["headers"])
        assert resp.status_code == 200

    def test_2fa_toggle_unauthenticated_returns_401(self, client):
        resp = client.put("/users/me/2fa", json={"is_2fa_enabled": True})
        assert resp.status_code == 401


# ── Payment cards ─────────────────────────────────────────────────────────────

class TestPaymentCards:
    @pytest.fixture(scope="class")
    def card_id(self, client, user):
        resp = client.post("/users/me/cards", json={
            "card_token": "tok_test_qa_" + uuid.uuid4().hex[:8],
            "last4": "4242",
            "expiry": "12/28",
            "owner_name": "QA User",
            "card_type": "visa",
        }, headers=user["headers"])
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_list_cards_returns_array(self, client, user):
        resp = client.get("/users/me/cards", headers=user["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_add_card_returns_card_object(self, client, user, card_id):
        assert card_id is not None

    def test_added_card_appears_in_list(self, client, user, card_id):
        resp = client.get("/users/me/cards", headers=user["headers"])
        ids = [c["id"] for c in resp.json()]
        assert card_id in ids

    def test_card_response_has_no_full_pan(self, client, user, card_id):
        resp = client.get("/users/me/cards", headers=user["headers"])
        card = next(c for c in resp.json() if c["id"] == card_id)
        assert "card_token" not in card
        assert len(card["last4"]) == 4

    def test_delete_card_removes_it(self, client, user, card_id):
        resp = client.delete(f"/users/me/cards/{card_id}", headers=user["headers"])
        assert resp.status_code == 200
        remaining = [c["id"] for c in client.get("/users/me/cards", headers=user["headers"]).json()]
        assert card_id not in remaining

    def test_delete_nonexistent_card_is_idempotent(self, client, user):
        resp = client.delete("/users/me/cards/nonexistent_id", headers=user["headers"])
        # Should not crash — returns 200 (filter finds nothing, saves empty list)
        assert resp.status_code == 200


# ── Wallet deposit / withdraw ─────────────────────────────────────────────────

class TestWallet:
    @pytest.fixture(scope="class")
    def funded_user(self, client):
        """A fresh user with a card already saved."""
        phone = unique_phone()
        password = "Wallet@Test1"
        register_user(client, phone, password)
        token = get_token(client, phone, password)
        headers = auth_headers(token)

        card_resp = client.post("/users/me/cards", json={
            "card_token": "tok_mock_wallet_" + uuid.uuid4().hex[:8],
            "last4": "1111",
            "expiry": "06/29",
            "owner_name": "Wallet User",
            "card_type": "mastercard",
        }, headers=headers)
        card_id = card_resp.json()["id"]
        return {"headers": headers, "card_id": card_id}

    def test_deposit_positive_amount_increases_balance(self, client, funded_user):
        me_before = client.get("/users/me", headers=funded_user["headers"]).json()
        resp = client.post("/users/me/balance/deposit", json={
            "amount": 100.0,
            "card_id": funded_user["card_id"],
        }, headers=funded_user["headers"])
        assert resp.status_code == 200
        assert resp.json()["balance"] >= me_before["balance"] + 100.0

    def test_deposit_zero_amount_returns_400(self, client, funded_user):
        resp = client.post("/users/me/balance/deposit", json={
            "amount": 0,
            "card_id": funded_user["card_id"],
        }, headers=funded_user["headers"])
        assert resp.status_code == 400

    def test_deposit_negative_amount_returns_400(self, client, funded_user):
        resp = client.post("/users/me/balance/deposit", json={
            "amount": -50.0,
            "card_id": funded_user["card_id"],
        }, headers=funded_user["headers"])
        assert resp.status_code == 400

    def test_deposit_without_card_returns_400(self, client, funded_user):
        resp = client.post("/users/me/balance/deposit", json={
            "amount": 50.0,
            "card_id": "nonexistent_card_id",
        }, headers=funded_user["headers"])
        assert resp.status_code == 400

    def test_withdraw_more_than_balance_returns_400(self, client, funded_user):
        me = client.get("/users/me", headers=funded_user["headers"]).json()
        too_much = me["balance"] + 99999.0
        resp = client.post("/users/me/balance/withdraw", json={
            "amount": too_much,
            "card_id": funded_user["card_id"],
        }, headers=funded_user["headers"])
        assert resp.status_code == 400
        assert "insufficient" in resp.json()["detail"].lower()

    def test_unauthenticated_deposit_returns_401(self, client, funded_user):
        resp = client.post("/users/me/balance/deposit", json={
            "amount": 10.0,
            "card_id": funded_user["card_id"],
        })
        assert resp.status_code == 401
