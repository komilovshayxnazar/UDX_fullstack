from core.neo4j_db import neo4j_db

from typing import List
import models

def recommend_for_user(user_id: str, limit: int = 10) -> List[str]:
    """
    Recommendation Algorithm via Neo4j:
    1. Try Collaborative Filtering: Recommend products interacted by users who interacted with similar products.
    2. Fallback: If no history, recommend popular products from the graph.
    """
    
    # Check if the user has any interactions
    check_query = """
    MATCH (u:User {id: $user_id})-[:INTERACTED]->()
    RETURN count(u) > 0 AS has_history
    """
    history_result = neo4j_db.execute_query(check_query, {"user_id": user_id})
    has_history = history_result[0]["has_history"] if history_result else False

    if has_history:
        # Collaborative Filtering via Cypher
        # Find products other users interacted with, who also interacted with products the current user interacted with.
        # Exclude products the current user has already interacted with.
        query = """
        MATCH (u:User {id: $user_id})-[:INTERACTED]->(p:Product)<-[:INTERACTED]-(other:User)-[:INTERACTED]->(rec:Product)
        WHERE NOT (u)-[:INTERACTED]->(rec)
        RETURN rec.id AS recommended_id, count(*) AS score
        ORDER BY score DESC
        LIMIT $limit
        """
        results = neo4j_db.execute_query(query, {"user_id": user_id, "limit": limit})
        recommended_ids = [record["recommended_id"] for record in results]
        
        # If we got enough collaborative recommendations, return them
        if len(recommended_ids) >= limit:
            return recommended_ids

    # Fallback Strategy: Popular Products overall
    fallback_limit = limit if not has_history else limit - len(recommended_ids)
    fallback_query = """
    MATCH ()-[r:INTERACTED]->(p:Product)
    RETURN p.id AS recommended_id, count(r) AS interactions
    ORDER BY interactions DESC
    LIMIT $limit
    """
    fallback_results = neo4j_db.execute_query(fallback_query, {"limit": fallback_limit * 2}) # Query extra to account for duplicates
    
    popular_ids = [record["recommended_id"] for record in fallback_results]
    
    # Merge, excluding duplicates
    if has_history:
        for pid in popular_ids:
            if pid not in recommended_ids and len(recommended_ids) < limit:
                recommended_ids.append(pid)
        return recommended_ids
    else:
        return popular_ids[:limit]
