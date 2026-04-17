"""
QA tests — Reviews & Fraud Reports
    POST /reviews/
    GET  /reviews/seller/{seller_id}
    POST /fraud-reports/

Anti-fraud qoidalari:
  - Faqat buyer sharh qoldira oladi
  - Faqat COMPLETED order uchun sharh
  - Bir order — bir sharh (duplicate taqiqlangan)
  - O'ziga sharh qoldirish taqiqlangan
  - Fraud report spam limiti: bitta target uchun max 3 ta
"""

import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def seller(client):
    phone, password = unique_phone(), "Seller@Rev1"
    register_user(client, phone, password, role="seller", name="Review Seller")
    token = get_token(client, phone, password)
    me = client.get("/users/me", headers=auth_headers(token)).json()
    return {"id": me["id"], "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def buyer(client):
    phone, password = unique_phone(), "Buyer@Rev1"
    register_user(client, phone, password, role="buyer", name="Review Buyer")
    token = get_token(client, phone, password)
    me = client.get("/users/me", headers=auth_headers(token)).json()
    return {"id": me["id"], "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def another_buyer(client):
    phone, password = unique_phone(), "Buyer@Rev2"
    register_user(client, phone, password, role="buyer", name="Another Buyer")
    token = get_token(client, phone, password)
    me = client.get("/users/me", headers=auth_headers(token)).json()
    return {"id": me["id"], "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def product(client, seller):
    cats = client.get("/categories/").json()
    cat_id = cats[0]["id"]
    resp = client.post("/products/", json={
        "name": "Review Test Apple",
        "price": 1.20,
        "unit": "kg",
        "image": "http://example.com/apple.jpg",
        "description": "Apples for review testing",
        "category_id": cat_id,
        "in_stock": True,
        "certified": False,
        "is_b2b": False,
    }, headers=seller["headers"])
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture(scope="module")
def completed_order(client, buyer, product, seller):
    """Buyurtma yaratib, statusini completed ga o'zgartiradi."""
    resp = client.post("/orders/", json={
        "items": [{"product_id": product["id"], "quantity": 2}],
        "delivery_method": "courier",
    }, headers=buyer["headers"])
    assert resp.status_code == 200, f"Order creation failed: {resp.text}"
    order = resp.json()

    # Dev endpoint orqali completed ga o'tkazish
    complete = client.post(f"/dev/orders/{order['id']}/complete")
    assert complete.status_code == 200, f"Could not complete order: {complete.text}"

    return {
        "id": order["id"],
        "seller_id": seller["id"],
        "product_id": product["id"],
    }


# ── POST /reviews/ ────────────────────────────────────────────────────────────

class TestCreateReview:
    def test_buyer_can_review_completed_order(self, client, buyer, completed_order):
        resp = client.post("/reviews/", json={
            "order_id": completed_order["id"],
            "seller_id": completed_order["seller_id"],
            "product_id": completed_order["product_id"],
            "rating": 5,
            "comment": "Excellent quality!",
        }, headers=buyer["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["rating"] == 5
        assert body["is_verified_purchase"] is True
        assert body["seller_id"] == completed_order["seller_id"]

    def test_duplicate_review_returns_409(self, client, buyer, completed_order):
        resp = client.post("/reviews/", json={
            "order_id": completed_order["id"],
            "seller_id": completed_order["seller_id"],
            "product_id": completed_order["product_id"],
            "rating": 4,
            "comment": "Second review attempt",
        }, headers=buyer["headers"])
        assert resp.status_code == 409

    def test_seller_cannot_leave_review(self, client, seller, completed_order):
        resp = client.post("/reviews/", json={
            "order_id": completed_order["id"],
            "seller_id": completed_order["seller_id"],
            "product_id": completed_order["product_id"],
            "rating": 3,
            "comment": "Seller reviewing",
        }, headers=seller["headers"])
        assert resp.status_code == 403

    def test_review_requires_auth(self, client, completed_order):
        resp = client.post("/reviews/", json={
            "order_id": completed_order["id"],
            "seller_id": completed_order["seller_id"],
            "product_id": completed_order["product_id"],
            "rating": 3,
        })
        assert resp.status_code == 401

    def test_non_owner_buyer_cannot_review_order(self, client, another_buyer, completed_order):
        resp = client.post("/reviews/", json={
            "order_id": completed_order["id"],
            "seller_id": completed_order["seller_id"],
            "product_id": completed_order["product_id"],
            "rating": 2,
            "comment": "Not my order",
        }, headers=another_buyer["headers"])
        assert resp.status_code == 403

    def test_review_on_new_order_returns_400(self, client, buyer, product, seller):
        """Tugallanmagan (new) order uchun sharh → 400."""
        new_order = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_method": "pickup",
        }, headers=buyer["headers"]).json()

        resp = client.post("/reviews/", json={
            "order_id": new_order["id"],
            "seller_id": seller["id"],
            "product_id": product["id"],
            "rating": 5,
        }, headers=buyer["headers"])
        assert resp.status_code == 400

    def test_rating_updates_seller_rating(self, client, seller):
        """Sharh qo'shilganda sotuvchi reytingi yangilanishi kerak."""
        profile = client.get(f"/users/{seller['id']}/public").json()
        assert profile["rating"] > 0
        assert profile["review_count"] >= 1

    def test_invalid_rating_value(self, client, buyer, completed_order):
        """Rating 1-5 orasida bo'lishi kerak."""
        resp = client.post("/reviews/", json={
            "order_id": completed_order["id"],
            "seller_id": completed_order["seller_id"],
            "product_id": completed_order["product_id"],
            "rating": 10,
        }, headers=buyer["headers"])
        assert resp.status_code in (400, 409, 422)


# ── GET /reviews/seller/{id} ──────────────────────────────────────────────────

class TestGetSellerReviews:
    def test_returns_reviews_list(self, client, seller, completed_order):
        resp = client.get(f"/reviews/seller/{seller['id']}")
        assert resp.status_code == 200
        reviews = resp.json()
        assert isinstance(reviews, list)
        assert len(reviews) >= 1

    def test_reviews_have_required_fields(self, client, seller):
        reviews = client.get(f"/reviews/seller/{seller['id']}").json()
        for r in reviews:
            assert "id" in r
            assert "rating" in r
            assert "reviewer_id" in r
            assert "is_verified_purchase" in r

    def test_pagination_works(self, client, seller):
        resp = client.get(f"/reviews/seller/{seller['id']}?skip=0&limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    def test_nonexistent_seller_returns_empty(self, client):
        resp = client.get("/reviews/seller/000000000000000000000000")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_no_auth_required_for_public_reviews(self, client, seller):
        resp = client.get(f"/reviews/seller/{seller['id']}")
        assert resp.status_code == 200


# ── POST /fraud-reports/ ──────────────────────────────────────────────────────

class TestFraudReports:
    def test_report_user_succeeds(self, client, buyer, seller):
        resp = client.post("/fraud-reports/", json={
            "target_user_id": seller["id"],
            "reason": "Suspicious activity",
        }, headers=buyer["headers"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "reported"

    def test_report_product_succeeds(self, client, buyer, product):
        resp = client.post("/fraud-reports/", json={
            "target_product_id": product["id"],
            "reason": "Fake product",
        }, headers=buyer["headers"])
        assert resp.status_code == 200

    def test_report_without_target_returns_400(self, client, buyer):
        resp = client.post("/fraud-reports/", json={
            "reason": "No target specified",
        }, headers=buyer["headers"])
        assert resp.status_code == 400

    def test_spam_limit_enforced(self, client, another_buyer, seller):
        """Bitta target uchun 3 dan ortiq shikoyat → 429."""
        for _ in range(3):
            client.post("/fraud-reports/", json={
                "target_user_id": seller["id"],
                "reason": "Spam test",
            }, headers=another_buyer["headers"])

        resp = client.post("/fraud-reports/", json={
            "target_user_id": seller["id"],
            "reason": "4th report — should be blocked",
        }, headers=another_buyer["headers"])
        assert resp.status_code == 429

    def test_requires_auth(self, client, seller):
        resp = client.post("/fraud-reports/", json={
            "target_user_id": seller["id"],
            "reason": "No auth",
        })
        assert resp.status_code == 401
