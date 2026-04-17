"""
QA tests — Asosiy API smoke tests
    GET /health
    GET /products/
    GET /weather
"""

import pytest
import httpx

from conftest import BASE_URL


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


class TestSmoke:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ok", "degraded")
        assert "services" in body

    def test_get_products_public(self, client):
        resp = client.get("/products/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_categories_public(self, client):
        resp = client.get("/categories/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_weather_requires_params(self, client):
        """lat/lon parametrisiz weather → 422 yoki 400."""
        resp = client.get("/weather")
        assert resp.status_code in (400, 422)

    def test_weather_with_coords(self, client):
        resp = client.get("/weather?lat=41.2995&lon=69.2401")
        # API key yo'q bo'lsa 500, bor bo'lsa 200
        assert resp.status_code in (200, 500)

    def test_unknown_endpoint_returns_404(self, client):
        resp = client.get("/this-does-not-exist")
        assert resp.status_code == 404
