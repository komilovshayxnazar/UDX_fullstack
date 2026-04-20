import os
import logging

logger = logging.getLogger(__name__)

NEO4J_URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver
    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # Verify connectivity
        _driver.verify_connectivity()
        logger.info("[Neo4j] Connected to %s", NEO4J_URI)
    except ImportError:
        logger.warning("[Neo4j] 'neo4j' package not installed — graph features disabled")
        _driver = None
    except Exception as e:
        logger.warning("[Neo4j] Connection failed: %s — graph features disabled", e)
        _driver = None
    return _driver


def execute_query(query: str, parameters: dict | None = None):
    """Run a Cypher query. Returns [] silently if Neo4j is unavailable."""
    driver = _get_driver()
    if driver is None:
        return []
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]
    except Exception as e:
        logger.warning("[Neo4j] Query error: %s", e)
        return []


def record_interaction(user_id: str, product_id: str, interaction_type: str = "view"):
    """
    MERGE user and product nodes, then MERGE the INTERACTED relationship.
    Safe to call even if Neo4j is down — errors are swallowed.
    """
    query = """
    MERGE (u:User {id: $user_id})
    MERGE (p:Product {id: $product_id})
    MERGE (u)-[r:INTERACTED {type: $type}]->(p)
    ON CREATE SET r.count = 1, r.last_seen = timestamp()
    ON MATCH  SET r.count = r.count + 1, r.last_seen = timestamp()
    RETURN r.count AS count
    """
    try:
        execute_query(query, {
            "user_id": user_id,
            "product_id": product_id,
            "type": interaction_type,
        })
    except Exception as e:
        logger.warning("[Neo4j] record_interaction failed: %s", e)


def is_available() -> bool:
    return _get_driver() is not None
