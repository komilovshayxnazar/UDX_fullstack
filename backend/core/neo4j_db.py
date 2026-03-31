import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class Neo4jConnection:
    def __init__(self, uri, user, pwd):
        self._driver = GraphDatabase.driver(uri, auth=(user, pwd))

    def close(self):
        if self._driver is not None:
            self._driver.close()

    def execute_query(self, query, parameters=None):
        if parameters is None:
            parameters = {}
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

# Global instance
neo4j_db = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
