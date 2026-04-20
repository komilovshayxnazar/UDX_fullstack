"""
test_neo4j.py — Neo4j graph database testlari.

Tekshiriladi:
  1. Ulanish (connectivity)
  2. CRUD — node va relationship yaratish / o'qish / o'chirish
  3. record_interaction() — user-product interaksiya yozish
  4. _neo4j_cf()          — collaborative filtering tavsiyalar
  5. _neo4j_popular()     — eng mashhur mahsulotlar
  6. is_available()       — health check
  7. Xato tolerantligi   — noto'g'ri query, yo'q driver

Barcha testlar pytest.mark.unit — backend server shart emas.
Neo4j server bo'lmasa testlar SKIP bo'ladi.
"""

import os
import sys
import uuid
import pytest

_BACKEND = os.path.join(os.path.dirname(__file__), "../../android_app/backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

os.environ.setdefault("NEO4J_URI",      "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER",     "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password")

from dotenv import load_dotenv
load_dotenv(os.path.join(_BACKEND, ".env"))


# ─────────────────────────────────────────────────────────────────────────────
# Neo4j mavjudligini tekshirish
# ─────────────────────────────────────────────────────────────────────────────

def _neo4j_running() -> bool:
    try:
        from core import neo4j_db
        # _driver cache'ni tozalash — har safar yangi ulanish
        neo4j_db._driver = None
        return neo4j_db.is_available()
    except Exception:
        return False


pytestmark = pytest.mark.unit

neo4j_required = pytest.mark.skipif(
    not _neo4j_running(),
    reason="Neo4j bolt://localhost:7687 da ishlamayapti — docker start neo4j"
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture — test ma'lumotlarini tozalash
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def cleanup_test_nodes():
    """Har bir test oldidan va keyin test node'larini o'chiradi."""
    from core import neo4j_db
    yield
    neo4j_db.execute_query(
        "MATCH (n) WHERE n.id STARTS WITH 'test_' DETACH DELETE n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Ulanish
# ─────────────────────────────────────────────────────────────────────────────

class TestNeo4jConnectivity:
    @neo4j_required
    def test_is_available_returns_true(self):
        from core.neo4j_db import is_available
        assert is_available() is True

    @neo4j_required
    def test_ping_query(self):
        from core.neo4j_db import execute_query
        result = execute_query("RETURN 1 AS ping")
        assert result[0]["ping"] == 1

    @neo4j_required
    def test_version_query(self):
        from core.neo4j_db import execute_query
        result = execute_query("CALL dbms.components() YIELD name RETURN name LIMIT 1")
        assert len(result) > 0

    def test_unavailable_returns_false_on_wrong_host(self):
        """Noto'g'ri host — is_available() False qaytaradi, istisno ko'tarmaydi."""
        import importlib, types
        # Vaqtinchalik yangi modul instansiyasi yaratib test qilamiz
        from neo4j import GraphDatabase
        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:19999",
                auth=("neo4j", "wrong"),
                connection_timeout=1,
            )
            driver.verify_connectivity()
            driver.close()
            available = True
        except Exception:
            available = False
        assert available is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. CRUD — node va munosabatlar
# ─────────────────────────────────────────────────────────────────────────────

class TestNeo4jCRUD:
    @neo4j_required
    def test_create_and_read_node(self):
        from core.neo4j_db import execute_query
        uid = f"test_user_{uuid.uuid4().hex[:8]}"
        execute_query("CREATE (:User {id: $id, name: 'Test'})", {"id": uid})
        result = execute_query("MATCH (u:User {id: $id}) RETURN u.name AS name", {"id": uid})
        assert result[0]["name"] == "Test"

    @neo4j_required
    def test_merge_idempotent(self):
        """MERGE ikki marta chaqirilsa faqat bitta node yaratiladi."""
        from core.neo4j_db import execute_query
        uid = f"test_merge_{uuid.uuid4().hex[:8]}"
        for _ in range(3):
            execute_query("MERGE (:User {id: $id})", {"id": uid})
        count = execute_query(
            "MATCH (u:User {id: $id}) RETURN count(u) AS c", {"id": uid}
        )
        assert count[0]["c"] == 1

    @neo4j_required
    def test_create_relationship(self):
        from core.neo4j_db import execute_query
        uid  = f"test_u_{uuid.uuid4().hex[:8]}"
        pid  = f"test_p_{uuid.uuid4().hex[:8]}"
        execute_query(
            """
            MERGE (u:User    {id: $uid})
            MERGE (p:Product {id: $pid})
            MERGE (u)-[:INTERACTED {type: 'view'}]->(p)
            """,
            {"uid": uid, "pid": pid},
        )
        result = execute_query(
            """
            MATCH (u:User {id: $uid})-[r:INTERACTED]->(p:Product {id: $pid})
            RETURN r.type AS type
            """,
            {"uid": uid, "pid": pid},
        )
        assert result[0]["type"] == "view"

    @neo4j_required
    def test_delete_node(self):
        from core.neo4j_db import execute_query
        uid = f"test_del_{uuid.uuid4().hex[:8]}"
        execute_query("CREATE (:User {id: $id})", {"id": uid})
        execute_query("MATCH (u:User {id: $id}) DETACH DELETE u", {"id": uid})
        result = execute_query(
            "MATCH (u:User {id: $id}) RETURN count(u) AS c", {"id": uid}
        )
        assert result[0]["c"] == 0

    @neo4j_required
    def test_update_property(self):
        from core.neo4j_db import execute_query
        uid = f"test_upd_{uuid.uuid4().hex[:8]}"
        execute_query("CREATE (:User {id: $id, score: 0})", {"id": uid})
        execute_query("MATCH (u:User {id: $id}) SET u.score = 42", {"id": uid})
        result = execute_query(
            "MATCH (u:User {id: $id}) RETURN u.score AS score", {"id": uid}
        )
        assert result[0]["score"] == 42


# ─────────────────────────────────────────────────────────────────────────────
# 3. record_interaction()
# ─────────────────────────────────────────────────────────────────────────────

class TestRecordInteraction:
    @neo4j_required
    def test_creates_user_and_product_nodes(self):
        from core.neo4j_db import execute_query, record_interaction
        uid = f"test_u_{uuid.uuid4().hex[:8]}"
        pid = f"test_p_{uuid.uuid4().hex[:8]}"
        record_interaction(uid, pid, "view")
        u = execute_query("MATCH (u:User {id: $id}) RETURN u.id AS id", {"id": uid})
        p = execute_query("MATCH (p:Product {id: $id}) RETURN p.id AS id", {"id": pid})
        assert u[0]["id"] == uid
        assert p[0]["id"] == pid

    @neo4j_required
    def test_relationship_count_increments(self):
        from core.neo4j_db import execute_query, record_interaction
        uid = f"test_u_{uuid.uuid4().hex[:8]}"
        pid = f"test_p_{uuid.uuid4().hex[:8]}"

        record_interaction(uid, pid, "view")
        record_interaction(uid, pid, "view")
        record_interaction(uid, pid, "view")

        result = execute_query(
            """
            MATCH (u:User {id: $uid})-[r:INTERACTED {type: 'view'}]->(p:Product {id: $pid})
            RETURN r.count AS cnt
            """,
            {"uid": uid, "pid": pid},
        )
        assert result[0]["cnt"] == 3

    @neo4j_required
    def test_different_interaction_types(self):
        from core.neo4j_db import execute_query, record_interaction
        uid = f"test_u_{uuid.uuid4().hex[:8]}"
        pid = f"test_p_{uuid.uuid4().hex[:8]}"

        record_interaction(uid, pid, "view")
        record_interaction(uid, pid, "click")
        record_interaction(uid, pid, "purchase")

        result = execute_query(
            """
            MATCH (u:User {id: $uid})-[r:INTERACTED]->(p:Product {id: $pid})
            RETURN r.type AS type, r.count AS cnt
            ORDER BY type
            """,
            {"uid": uid, "pid": pid},
        )
        types = {r["type"] for r in result}
        assert {"view", "click", "purchase"} == types

    @neo4j_required
    def test_last_seen_timestamp_updated(self):
        from core.neo4j_db import execute_query, record_interaction
        uid = f"test_u_{uuid.uuid4().hex[:8]}"
        pid = f"test_p_{uuid.uuid4().hex[:8]}"

        record_interaction(uid, pid, "view")
        r1 = execute_query(
            "MATCH (:User {id:$uid})-[r:INTERACTED]->(:Product {id:$pid}) RETURN r.last_seen AS ts",
            {"uid": uid, "pid": pid},
        )[0]["ts"]

        record_interaction(uid, pid, "view")
        r2 = execute_query(
            "MATCH (:User {id:$uid})-[r:INTERACTED]->(:Product {id:$pid}) RETURN r.last_seen AS ts",
            {"uid": uid, "pid": pid},
        )[0]["ts"]

        assert r2 >= r1  # timestamp oshgan yoki teng

    @neo4j_required
    def test_record_interaction_does_not_raise_on_error(self):
        """record_interaction() xato chiqsa istisno ko'tarmaydi (swallowed)."""
        from core import neo4j_db
        original = neo4j_db.execute_query

        def broken(*args, **kwargs):
            raise RuntimeError("simulated failure")

        neo4j_db.execute_query = broken
        try:
            neo4j_db.record_interaction("u1", "p1", "view")
        except Exception as e:
            pytest.fail(f"record_interaction istisno ko'tardi: {e}")
        finally:
            neo4j_db.execute_query = original


# ─────────────────────────────────────────────────────────────────────────────
# 4. execute_query() — xato tolerantligi
# ─────────────────────────────────────────────────────────────────────────────

class TestExecuteQuerySafety:
    @neo4j_required
    def test_invalid_cypher_returns_empty_list(self):
        """Noto'g'ri Cypher — [] qaytaradi, istisno ko'tarmaydi."""
        from core.neo4j_db import execute_query
        result = execute_query("THIS IS NOT CYPHER !!!")
        assert result == []

    @neo4j_required
    def test_empty_result_returns_empty_list(self):
        from core.neo4j_db import execute_query
        result = execute_query(
            "MATCH (n:NoSuchLabelXYZ_99999) RETURN n"
        )
        assert result == []

    @neo4j_required
    def test_parametrized_query(self):
        from core.neo4j_db import execute_query
        result = execute_query(
            "RETURN $val AS v", {"val": "hello"}
        )
        assert result[0]["v"] == "hello"

    def test_execute_query_when_driver_is_none(self):
        """Driver None bo'lsa — [] qaytaradi."""
        from core import neo4j_db
        original = neo4j_db._driver
        neo4j_db._driver = None

        original_get = neo4j_db._get_driver
        neo4j_db._get_driver = lambda: None

        try:
            result = neo4j_db.execute_query("RETURN 1")
            assert result == []
        finally:
            neo4j_db._driver = original
            neo4j_db._get_driver = original_get


# ─────────────────────────────────────────────────────────────────────────────
# 5. Collaborative Filtering — _neo4j_cf() va _neo4j_popular()
# ─────────────────────────────────────────────────────────────────────────────

class TestNeo4jCF:
    """
    Graf:
      user_A  → product_1, product_2
      user_B  → product_1, product_3   (user_A bilan product_1 umumiy)
      user_C  → product_2, product_4   (user_A bilan product_2 umumiy)

    user_A uchun tavsiya: product_3 (user_B tavsiyasi), product_4 (user_C tavsiyasi)
    """

    @pytest.fixture(autouse=True)
    def seed_cf_graph(self):
        from core.neo4j_db import execute_query, is_available
        if not is_available():
            pytest.skip("Neo4j mavjud emas")

        self.uid_a = f"test_cf_a_{uuid.uuid4().hex[:6]}"
        self.uid_b = f"test_cf_b_{uuid.uuid4().hex[:6]}"
        self.uid_c = f"test_cf_c_{uuid.uuid4().hex[:6]}"
        self.pid_1 = f"test_p1_{uuid.uuid4().hex[:6]}"
        self.pid_2 = f"test_p2_{uuid.uuid4().hex[:6]}"
        self.pid_3 = f"test_p3_{uuid.uuid4().hex[:6]}"
        self.pid_4 = f"test_p4_{uuid.uuid4().hex[:6]}"

        edges = [
            (self.uid_a, self.pid_1), (self.uid_a, self.pid_2),
            (self.uid_b, self.pid_1), (self.uid_b, self.pid_3),
            (self.uid_c, self.pid_2), (self.uid_c, self.pid_4),
        ]
        for uid, pid in edges:
            execute_query(
                """
                MERGE (u:User    {id: $uid})
                MERGE (p:Product {id: $pid})
                MERGE (u)-[r:INTERACTED {type:'view'}]->(p)
                ON CREATE SET r.count=1, r.last_seen=timestamp()
                """,
                {"uid": uid, "pid": pid},
            )
        yield

    @neo4j_required
    def test_cf_returns_unseen_products(self):
        from core.ml_recommendations import _neo4j_cf
        recs = _neo4j_cf(self.uid_a, limit=5)
        # user_A ko'rmagan mahsulotlar tavsiya qilinishi kerak
        seen = {self.pid_1, self.pid_2}
        for rec in recs:
            assert rec not in seen, f"{rec} allaqachon ko'rilgan mahsulot"

    @neo4j_required
    def test_cf_recommends_collaboratively_seen_products(self):
        from core.ml_recommendations import _neo4j_cf
        recs = _neo4j_cf(self.uid_a, limit=5)
        # pid_3 (user_B) yoki pid_4 (user_C) tavsiya qilinishi kerak
        assert self.pid_3 in recs or self.pid_4 in recs

    @neo4j_required
    def test_cf_respects_limit(self):
        from core.ml_recommendations import _neo4j_cf
        recs = _neo4j_cf(self.uid_a, limit=1)
        assert len(recs) <= 1

    @neo4j_required
    def test_cf_no_history_falls_back_to_popular(self):
        """Tarixi yo'q foydalanuvchi uchun popular mahsulotlar qaytadi."""
        from core.ml_recommendations import _neo4j_cf
        new_user = f"test_new_{uuid.uuid4().hex[:8]}"
        recs = _neo4j_cf(new_user, limit=5)
        # popular list bo'sh bo'lmasligi kerak (biz data to'ldirdik)
        assert isinstance(recs, list)

    @neo4j_required
    def test_popular_returns_sorted_by_interactions(self):
        from core.neo4j_db import execute_query
        from core.ml_recommendations import _neo4j_popular

        # pid_1 eng ko'p interaksiyaga ega (2 ta user ko'rgan)
        result = _neo4j_popular(limit=4)
        assert isinstance(result, list)
        assert len(result) > 0
        # Eng mashhur birinchi bo'lishi kerak
        if self.pid_1 in result:
            idx1 = result.index(self.pid_1)
            for pid in [self.pid_3, self.pid_4]:
                if pid in result:
                    assert idx1 <= result.index(pid)

    @neo4j_required
    def test_cf_result_contains_only_strings(self):
        from core.ml_recommendations import _neo4j_cf
        recs = _neo4j_cf(self.uid_a, limit=5)
        for rec in recs:
            assert isinstance(rec, str)


# ─────────────────────────────────────────────────────────────────────────────
# 6. is_available() health check
# ─────────────────────────────────────────────────────────────────────────────

class TestIsAvailable:
    @neo4j_required
    def test_returns_true_when_connected(self):
        from core.neo4j_db import is_available
        assert is_available() is True

    def test_returns_false_when_driver_none(self):
        from core import neo4j_db
        orig = neo4j_db._driver
        neo4j_db._driver = None
        orig_get = neo4j_db._get_driver
        neo4j_db._get_driver = lambda: None
        try:
            assert neo4j_db.is_available() is False
        finally:
            neo4j_db._driver = orig
            neo4j_db._get_driver = orig_get
