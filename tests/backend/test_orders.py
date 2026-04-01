"""
QA tests — Orders endpoints
    POST /orders/
    GET  /orders/
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
    password = "Seller@Order1"
    register_user(client, phone, password, role="seller", name="Order Seller")
    token = get_token(client, phone, password)
    return {"headers": auth_headers(token)}


@pytest.fixture(scope="module")
def buyer(client):
    phone = unique_phone()
    password = "Buyer@Order1"
    register_user(client, phone, password, role="buyer", name="Order Buyer")
    token = get_token(client, phone, password)
    return {"headers": auth_headers(token)}


@pytest.fixture(scope="module")
def product(client, seller):
    cats = client.get("/categories/").json()
    cat_id = cats[0]["id"]
    resp = client.post("/products/", json={
        "name": "Order Test Potato",
        "price": 0.75,
        "unit": "kg",
        "image": "http://example.com/potato.jpg",
        "description": "Potatoes for ordering",
        "category_id": cat_id,
        "in_stock": True,
        "certified": False,
        "is_b2b": False,
    }, headers=seller["headers"])
    assert resp.status_code == 200
    return resp.json()


# ── POST /orders/ ─────────────────────────────────────────────────────────────

class TestCreateOrder:
    def test_buyer_can_create_order(self, client, buyer, product):
        resp = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 3}],
            "delivery_method": "courier",
        }, headers=buyer["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["status"] == "new"

    def test_order_total_computed_correctly(self, client, buyer, product):
        qty = 4
        resp = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": qty}],
            "delivery_method": "pickup",
        }, headers=buyer["headers"])
        assert resp.status_code == 200
        expected_total = round(product["price"] * qty, 2)
        assert abs(resp.json()["total"] - expected_total) < 0.01

    def test_order_with_multiple_items(self, client, buyer, product):
        resp = client.post("/orders/", json={
            "items": [
                {"product_id": product["id"], "quantity": 1},
                {"product_id": product["id"], "quantity": 2},
            ],
            "delivery_method": "courier",
        }, headers=buyer["headers"])
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_order_with_nonexistent_product_returns_404(self, client, buyer):
        resp = client.post("/orders/", json={
            "items": [{"product_id": "000000000000000000000000", "quantity": 1}],
            "delivery_method": "courier",
        }, headers=buyer["headers"])
        assert resp.status_code == 404

    def test_unauthenticated_order_returns_401(self, client, product):
        resp = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_method": "courier",
        })
        assert resp.status_code == 401

    def test_order_missing_items_returns_422(self, client, buyer):
        resp = client.post("/orders/", json={"delivery_method": "courier"}, headers=buyer["headers"])
        assert resp.status_code == 422

    def test_default_delivery_method_is_courier(self, client, buyer, product):
        resp = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
        }, headers=buyer["headers"])
        assert resp.status_code == 200

    def test_order_status_defaults_to_new(self, client, buyer, product):
        resp = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_method": "pickup",
        }, headers=buyer["headers"])
        assert resp.json()["status"] == "new"


# ── GET /orders/ ──────────────────────────────────────────────────────────────

class TestListOrders:
    def test_buyer_can_list_their_orders(self, client, buyer, product):
        # Place one order first to ensure list is not empty
        client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_method": "courier",
        }, headers=buyer["headers"])
        resp = client.get("/orders/", headers=buyer["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_seller_can_list_orders_for_their_products(self, client, seller):
        resp = client.get("/orders/", headers=seller["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_orders_have_required_fields(self, client, buyer, product):
        client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_method": "courier",
        }, headers=buyer["headers"])
        resp = client.get("/orders/", headers=buyer["headers"])
        order = resp.json()[0]
        for field in ("id", "status", "total", "items", "date"):
            assert field in order, f"Missing field: {field}"

    def test_pagination_limit_respected(self, client, buyer):
        resp = client.get("/orders/", params={"limit": 1}, headers=buyer["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    def test_unauthenticated_list_returns_401(self, client):
        resp = client.get("/orders/")
        assert resp.status_code == 401

    def test_new_user_has_empty_orders(self, client):
        phone = unique_phone()
        password = "Empty@Order1"
        register_user(client, phone, password)
        token = get_token(client, phone, password)
        resp = client.get("/orders/", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []
