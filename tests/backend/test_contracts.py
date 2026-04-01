"""
QA tests — Contracts endpoints
    GET  /contracts/
    POST /contracts/
    PUT  /contracts/{id}/status
"""

import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Module-scoped fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def seller(client):
    phone = unique_phone()
    password = "Seller@Contract1"
    data = register_user(client, phone, password, role="seller", name="Contract Seller")
    token = get_token(client, phone, password)
    return {**data, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def buyer(client):
    phone = unique_phone()
    password = "Buyer@Contract1"
    data = register_user(client, phone, password, role="buyer", name="Contract Buyer")
    token = get_token(client, phone, password)
    return {**data, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def outsider(client):
    """A user who is neither buyer nor seller of any contract."""
    phone = unique_phone()
    password = "Outsider@Contract1"
    data = register_user(client, phone, password, name="Outsider")
    token = get_token(client, phone, password)
    return {**data, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def contract(client, seller, buyer):
    resp = client.post("/contracts/", json={
        "buyer_id": buyer["id"],
        "title": "QA Supply Agreement",
        "description": "Automated test contract",
        "amount": 500.0,
    }, headers=seller["headers"])
    assert resp.status_code == 200, f"Contract creation failed: {resp.text}"
    return resp.json()


# ── POST /contracts/ ──────────────────────────────────────────────────────────

class TestCreateContract:
    def test_seller_can_create_contract(self, client, contract):
        assert contract["id"] is not None
        assert contract["status"] == "pending"

    def test_contract_has_correct_parties(self, client, contract, seller, buyer):
        assert contract["seller_id"] == seller["id"]
        assert contract["buyer_id"] == buyer["id"]

    def test_contract_stores_title_and_amount(self, client, contract):
        assert contract["title"] == "QA Supply Agreement"
        assert contract["amount"] == 500.0

    def test_contract_includes_party_names(self, client, contract):
        assert contract["buyer_name"] == "Contract Buyer"
        assert contract["seller_name"] == "Contract Seller"

    def test_nonexistent_buyer_returns_404(self, client, seller):
        resp = client.post("/contracts/", json={
            "buyer_id": "000000000000000000000000",
            "title": "Bad Contract",
            "amount": 100.0,
        }, headers=seller["headers"])
        assert resp.status_code == 404

    def test_missing_required_fields_returns_422(self, client, seller):
        resp = client.post("/contracts/", json={"title": "Incomplete"}, headers=seller["headers"])
        assert resp.status_code == 422

    def test_unauthenticated_create_returns_401(self, client, buyer):
        resp = client.post("/contracts/", json={
            "buyer_id": buyer["id"],
            "title": "Ghost Contract",
            "amount": 50.0,
        })
        assert resp.status_code == 401


# ── GET /contracts/ ───────────────────────────────────────────────────────────

class TestListContracts:
    def test_seller_can_list_contracts(self, client, seller, contract):
        resp = client.get("/contracts/", headers=seller["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_buyer_can_list_contracts(self, client, buyer, contract):
        resp = client.get("/contracts/", headers=buyer["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_contract_appears_for_both_parties(self, client, seller, buyer, contract):
        seller_contracts = [c["id"] for c in client.get("/contracts/", headers=seller["headers"]).json()]
        buyer_contracts = [c["id"] for c in client.get("/contracts/", headers=buyer["headers"]).json()]
        assert contract["id"] in seller_contracts
        assert contract["id"] in buyer_contracts

    def test_outsider_does_not_see_the_contract(self, client, outsider, contract):
        resp = client.get("/contracts/", headers=outsider["headers"])
        ids = [c["id"] for c in resp.json()]
        assert contract["id"] not in ids

    def test_contract_list_item_has_required_fields(self, client, seller):
        resp = client.get("/contracts/", headers=seller["headers"])
        if resp.json():
            item = resp.json()[0]
            for field in ("id", "buyer_id", "seller_id", "title", "amount", "status", "created_at"):
                assert field in item

    def test_unauthenticated_list_returns_401(self, client):
        resp = client.get("/contracts/")
        assert resp.status_code == 401


# ── PUT /contracts/{id}/status ────────────────────────────────────────────────

class TestUpdateContractStatus:
    def test_buyer_can_update_status(self, client, buyer, contract):
        resp = client.put(f"/contracts/{contract['id']}/status",
                          params={"status": "active"},
                          headers=buyer["headers"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_seller_can_update_status(self, client, seller, contract):
        resp = client.put(f"/contracts/{contract['id']}/status",
                          params={"status": "completed"},
                          headers=seller["headers"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_cancel_contract(self, client, seller, contract):
        resp = client.put(f"/contracts/{contract['id']}/status",
                          params={"status": "cancelled"},
                          headers=seller["headers"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_outsider_cannot_update_status(self, client, outsider, contract):
        resp = client.put(f"/contracts/{contract['id']}/status",
                          params={"status": "active"},
                          headers=outsider["headers"])
        assert resp.status_code == 403

    def test_invalid_status_returns_422(self, client, seller, contract):
        resp = client.put(f"/contracts/{contract['id']}/status",
                          params={"status": "invalid_status"},
                          headers=seller["headers"])
        assert resp.status_code == 422

    def test_nonexistent_contract_returns_404(self, client, seller):
        resp = client.put("/contracts/000000000000000000000000/status",
                          params={"status": "active"},
                          headers=seller["headers"])
        assert resp.status_code == 404

    def test_unauthenticated_update_returns_401(self, client, contract):
        resp = client.put(f"/contracts/{contract['id']}/status",
                          params={"status": "active"})
        assert resp.status_code == 401
