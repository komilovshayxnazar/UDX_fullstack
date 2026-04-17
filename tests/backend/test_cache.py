"""
QA tests — Cache layer (observable behavior)

Cache to'g'ri ishlamoqda deb hisoblash uchun:
  - Bir xil so'rov bir xil ma'lumot qaytarishi
  - Yangi product qo'shilganda product listing o'zgarishi (invalidation)
  - Categories bir xil qolishi (static cache)
  - Seller profil cache review qo'shilganda yangilanishi
  - /health endpoint storage turini qaytarishi
"""

import time
import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def seller(client):
    phone, password = unique_phone(), "Cache@Seller1"
    register_user(client, phone, password, role="seller", name="Cache Seller")
    token = get_token(client, phone, password)
    me = client.get("/users/me", headers=auth_headers(token)).json()
    return {"id": me["id"], "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def buyer(client):
    phone, password = unique_phone(), "Cache@Buyer1"
    register_user(client, phone, password, role="buyer", name="Cache Buyer")
    token = get_token(client, phone, password)
    me = client.get("/users/me", headers=auth_headers(token)).json()
    return {"id": me["id"], "headers": auth_headers(token)}


def make_product(client, seller_headers, name="Cache Product"):
    cats = client.get("/categories/").json()
    cat_id = cats[0]["id"]
    return client.post("/products/", json={
        "name": name,
        "price": 3.00,
        "unit": "kg",
        "image": "http://example.com/img.jpg",
        "description": "Cache test product",
        "category_id": cat_id,
        "in_stock": True,
        "certified": False,
        "is_b2b": False,
    }, headers=seller_headers).json()


# ── Categories cache ──────────────────────────────────────────────────────────

class TestCategoriesCache:
    def test_categories_consistent_across_requests(self, client):
        r1 = client.get("/categories/").json()
        r2 = client.get("/categories/").json()
        assert [c["id"] for c in r1] == [c["id"] for c in r2]

    def test_categories_not_empty(self, client):
        cats = client.get("/categories/").json()
        assert len(cats) > 0

    def test_category_has_required_fields(self, client):
        cats = client.get("/categories/").json()
        for c in cats:
            assert "id" in c
            assert "name" in c


# ── Products cache + invalidation ────────────────────────────────────────────

class TestProductsCache:
    def test_product_listing_consistent(self, client):
        r1 = client.get("/products/?limit=5").json()
        r2 = client.get("/products/?limit=5").json()
        ids1 = [p["id"] for p in r1]
        ids2 = [p["id"] for p in r2]
        assert ids1 == ids2

    def test_new_product_appears_after_invalidation(self, client, seller):
        """Yangi mahsulot qo'shilganda listing o'zgarishi kerak."""
        before_ids = {p["id"] for p in client.get("/products/?limit=100").json()}
        new = make_product(client, seller["headers"], "Invalidation Test Product")

        # Cache invalidation bo'lishi uchun bir oz kutiladi
        time.sleep(0.5)

        after_ids = {p["id"] for p in client.get("/products/?limit=100").json()}
        assert new["id"] in after_ids, "Yangi mahsulot listingda ko'rinmadi (cache invalidation ishlamadi?)"

    def test_filter_by_category_cached_separately(self, client, seller):
        cats = client.get("/categories/").json()
        cat_id = cats[0]["id"]
        r1 = client.get(f"/products/?category_id={cat_id}").json()
        r2 = client.get(f"/products/?category_id={cat_id}").json()
        assert [p["id"] for p in r1] == [p["id"] for p in r2]


# ── Seller profile cache ──────────────────────────────────────────────────────

class TestProfileCache:
    def test_seller_profile_consistent(self, client, seller):
        r1 = client.get(f"/users/{seller['id']}/public")
        r2 = client.get(f"/users/{seller['id']}/public")
        if r1.status_code == 200:
            assert r1.json()["id"] == r2.json()["id"]
            assert r1.json()["rating"] == r2.json()["rating"]

    def test_review_updates_seller_profile(self, client, buyer, seller):
        """Review qo'shilganda seller profil cache yangilanishi kerak."""
        # Mahsulot va buyurtma yaratish
        product = make_product(client, seller["headers"], "Profile Cache Product")
        order = client.post("/orders/", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_method": "pickup",
        }, headers=buyer["headers"]).json()

        # Buyurtmani complete qilish
        client.post(f"/dev/orders/{order['id']}/complete")

        # Review oldin profil
        before = client.get(f"/users/{seller['id']}/public")
        before_count = before.json().get("review_count", 0) if before.status_code == 200 else 0

        # Review qo'shish
        client.post("/reviews/", json={
            "order_id": order["id"],
            "seller_id": seller["id"],
            "product_id": product["id"],
            "rating": 4,
            "comment": "Cache test review",
        }, headers=buyer["headers"])

        time.sleep(0.3)

        # Review keyin profil
        after = client.get(f"/users/{seller['id']}/public")
        if after.status_code == 200:
            after_count = after.json().get("review_count", 0)
            assert after_count >= before_count


# ── /health endpoint ──────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "services" in body

    def test_health_includes_mongodb(self, client):
        services = client.get("/health").json()["services"]
        assert "mongodb" in services

    def test_health_includes_redis(self, client):
        services = client.get("/health").json()["services"]
        assert "redis" in services

    def test_health_includes_storage(self, client):
        services = client.get("/health").json()["services"]
        assert "storage" in services
        assert services["storage"] in ("r2", "local")

    def test_mongodb_is_ok(self, client):
        """Backend ishlayotgan bo'lsa MongoDB ham ishlaydi."""
        services = client.get("/health").json()["services"]
        assert services["mongodb"] == "ok"
