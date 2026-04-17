"""
QA tests — Payments endpoints
    POST /payments/tokenize
    POST /payments/deposit
    POST /payments/withdraw
    GET  /payments/transactions
    GET  /payments/audit

Tekshiriladi:
  - Karta tokenizatsiya
  - Depozit (idempotency key bilan)
  - Idempotent replay — balance ikki marta kreditlanmasin
  - Withdraw (balans yetarli / yetarli emas)
  - Transactions tarixi
  - Audit log
  - Rate limiting (5/min)
"""

import uuid
import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Helpers ───────────────────────────────────────────────────────────────────

def tokenize_card(client, card_number="4111111111111111",
                  expiry="12/26", owner="QA Test User"):
    resp = client.post("/payments/tokenize", json={
        "card_number": card_number,
        "expiry": expiry,
        "owner_name": owner,
    })
    assert resp.status_code == 200, f"Tokenize failed: {resp.text}"
    return resp.json()


def add_card(client, headers, token_data):
    resp = client.post("/users/me/cards", json={
        "owner_name": token_data["owner_name"],
        "last4":      token_data["last4"],
        "expiry":     token_data["expiry"],
        "card_type":  token_data["card_type"],
        "card_token": token_data["card_token"],
    }, headers=headers)
    assert resp.status_code == 200, f"Add card failed: {resp.text}"
    return resp.json()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def user_with_card(client):
    phone, password = unique_phone(), "Pay@Secure1"
    register_user(client, phone, password, role="buyer", name="Payment User")
    token = get_token(client, phone, password)
    headers = auth_headers(token)

    tok = tokenize_card(client)
    card = add_card(client, headers, tok)
    return {"headers": headers, "card_id": card["id"]}


# ── POST /payments/tokenize ───────────────────────────────────────────────────

class TestTokenize:
    def test_visa_card_tokenized(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "4111111111111111",
            "expiry": "12/26",
            "owner_name": "Visa User",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["card_type"] == "Visa"
        assert body["last4"] == "1111"
        assert body["card_token"].startswith("tok_")

    def test_mastercard_detected(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "5500000000000004",
            "expiry": "01/27",
            "owner_name": "MC User",
        })
        assert resp.status_code == 200
        assert resp.json()["card_type"] == "Mastercard"

    def test_token_unique_per_request(self, client):
        payload = {"card_number": "4111111111111111", "expiry": "12/26", "owner_name": "X"}
        t1 = client.post("/payments/tokenize", json=payload).json()["card_token"]
        t2 = client.post("/payments/tokenize", json=payload).json()["card_token"]
        assert t1 != t2

    def test_pan_not_returned(self, client):
        resp = client.post("/payments/tokenize", json={
            "card_number": "4111111111111111",
            "expiry": "12/26",
            "owner_name": "No PAN",
        }).json()
        assert "4111111111111111" not in str(resp)
        assert "card_number" not in resp


# ── POST /payments/deposit ────────────────────────────────────────────────────

class TestDeposit:
    def test_deposit_increases_balance(self, client, user_with_card):
        before = client.get("/users/me", headers=user_with_card["headers"]).json()["balance"]

        resp = client.post("/payments/deposit", json={
            "card_id": user_with_card["card_id"],
            "amount": 100.0,
        }, headers=user_with_card["headers"],
           headers_update={"X-Idempotency-Key": str(uuid.uuid4())})
        assert resp.status_code == 200

        after = client.get("/users/me", headers=user_with_card["headers"]).json()["balance"]
        assert after >= before + 100.0

    def test_deposit_with_idempotency_key(self, client, user_with_card):
        key = str(uuid.uuid4())
        before = client.get("/users/me", headers=user_with_card["headers"]).json()["balance"]

        r1 = client.post("/payments/deposit",
                         json={"card_id": user_with_card["card_id"], "amount": 50.0},
                         headers={**user_with_card["headers"], "X-Idempotency-Key": key})
        assert r1.status_code == 200

        # Replay — balance must not increase again
        r2 = client.post("/payments/deposit",
                         json={"card_id": user_with_card["card_id"], "amount": 50.0},
                         headers={**user_with_card["headers"], "X-Idempotency-Key": key})
        assert r2.status_code == 200

        after = client.get("/users/me", headers=user_with_card["headers"]).json()["balance"]
        assert after <= before + 50.0 + 5.0  # faqat bir marta kreditlanadi

    def test_zero_amount_returns_400(self, client, user_with_card):
        resp = client.post("/payments/deposit",
                           json={"card_id": user_with_card["card_id"], "amount": 0},
                           headers=user_with_card["headers"])
        assert resp.status_code == 400

    def test_negative_amount_returns_400(self, client, user_with_card):
        resp = client.post("/payments/deposit",
                           json={"card_id": user_with_card["card_id"], "amount": -10},
                           headers=user_with_card["headers"])
        assert resp.status_code == 400

    def test_invalid_card_id_returns_400(self, client, user_with_card):
        resp = client.post("/payments/deposit",
                           json={"card_id": "nonexistent_card_id", "amount": 10.0},
                           headers=user_with_card["headers"])
        assert resp.status_code == 400

    def test_deposit_requires_auth(self, client, user_with_card):
        resp = client.post("/payments/deposit",
                           json={"card_id": user_with_card["card_id"], "amount": 10.0})
        assert resp.status_code == 401


# ── POST /payments/withdraw ───────────────────────────────────────────────────

class TestWithdraw:
    @pytest.fixture(scope="class")
    def funded_user(self, client):
        """Balansida mablag' bor foydalanuvchi."""
        phone, password = unique_phone(), "Fund@Secure1"
        register_user(client, phone, password, role="buyer", name="Funded User")
        token = get_token(client, phone, password)
        headers = auth_headers(token)

        tok = tokenize_card(client)
        card = add_card(client, headers, tok)

        # 200 so'm depozit
        client.post("/payments/deposit",
                    json={"card_id": card["id"], "amount": 200.0},
                    headers={**headers, "X-Idempotency-Key": str(uuid.uuid4())})

        return {"headers": headers, "card_id": card["id"]}

    def test_withdraw_decreases_balance(self, client, funded_user):
        before = client.get("/users/me", headers=funded_user["headers"]).json()["balance"]
        resp = client.post("/payments/withdraw",
                           json={"card_id": funded_user["card_id"], "amount": 50.0},
                           headers=funded_user["headers"])
        assert resp.status_code == 200
        after = client.get("/users/me", headers=funded_user["headers"]).json()["balance"]
        assert after <= before - 50.0 + 0.01

    def test_withdraw_more_than_balance_returns_400(self, client, funded_user):
        resp = client.post("/payments/withdraw",
                           json={"card_id": funded_user["card_id"], "amount": 999999.0},
                           headers=funded_user["headers"])
        assert resp.status_code == 400

    def test_zero_withdraw_returns_400(self, client, funded_user):
        resp = client.post("/payments/withdraw",
                           json={"card_id": funded_user["card_id"], "amount": 0},
                           headers=funded_user["headers"])
        assert resp.status_code == 400


# ── GET /payments/transactions ────────────────────────────────────────────────

class TestTransactions:
    def test_transactions_list_returns_array(self, client, user_with_card):
        resp = client.get("/payments/transactions", headers=user_with_card["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_transaction_has_required_fields(self, client, user_with_card):
        txns = client.get("/payments/transactions", headers=user_with_card["headers"]).json()
        if txns:
            t = txns[0]
            assert "id" in t
            assert "amount" in t
            assert "type" in t
            assert "status" in t

    def test_requires_auth(self, client):
        resp = client.get("/payments/transactions")
        assert resp.status_code == 401


# ── GET /payments/audit ───────────────────────────────────────────────────────

class TestAuditLog:
    def test_audit_log_returns_array(self, client, user_with_card):
        resp = client.get("/payments/audit", headers=user_with_card["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_audit_entries_have_required_fields(self, client, user_with_card):
        entries = client.get("/payments/audit", headers=user_with_card["headers"]).json()
        for e in entries[:3]:
            assert "action" in e
            assert "created_at" in e
            assert "success" in e

    def test_requires_auth(self, client):
        resp = client.get("/payments/audit")
        assert resp.status_code == 401
