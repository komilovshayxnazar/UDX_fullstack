# Neo4j Recommendation System Setup

The backend now uses Neo4j to power the `recommend_for_user` logic through Collaborative Filtering. 

## 1. Running Neo4j with Docker

You can instantly spin up a local Neo4j database using Docker. Run the following command in your terminal:

```bash
docker run \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -name udx-neo4j \
    -d \
    neo4j:latest
```

This will:
- Start Neo4j in the background (`-d`).
- Expose the HTTP interface on `http://localhost:7474` (you can browse the graph here).
- Expose the Bolt database connection on `bolt://localhost:7687`.
- Set the default credentials to `neo4j` / `password`.

## 2. Environment Configuration

Ensure your `backend/.env` file has the following credentials matching the Docker command:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## 3. Synchronize Existing Data

The Neo4j database starts out empty. To populate it with the existing `Users`, `Categories`, `Products`, and `Interactions` from your SQLite/PostgreSQL database, run the sync script:

```powershell
cd UDX (2)/backend
python sync_neo4j.py
```

This script will run idempotent `MERGE` statements, meaning you can run it securely multiple times whenever new data needs to be populated into the graph for recommendation calculations.

## 4. How it Works

When the API endpoint `/products/recommendations/` is hit:
1. It queries Neo4j to see if the user has any interaction history.
2. If yes, it runs a **Collaborative Filtering** Cypher query: It finds other users with similar interaction histories and recommends products they have engaged with that the current user hasn't seen yet.
3. If no history is found, it gracefully falls back to querying the graph for the most globally interacted products.
