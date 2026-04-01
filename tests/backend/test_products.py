"""
QA tests — Products & Categories endpoints
    GET  /products/
    POST /products/
    GET  /products/{id}
    GET  /products/{id}/prices/
    POST /products/{id}/prices/
    POST /products/interactions/
    GET  /products/recommendations/
    GET  /categories/
    POST /upload/image/
"""

import io
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
    password = "Seller@Prod1"
    register_user(client, phone, password, role="seller", name="Product Seller")
    token = get_token(client, phone, password)
    return {"headers": auth_headers(token)}


@pytest.fixture(scope="module")
def buyer(client):
    phone = unique_phone()
    password = "Buyer@Prod1"
    register_user(client, phone, password, role="buyer", name="Product Buyer")
    token = get_token(client, phone, password)
    return {"headers": auth_headers(token)}


@pytest.fixture(scope="module")
def category_id(client):
    resp = client.get("/categories/")
    assert resp.status_code == 200
    cats = resp.json()
    return cats[0]["id"]


@pytest.fixture(scope="module")
def product(client, seller, category_id):
    resp = client.post("/products/", json={
        "name": "QA Apples",
        "price": 1.99,
        "unit": "kg",
        "image": "http://example.com/apple.jpg",
        "description": "Fresh apples",
        "category_id": category_id,
        "in_stock": True,
        "certified": True,
        "is_b2b": False,
    }, headers=seller["headers"])
    assert resp.status_code == 200
    return resp.json()


# ── GET /categories/ ─────────────────────────────────────────────────────────

class TestCategories:
    def test_returns_list(self, client):
        resp = client.get("/categories/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_categories_have_required_fields(self, client):
        resp = client.get("/categories/")
        for cat in resp.json():
            assert "id" in cat
            assert "name" in cat
            assert "icon" in cat

    def test_returns_at_least_one_category(self, client):
        resp = client.get("/categories/")
        assert len(resp.json()) >= 1


# ── GET /products/ ────────────────────────────────────────────────────────────

class TestListProducts:
    def test_returns_list(self, client):
        resp = client.get("/products/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_pagination_skip_and_limit(self, client, product):
        full = client.get("/products/", params={"limit": 100}).json()
        sliced = client.get("/products/", params={"skip": 1, "limit": 1}).json()
        assert len(sliced) <= 1

    def test_filter_by_is_b2b_false(self, client, product):
        resp = client.get("/products/", params={"is_b2b": False})
        assert resp.status_code == 200
        for p in resp.json():
            assert p["is_b2b"] is False

    def test_filter_by_category_id(self, client, product, category_id):
        resp = client.get("/products/", params={"category_id": category_id})
        assert resp.status_code == 200
        for p in resp.json():
            assert p["category_id"] == category_id

    def test_product_has_required_fields(self, client, product):
        resp = client.get("/products/")
        if resp.json():
            p = resp.json()[0]
            for field in ("id", "name", "price", "unit", "seller_id", "in_stock"):
                assert field in p


# ── POST /products/ ───────────────────────────────────────────────────────────

class TestCreateProduct:
    def test_seller_can_create_product(self, client, seller, category_id):
        resp = client.post("/products/", json={
            "name": "Create Test Carrots",
            "price": 0.99,
            "unit": "kg",
            "image": "http://example.com/carrot.jpg",
            "description": "Orange carrots",
            "category_id": category_id,
            "in_stock": True,
            "certified": False,
            "is_b2b": False,
        }, headers=seller["headers"])
        assert resp.status_code == 200
        assert resp.json()["name"] == "Create Test Carrots"

    def test_buyer_cannot_create_product(self, client, buyer, category_id):
        resp = client.post("/products/", json={
            "name": "Buyer Should Fail",
            "price": 5.0,
            "unit": "kg",
            "image": "http://example.com/x.jpg",
            "description": "desc",
            "category_id": category_id,
            "in_stock": True,
            "certified": False,
            "is_b2b": False,
        }, headers=buyer["headers"])
        assert resp.status_code == 403

    def test_unauthenticated_create_returns_401(self, client, category_id):
        resp = client.post("/products/", json={
            "name": "Ghost Product",
            "price": 1.0,
            "unit": "kg",
            "image": "http://example.com/g.jpg",
            "description": "no auth",
            "category_id": category_id,
            "in_stock": True,
            "certified": False,
            "is_b2b": False,
        })
        assert resp.status_code == 401

    def test_missing_required_fields_returns_422(self, client, seller):
        resp = client.post("/products/", json={"name": "Incomplete"}, headers=seller["headers"])
        assert resp.status_code == 422


# ── GET /products/{id} ───────────────────────────────────────────────────────

class TestGetProduct:
    def test_existing_product_returned(self, client, product):
        resp = client.get(f"/products/{product['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == product["id"]

    def test_nonexistent_id_returns_404(self, client):
        resp = client.get("/products/000000000000000000000000")
        assert resp.status_code == 404

    def test_returned_product_fields(self, client, product):
        resp = client.get(f"/products/{product['id']}")
        body = resp.json()
        for field in ("id", "name", "price", "unit", "seller_id", "rating", "views"):
            assert field in body


# ── Price history ─────────────────────────────────────────────────────────────

class TestPriceHistory:
    def test_add_price_entry(self, client, product):
        resp = client.post(f"/products/{product['id']}/prices/", json={"price": 3.50})
        assert resp.status_code == 200
        body = resp.json()
        assert body["price"] == 3.50
        assert body["product_id"] == product["id"]

    def test_price_history_is_list(self, client, product):
        resp = client.get(f"/products/{product['id']}/prices/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_price_history_entry_has_date(self, client, product):
        client.post(f"/products/{product['id']}/prices/", json={"price": 4.00})
        resp = client.get(f"/products/{product['id']}/prices/")
        for entry in resp.json():
            assert "date" in entry

    def test_price_history_nonexistent_product_returns_404(self, client):
        resp = client.get("/products/000000000000000000000000/prices/")
        assert resp.status_code == 404


# ── Product interactions ──────────────────────────────────────────────────────

class TestProductInteractions:
    def test_buyer_can_record_view(self, client, buyer, product):
        resp = client.post("/products/interactions/", json={
            "product_id": product["id"],
            "interaction_type": "view",
        }, headers=buyer["headers"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_buyer_can_record_click(self, client, buyer, product):
        resp = client.post("/products/interactions/", json={
            "product_id": product["id"],
            "interaction_type": "click",
        }, headers=buyer["headers"])
        assert resp.status_code == 200

    def test_invalid_interaction_type_returns_422(self, client, buyer, product):
        resp = client.post("/products/interactions/", json={
            "product_id": product["id"],
            "interaction_type": "invalid_type",
        }, headers=buyer["headers"])
        assert resp.status_code == 422

    def test_unauthenticated_interaction_returns_401(self, client, product):
        resp = client.post("/products/interactions/", json={
            "product_id": product["id"],
            "interaction_type": "view",
        })
        assert resp.status_code == 401


# ── Recommendations ──────────────────────────────────────────────────────────

class TestRecommendations:
    def test_authenticated_user_gets_recommendations(self, client, buyer):
        resp = client.get("/products/recommendations/", headers=buyer["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_recommendations_respect_limit(self, client, buyer):
        resp = client.get("/products/recommendations/", params={"limit": 2}, headers=buyer["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    def test_unauthenticated_recommendations_returns_401(self, client):
        resp = client.get("/products/recommendations/")
        assert resp.status_code == 401


# ── Image upload ──────────────────────────────────────────────────────────────

class TestImageUpload:
    def test_upload_valid_image_returns_url(self, client):
        fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        resp = client.post(
            "/upload/image/",
            files={"file": ("test.png", fake_image, "image/png")},
        )
        assert resp.status_code == 200
        assert "url" in resp.json()

    def test_upload_non_image_returns_400(self, client):
        fake_txt = io.BytesIO(b"this is not an image")
        resp = client.post(
            "/upload/image/",
            files={"file": ("test.txt", fake_txt, "text/plain")},
        )
        assert resp.status_code == 400
